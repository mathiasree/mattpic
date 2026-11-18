# PyInstaller-Rezept für Matt|Pic (Windows und macOS).
# Aufruf aus dem Repo-Hauptordner:  pyinstaller --noconfirm packaging/mattpic.spec
# Ergebnis: dist/MattPic/ (Grundlage für den MSI-Installer) bzw. dist/MattPic.app (macOS)
# exiftool wird vorher von der CI nach tools/exiftool/ gelegt (siehe release.yml).
# Copyright (C) 2026 Mathias Ree – GPL-3.0-or-later
import re
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
PKG = ROOT / "packaging"
VERSION = re.search(r'APP_VERSION = "([^"]+)"', (ROOT / "mattpic.py").read_text(encoding="utf-8")).group(1)

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

# Windows: Versionsangaben in MattPic.exe (Produktname + Version, für die Code-Signatur über SignPath)
version_file = None
if sys.platform == "win32":
    nums = tuple((list(map(int, re.findall(r"\d+", VERSION))) + [0, 0, 0, 0])[:4])
    version_file = Path(workpath) / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Mathias Ree'),
      StringStruct('FileDescription', 'Matt|Pic'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'MattPic'),
      StringStruct('LegalCopyright', '© 2026 Mathias Ree – GNU GPL v3 or later'),
      StringStruct('OriginalFilename', 'MattPic.exe'),
      StringStruct('ProductName', 'Matt|Pic'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="MattPic",
    console=False,
    icon=str(PKG / ("macos/mattpic.icns" if sys.platform == "darwin" else "windows/mattpic.ico")),
    upx=False,
    version=str(version_file) if version_file else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MattPic", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="MattPic.app",
        icon=str(PKG / "macos/mattpic.icns"),
        bundle_identifier="com.mathiasree.MattPic",
        version=VERSION,
        info_plist={
            "CFBundleName": "MattPic",
            "CFBundleDisplayName": "Matt|Pic",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHumanReadableCopyright": "© 2026 Mathias Ree – GNU GPL v3 or later",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
            "LSApplicationCategoryType": "public.app-category.photography",
            "CFBundleDevelopmentRegion": "en",
            "CFBundleLocalizations": ["en", "de", "es", "pt"],
            "CFBundleAllowMixedLocalizations": True,
            # Zugriff auf Fotos in Bilder, Schreibtisch, Dokumente, Downloads und Wechselmedien
            "NSPicturesFolderUsageDescription": "Matt|Pic shows and organizes your photos.",
            "NSDesktopFolderUsageDescription": "Matt|Pic shows and organizes your photos.",
            "NSDocumentsFolderUsageDescription": "Matt|Pic shows and organizes your photos.",
            "NSDownloadsFolderUsageDescription": "Matt|Pic shows and organizes your photos.",
            "NSRemovableVolumesUsageDescription": "Matt|Pic shows and organizes your photos.",
        },
    )
