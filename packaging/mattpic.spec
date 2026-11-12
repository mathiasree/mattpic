# PyInstaller-Rezept für Matt|Pic (Windows).
# Aufruf aus dem Repo-Hauptordner:  pyinstaller --noconfirm packaging/mattpic.spec
# Ergebnis: dist/MattPic/ (Grundlage für den MSI-Installer)
# exiftool wird vorher von der CI nach tools/exiftool/ gelegt (siehe release.yml).
# Copyright (C) 2026 Mathias Ree – GPL-3.0-or-later
from pathlib import Path

ROOT = Path(SPECPATH).parent
PKG = ROOT / "packaging"

datas = [(str(ROOT / f), ".") for f in ("mattpic.svg", "LICENSE")]
if (ROOT / "tools/exiftool").is_dir():
    datas.append((str(ROOT / "tools/exiftool"), "tools/exiftool"))

a = Analysis(
    [str(ROOT / "mattpic.py")],
    pathex=[str(ROOT)],
    hiddenimports=["i18n"],
    datas=datas,
    excludes=["tkinter", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtMultimedia", "PyQt6.QtBluetooth",
              "PyQt6.QtWebEngineCore", "PyQt6.QtPdf", "PyQt6.QtNetwork", "PyQt6.QtSql"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="MattPic",
    console=False,
    icon=str(PKG / "windows/mattpic.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MattPic", upx=False)
