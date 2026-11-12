"""Make one multilingual MSI out of several single-language MSIs.

Windows Installer applies an embedded transform whose name is the LCID of
the user's interface language (the classic WiLangId/WiSubStg technique).
Runs on Windows (GitHub Actions) with Python 3.12 (msilib) and pywin32.

    python embed_languages.py base.msi 1031=de.msi 3082=es.msi 1046=pt.msi

Copyright (C) 2026 Mathias Ree – GPL-3.0-or-later
"""
import gc
import os
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
import msilib  # noqa: E402  (Windows only, removed in Python 3.13)
import win32com.client  # noqa: E402

base = os.path.abspath(sys.argv[1])
langs = [(lcid, os.path.abspath(path)) for lcid, path in (a.split("=", 1) for a in sys.argv[2:])]
tmp = tempfile.mkdtemp()

installer = win32com.client.Dispatch("WindowsInstaller.Installer")
transforms = []
for lcid, path in langs:
    mst = os.path.join(tmp, f"{lcid}.mst")
    ref = installer.OpenDatabase(base, 0)          # read-only
    upd = installer.OpenDatabase(path, 0)
    upd.GenerateTransform(ref, mst)                # base -> this language
    upd.CreateTransformSummaryInfo(ref, mst, 0, 0)
    del ref, upd
    transforms.append((lcid, mst))
    print(f"transform {lcid}: {os.path.getsize(mst)} bytes")
del installer
gc.collect()

db = msilib.OpenDatabase(base, msilib.MSIDBOPEN_TRANSACT)
view = db.OpenView("SELECT `Name`, `Data` FROM `_Storages`")
for lcid, mst in transforms:
    rec = msilib.CreateRecord(2)
    rec.SetString(1, lcid)
    rec.SetStream(2, mst)
    view.Modify(msilib.MSIMODIFY_ASSIGN, rec)
view.Close()

si = db.GetSummaryInformation(1)
platform, base_lang = si.GetProperty(msilib.PID_TEMPLATE).decode().split(";")
template = f"{platform};{','.join([base_lang] + [lcid for lcid, _ in transforms])}"
si.SetProperty(msilib.PID_TEMPLATE, template)
si.Persist()
db.Commit()
print("Template:", template)
