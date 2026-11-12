#!/bin/sh
# Baut Matt|Pic als Flatpak und packt es in EINE Datei (MattPic-Linux.flatpak),
# die man per Doppelklick (GNOME Software/KDE Discover) oder mit
#   flatpak install --user MattPic-Linux.flatpak
# installiert. Fehlende Laufzeitumgebungen kommen dabei automatisch von Flathub.
# Voraussetzung: flatpak-builder, org.kde.Sdk//6.11, com.riverbankcomputing.PyQt.BaseApp//6.11
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$HERE/../.." && pwd)"
OUT="${OUT:-$SRC/dist}"
WORK="${WORK:-$HOME/.cache/mattpic-flatpak}"
mkdir -p "$OUT" "$WORK"
flatpak-builder --user --force-clean --disable-rofiles-fuse \
    --state-dir="$WORK/state" --repo="$WORK/repo" \
    "$WORK/build" "$HERE/com.mathiasree.MattPic.yml"
flatpak build-bundle --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo \
    "$WORK/repo" "$OUT/MattPic-Linux.flatpak" com.mathiasree.MattPic
ls -la "$OUT/MattPic-Linux.flatpak"
