# Matt|Pic

Fotos schnell sortieren und bearbeiten, im Stil von Picasa. Python + PyQt6, alles in `mattpic.py`.

*A fast Picasa-style photo organizer for Linux, Windows and macOS. Interface in English, Spanish, Portuguese and German.*

Die Oberfläche folgt der Systemsprache (Deutsch, Englisch, Spanisch, Portugiesisch) und lässt sich unter **Hilfe → Sprache der Oberfläche** umstellen. Übersetzungen stehen in `i18n.py`.

## Herunterladen (Linux)
[MattPic-Linux.flatpak](https://github.com/mathiasree/mattpic/releases/latest/download/MattPic-Linux.flatpak) herunterladen und per Doppelklick (KDE Discover, GNOME Software) installieren, oder im Terminal:
```sh
flatpak install --user MattPic-Linux.flatpak
```
Die Laufzeitumgebung kommt dabei automatisch von Flathub.

## Herunterladen (Windows 10/11)
[MattPic-Windows.msi](https://github.com/mathiasree/mattpic/releases/latest/download/MattPic-Windows.msi) herunterladen, öffnen und die Lizenz bestätigen. Es sind keine Administratorrechte nötig. Erscheint „Der Computer wurde durch Windows geschützt“: „Weitere Informationen“ → „Trotzdem ausführen“. Videos zeigen unter Windows kein Vorschaubild (ffmpeg ist nicht dabei).

## Herunterladen (macOS 12 oder neuer)
- Mac mit Apple-Chip (M1–M4): [MattPic-macOS-AppleSilicon.dmg](https://github.com/mathiasree/mattpic/releases/latest/download/MattPic-macOS-AppleSilicon.dmg)
- Ältere Macs mit Intel-Prozessor: [MattPic-macOS-Intel.dmg](https://github.com/mathiasree/mattpic/releases/latest/download/MattPic-macOS-Intel.dmg)

Das .dmg öffnen und MattPic in „Programme“ ziehen. Beim ersten Start (das Programm ist nicht von Apple beglaubigt): ab macOS 15 einmal öffnen → „Fertig“ → Systemeinstellungen → Datenschutz & Sicherheit → unten „Trotzdem öffnen“; macOS 12–14: Rechtsklick auf MattPic → „Öffnen“ → „Öffnen“. Videos zeigen auf dem Mac kein Vorschaubild, außer ffmpeg ist z. B. über Homebrew installiert.

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

## Code signing policy
Free code signing provided by [SignPath.io](https://about.signpath.io), certificate by [SignPath Foundation](https://signpath.org)

The Windows installer (`MattPic-Windows.msi`) and the program files it contains are built from this repository by GitHub Actions (`.github/workflows/release.yml`) and signed only after manual approval of each release.

- Committers and reviewers: [Mathias Ree](https://github.com/mathiasree)
- Approvers: [Mathias Ree](https://github.com/mathiasree)

Changes proposed by others (pull requests) are reviewed by a team member before they are merged.

### Privacy policy
This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

## Lizenz
GPL-3.0-or-later, © Mathias Ree
