# Matt|Pic

Fotos schnell sortieren und bearbeiten, im Stil von Picasa. Python + PyQt6, alles in `mattpic.py`.

*A fast Picasa-style photo organizer for Linux. Interface currently in German.*

## Herunterladen (Linux)
[MattPic-Linux.flatpak](https://github.com/mathiasree/mattpic/releases/latest/download/MattPic-Linux.flatpak) herunterladen und per Doppelklick (KDE Discover, GNOME Software) installieren, oder im Terminal:
```sh
flatpak install --user MattPic-Linux.flatpak
```
Die Laufzeitumgebung kommt dabei automatisch von Flathub.

## Aus dem Quelltext starten
```sh
python3 mattpic.py
```
Benötigt `PyQt6`, `numpy`, `Pillow`, für Videos `ffmpeg`, für RAW in voller Auflösung `kimageformats` mit libraw, für den EXIF-Reiter `exiftool`.

Flatpak selbst bauen: `packaging/flatpak/build.sh` → `dist/MattPic-Linux.flatpak`.

## Grundsätze
- Die Originale werden nie verändert. Sterne und Korrekturen stehen in `~/.local/share/mattpic/library.db`, Vorschaubilder in `thumbs.db` daneben. Nur der Export schreibt neue Dateien.
- Nur Verschieben und Papierkorb fassen Dateien an, beides geht mit Strg+Z zurück.
- Ein nicht erreichbarer Ordner (z. B. nicht eingehängtes Netzlaufwerk) verliert nichts: Sterne und Korrekturen bleiben. Außerhalb verschobene Dateien werden an Name, Größe und Datum wiedererkannt.
- Bewusst nicht drin: Gesichtserkennung, Collagen, Effekte.

## Tastenkürzel
F1 im Programm.

## Lizenz
GPL-3.0-or-later, © Mathias Ree
