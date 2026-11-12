#!/usr/bin/env python3
"""Matt|Pic: schnelle Foto-Verwaltung im Stil von Picasa.

Die Originale werden nie verändert. Bearbeitungen liegen als Parameter in der
Datenbank und werden erst beim Exportieren in eine neue Datei gerechnet.
"""
import bisect
import html
import io
import json
import math
import os
import shlex
import shutil
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import traceback
from collections import OrderedDict, deque

import numpy as np
from PIL import Image, ImageOps
from PyQt6.QtCore import (QBuffer, QByteArray, QEvent, QFile, QIODevice, QMimeDatabase, QProcess, QMimeData, QObject, QPoint, QPointF, QRect,
                          QRectF, QSettings, QSize, QStandardPaths, Qt, QThread, QTimer, QUrl, pyqtSignal,
                          QLibraryInfo, QLocale, QTranslator)
from PyQt6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QDrag, QFont, QIcon,
                         QImage, QImageReader, QKeySequence, QPainter, QPainterPath,
                         QPen, QPixmap, QPolygonF, QTransform)
from PyQt6.QtWidgets import (QAbstractItemView, QAbstractScrollArea, QApplication, QComboBox, QDialog,
                             QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                             QMenu, QMessageBox, QProgressDialog, QPushButton, QSizePolicy, QSlider,
                             QSplitter, QStackedWidget, QTabWidget, QTextBrowser, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

APP = "Matt|Pic"          # Anzeigename
APP_ID = "MattPic"        # technischer Name (Dateien, Einstellungen)
APP_VERSION = "1.2.0"
FLATPAK = bool(os.environ.get("FLATPAK_ID"))
WINDOWS = sys.platform == "win32"
MAC = sys.platform == "darwin"
_DEFAULT_DATA = (os.path.join(os.environ.get("APPDATA", "~"), "MattPic") if WINDOWS
                 else "~/Library/Application Support/MattPic" if MAC else "~/.local/share/mattpic")
DATA_DIR = os.path.expanduser(os.environ.get("MATTPIC_DATA") or os.environ.get("PHOTOMATHIAS_DATA") or _DEFAULT_DATA)
# Unter Windows kein schwarzes Konsolenfenster für exiftool
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if WINDOWS else {}


def tool(name):
    """Befehl für ein Hilfsprogramm als Liste: das mitgelieferte (Windows: tools\\name\\name.exe,
    macOS: Perl-Skript tools/exiftool/exiftool, Perl gehört zum System), sonst das des Systems."""
    if WINDOWS:
        exe = os.path.join(HERE, "tools", name, name + ".exe")
        if os.path.exists(exe):
            return [exe]
    if MAC:
        script = os.path.join(HERE, "tools", name, name)
        if os.path.exists(script):
            return ["/usr/bin/perl", script]
        for d in ("/opt/homebrew/bin", "/usr/local/bin"):     # z. B. von Homebrew
            if os.path.exists(os.path.join(d, name)):
                return [os.path.join(d, name)]
    return [name]


def settings_store():
    """Einstellungen: unter Windows als INI-Datei in %APPDATA%\\MattPic, sonst im Standardort."""
    if WINDOWS:
        return QSettings(os.path.join(DATA_DIR, APP_ID + ".ini"), QSettings.Format.IniFormat)
    return QSettings(APP_ID, APP_ID)
# Im fertigen Programm (PyInstaller) liegen die Beilagen in sys._MEIPASS
HERE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import i18n                         # noqa: E402
from i18n import T                  # noqa: E402


def num(n):
    """Zahl mit Tausendertrennzeichen der Oberflächensprache."""
    return f"{n:,}".replace(",", i18n.THOUSANDS.get(i18n.language(), "."))


def photos_text(n):
    return T("1 Foto") if n == 1 else T("{n} Fotos", n=num(n))
THUMB = 256         # Kantenlänge der gespeicherten Vorschaubilder
PREVIEW = 2048      # Kantenlänge der Bilder in der Großansicht
MIME = "application/x-mattpic-ids"

EXT_PHOTO = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".heic", ".heif"}
EXT_RAW = {".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf", ".pef", ".srw"}
EXT_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".mpg", ".mpeg", ".wmv", ".m4v", ".3gp", ".mts"}
KIND_PHOTO, KIND_RAW, KIND_VIDEO = 0, 1, 2
SKIP_DIRS = {"$RECYCLE.BIN", "System Volume Information", "lost+found", "@eaDir", "__MACOSX"}

MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
          "Oktober", "November", "Dezember"]

# Picasa-Farben
C_BLUE = "#3b73c4"
C_LIBRARY = "#ececec"
C_PANEL = "#dfe3e8"
C_EDIT_BG = "#2b2b2b"

STYLE = f"""
QMainWindow, QDialog {{ background: {C_PANEL}; }}
QMenuBar {{ background: #f4f5f7; border-bottom: 1px solid #b9bfc7; }}
QMenuBar::item:selected, QMenu::item:selected {{ background: {C_BLUE}; color: white; }}
QMenu {{ background: #fbfbfb; border: 1px solid #9aa2ac; }}
QStatusBar {{ background: #d5d9df; color: #333; border-top: 1px solid #aeb5be; }}
QStatusBar::item {{ border: none; }}
QTreeWidget {{ background: {C_PANEL}; border: none; outline: 0; color: #1c1c1c; }}
QTreeWidget::item {{ height: 21px; }}
QTreeWidget::item:selected {{ background: {C_BLUE}; color: white; }}
QTreeWidget::item:hover:!selected {{ background: #cdd6e3; }}
QSplitter::handle {{ background: #aeb5be; }}
QPushButton {{
    background: qlineargradient(y1:0, y2:1, stop:0 #ffffff, stop:1 #d4d9e0);
    border: 1px solid #98a0ab; border-radius: 3px; padding: 3px 9px; color: #1c1c1c; }}
QPushButton:hover {{ background: qlineargradient(y1:0, y2:1, stop:0 #ffffff, stop:1 #c3d4ec); border-color: {C_BLUE}; }}
QPushButton:pressed, QPushButton:checked {{ background: #a9c3e8; border-color: {C_BLUE}; }}
QPushButton:disabled {{ color: #9a9a9a; background: #e4e6e9; border-color: #c4c8ce; }}
QLineEdit {{ background: white; border: 1px solid #98a0ab; border-radius: 9px; padding: 2px 8px; color: #1c1c1c; }}
QLineEdit:focus {{ border-color: {C_BLUE}; }}
QComboBox {{ background: #fbfbfb; border: 1px solid #98a0ab; border-radius: 3px; padding: 2px 6px; color: #1c1c1c; }}
QSlider::groove:horizontal {{ height: 4px; background: #9aa2ac; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 13px; margin: -5px 0; border-radius: 6px;
    background: qlineargradient(y1:0, y2:1, stop:0 #ffffff, stop:1 #bfc6d0); border: 1px solid #7d8591; }}
QSlider::sub-page:horizontal {{ background: {C_BLUE}; border-radius: 2px; }}
QTabWidget::pane {{ border: 1px solid #aeb5be; background: #f2f3f5; top: -1px; }}
QTabBar::tab {{ background: #cfd4db; border: 1px solid #aeb5be; padding: 5px 9px; border-top-left-radius: 3px;
    border-top-right-radius: 3px; color: #1c1c1c; }}
QTabBar::tab:selected {{ background: #f2f3f5; border-bottom-color: #f2f3f5; }}
#toolbar {{ background: qlineargradient(y1:0, y2:1, stop:0 #f6f7f9, stop:1 #cfd5dd); border-bottom: 1px solid #a3abb5; }}
#bottombar {{ background: qlineargradient(y1:0, y2:1, stop:0 #e7eaee, stop:1 #c5ccd5); border-top: 1px solid #a3abb5; }}
#editpanel {{ background: #f2f3f5; }}
#editbar {{ background: qlineargradient(y1:0, y2:1, stop:0 #e7eaee, stop:1 #c5ccd5); }}
#filmbar {{ background: #1f1f1f; }}
QLabel#muted {{ color: #555; }}
"""


# ---------------------------------------------------------------------------
# Bilder laden
# ---------------------------------------------------------------------------

def _is_viewable_jpeg(f, off):
    """Normales JPEG? Die eigentlichen RAW-Daten sind oft verlustfreies JPEG (SOF3), das kein Dekoder liest."""
    f.seek(off)
    if f.read(2) != b"\xff\xd8":
        return False
    for _ in range(64):
        head = f.read(4)
        if len(head) < 4 or head[0] != 0xff:
            return False
        if head[1] in (0xc0, 0xc1, 0xc2):
            return True
        if 0xc3 <= head[1] <= 0xcf and head[1] not in (0xc4, 0xc8, 0xcc):
            return False
        f.seek(struct.unpack(">H", head[2:4])[0] - 2, 1)
    return False


def raw_embedded_jpeg(path):
    """Liefert (JPEG-Bytes, Orientierung) der größten Vorschau einer TIFF-basierten RAW-Datei."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
            if head[:2] == b"II":
                end = "<"
            elif head[:2] == b"MM":
                end = ">"
            else:
                return None
            if struct.unpack(end + "H", head[2:4])[0] not in (42, 0x55, 0x4f52):    # TIFF, Panasonic, Olympus
                return None
            todo = [struct.unpack(end + "I", head[4:8])[0]]
            seen, best, orientation = set(), None, 1
            while todo and len(seen) < 16:
                ifd = todo.pop(0)
                if not ifd or ifd in seen:
                    continue
                seen.add(ifd)
                f.seek(ifd)
                count = struct.unpack(end + "H", f.read(2))[0]
                tags = {}
                for _ in range(count):
                    entry = f.read(12)
                    tag, typ, n = struct.unpack(end + "HHI", entry[:8])
                    if typ == 3 and n == 1:
                        tags[tag] = struct.unpack(end + "H", entry[8:10])[0]
                    elif typ == 4 and n == 1:
                        tags[tag] = struct.unpack(end + "I", entry[8:12])[0]
                    elif tag == 0x2e and n > 4:     # Panasonic: JPEG steckt direkt im Tag
                        offset = struct.unpack(end + "I", entry[8:12])[0]
                        pos = f.tell()
                        if (best is None or n > best[1]) and _is_viewable_jpeg(f, offset):
                            best = (offset, n)
                        f.seek(pos)
                    elif tag == 0x14a and typ == 4 and n > 1:
                        pos = f.tell()
                        f.seek(struct.unpack(end + "I", entry[8:12])[0])
                        todo += list(struct.unpack(end + "I" * n, f.read(4 * n)))
                        f.seek(pos)
                if len(seen) == 1:
                    orientation = tags.get(0x112, 1)
                if 0x14a in tags:
                    todo.append(tags[0x14a])
                for off_tag, len_tag in ((0x111, 0x117), (0x201, 0x202)):
                    off, size = tags.get(off_tag), tags.get(len_tag)
                    if off and size and (best is None or size > best[1]):
                        if _is_viewable_jpeg(f, off):
                            best = (off, size)
                f.seek(ifd + 2 + 12 * count)
                nxt = f.read(4)
                if len(nxt) == 4:
                    todo.append(struct.unpack(end + "I", nxt)[0])
            if not best:
                return None
            f.seek(best[0])
            return f.read(best[1]), orientation
    except (OSError, struct.error):
        return None


def video_frame(path, size):
    """Holt ein Einzelbild aus einem Video."""
    for seek in ("1", "0"):
        cmd = tool("ffmpeg") + ["-v", "error", "-ss", seek, "-i", path, "-frames:v", "1",
               "-vf", f"scale='min({size},iw)':-2", "-f", "image2pipe", "-c:v", "mjpeg", "-"]
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=30, **NO_WINDOW).stdout
        except (OSError, subprocess.TimeoutExpired):
            return QImage()
        if out:
            return QImage.fromData(out, "JPEG")
    return QImage()


def _scaled_read(reader, size):
    reader.setAutoTransform(True)
    if size:
        s = reader.size()
        if s.isValid() and max(s.width(), s.height()) > size:
            reader.setScaledSize(s.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio))
    return reader.read()


def load_qimage(path, kind, size=None):
    """Lädt ein Bild, auf Wunsch gleich beim Dekodieren verkleinert (schnell bei JPEG)."""
    if kind == KIND_VIDEO:
        return video_frame(path, size or PREVIEW)
    if kind == KIND_RAW and size:   # Für 100 % und Export liest unten der RAW-Dekoder die volle Auflösung
        emb = raw_embedded_jpeg(path)
        if emb:
            data = QByteArray(emb[0])
            buf = QBuffer(data)
            buf.open(QIODevice.OpenModeFlag.ReadOnly)
            img = _scaled_read(QImageReader(buf, b"jpeg"), size)
            # Eine sehr kleine Vorschau (manche DNG) reicht nur für die Galerie, sonst unten voll dekodieren
            if not img.isNull() and max(img.width(), img.height()) >= min(size, 1000):
                angle = {3: 180, 6: 90, 8: 270}.get(emb[1])
                return img.transformed(QTransform().rotate(angle)) if angle else img
    img = _scaled_read(QImageReader(path), size)
    if img.isNull():
        try:
            with Image.open(path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                if size:
                    im.thumbnail((size, size))
                return array_to_qimage(np.asarray(im))
        except Exception:
            return QImage()
    return img


def load_pil_full(path, kind):
    """Volle Auflösung für den Export, immer aufrecht gedreht, dazu die EXIF-Daten des Originals."""
    if kind == KIND_RAW:
        img = _scaled_read(QImageReader(path), None)
        if not img.isNull():
            return Image.fromarray(qimage_to_array(img)), None
        emb = raw_embedded_jpeg(path)
        if emb:
            im = Image.open(io.BytesIO(emb[0]))
            angle = {3: 180, 6: 270, 8: 90}.get(emb[1])
            im = im.convert("RGB")
            return im.rotate(angle, expand=True) if angle else im, None
    with Image.open(path) as src:
        im = ImageOps.exif_transpose(src).convert("RGB")
        try:
            exif = src.getexif()
            exif[0x112] = 1
            exif = exif.tobytes()
        except Exception:
            exif = None
    return im, exif


def qimage_to_array(img):
    img = img.convertToFormat(QImage.Format.Format_RGB888)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    ptr = img.constBits()
    ptr.setsize(h * bpl)
    return np.frombuffer(ptr, np.uint8).reshape(h, bpl)[:, :w * 3].reshape(h, w, 3).copy()


def array_to_qimage(a):
    h, w = a.shape[:2]
    a = np.ascontiguousarray(a)
    return QImage(a.data, w, h, w * 3, QImage.Format.Format_RGB888).copy()


# ---------------------------------------------------------------------------
# Bearbeitung: Geometrie, dann Töne. edits ist ein dict, fehlende Schlüssel = neutral.
# ---------------------------------------------------------------------------

def geometry(a, e, with_crop=True):
    rot = e.get("rot", 0)
    if rot:
        a = np.rot90(a, -rot)
    angle = e.get("straighten", 0)
    if angle:
        h, w = a.shape[:2]
        rotated = np.asarray(Image.fromarray(np.ascontiguousarray(a)).rotate(-angle, Image.Resampling.BICUBIC))
        t = math.radians(abs(angle))
        k = 1 / (math.cos(t) + math.sin(t) * max(w / h, h / w))
        cw, ch = max(1, int(w * k)), max(1, int(h * k))
        x, y = (w - cw) // 2, (h - ch) // 2
        a = rotated[y:y + ch, x:x + cw]
    crop = e.get("crop")
    if crop and with_crop:
        h, w = a.shape[:2]
        x0, y0 = int(crop[0] * w), int(crop[1] * h)
        x1, y1 = max(x0 + 1, int(crop[2] * w)), max(y0 + 1, int(crop[3] * h))
        a = a[y0:y1, x0:x1]
    return a


TONE_KEYS = ("levels", "gains", "fill", "high", "shad", "temp", "sat")


def tone(a, e):
    if not any(k in e for k in TONE_KEYS):
        return a
    x = np.linspace(0, 1, 256)
    gains = list(e.get("gains", (1, 1, 1)))
    temp = e.get("temp", 0)
    if temp:
        gains[0] *= 1 + 0.25 * temp
        gains[2] *= 1 - 0.25 * temp
    fill, high, shad = e.get("fill", 0), e.get("high", 0), e.get("shad", 0)
    levels = e.get("levels")
    channels = []
    for c in range(3):
        v = np.clip(x * gains[c], 0, 1)
        if levels:
            v = np.clip((v - levels[0]) / max(0.02, levels[1] - levels[0]), 0, 1)
        if fill:
            v = v ** (1 / (1 + 1.5 * fill))
        if shad:
            v = v - shad * 0.9 * v * (1 - v) ** 2
        if high:
            v = v + high * 1.2 * v ** 2 * (1 - v)
        channels.append((np.clip(v, 0, 1) * 255 + 0.5).astype(np.uint8))
    out = np.stack([channels[c][a[..., c]] for c in range(3)], axis=-1)
    sat = e.get("sat", 0)
    if sat:
        f = out.astype(np.float32)
        gray = f @ np.array([0.299, 0.587, 0.114], np.float32)
        out = np.clip(gray[..., None] + (1 + sat) * (f - gray[..., None]), 0, 255).astype(np.uint8)
    return out


def render_edits(a, e):
    return tone(geometry(a, e), e) if e else a


def auto_levels(a):
    step = max(1, max(a.shape[:2]) // 512)
    s = a[::step, ::step].astype(np.float32)
    luma = s @ np.array([0.299, 0.587, 0.114], np.float32)
    lo, hi = np.percentile(luma, (0.5, 99.5))
    return [round(float(lo) / 255, 4), round(max(float(hi), float(lo) + 8) / 255, 4)]


def auto_gains(a):
    step = max(1, max(a.shape[:2]) // 512)
    s = a[::step, ::step].astype(np.float32)
    mids = (s.mean(axis=2) > 25) & (s.mean(axis=2) < 230)
    if mids.sum() < 100:
        return [1.0, 1.0, 1.0]
    m = s[mids].mean(axis=0)
    gray = m.mean()
    return [round(float(np.clip(gray / max(v, 1), 0.7, 1.4)), 4) for v in m]


def rotated_edits(e, turns):
    """Drehung in 90-Grad-Schritten (1 = rechts, -1 = links), ein Ausschnitt dreht mit."""
    e = dict(e or {})
    rot = (e.get("rot", 0) + turns) % 4
    if rot:
        e["rot"] = rot
    else:
        e.pop("rot", None)
    crop = e.get("crop")
    if crop:
        x0, y0, x1, y1 = crop
        e["crop"] = [1 - y1, x0, 1 - y0, x1] if turns == 1 else [y0, 1 - x1, y1, 1 - x0]
    return e


def edits_json(e):
    return json.dumps(e, sort_keys=True) if e else ""


# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

class Photo:
    __slots__ = ("id", "path", "folder", "name", "size", "mtime", "taken", "kind", "rating", "edits", "missing")

    @property
    def date(self):
        return self.taken if self.taken and self.taken > 0 else self.mtime

    @property
    def ver(self):
        return f"{int(self.mtime)}|{edits_json(self.edits)}"


def open_library():
    con = sqlite3.connect(os.path.join(DATA_DIR, "library.db"), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS roots(path TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS folders(path TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS photos(
            id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, folder TEXT NOT NULL, name TEXT NOT NULL,
            size INTEGER, mtime REAL, taken REAL, kind INTEGER, rating INTEGER DEFAULT 0, edits TEXT,
            missing INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS photos_folder ON photos(folder);
    """)
    return con


def open_thumbs():
    con = sqlite3.connect(os.path.join(DATA_DIR, "thumbs.db"), timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("CREATE TABLE IF NOT EXISTS thumbs(id INTEGER PRIMARY KEY, ver TEXT, data BLOB)")
    return con


def read_taken(path):
    """Aufnahmezeit aus den EXIF-Daten, 0 wenn keine da ist."""
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            s = ex.get_ifd(0x8769).get(36867) or ex.get(306)
        if isinstance(s, bytes):
            s = s.decode("ascii", "ignore")
        return time.mktime(time.strptime(s.strip()[:19], "%Y:%m:%d %H:%M:%S"))
    except Exception:
        return 0


class Scanner(QThread):
    """Gleicht die Ordner mit der Datenbank ab und liest danach die Aufnahmezeiten."""
    changed = pyqtSignal()
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop = False
        self.offline = set()

    def run(self):
        con = open_library()
        try:
            self.scan(con)
            self.read_dates(con)
        finally:
            con.close()
        self.status.emit("")

    def scan(self, con):
        roots = [r[0] for r in con.execute("SELECT path FROM roots")]
        rows = {r[0]: r[1:] for r in con.execute("SELECT path,id,size,mtime,missing,name FROM photos")}
        seen, skipped, new, updates, unmiss, folders = set(), [], [], [], [], set()
        changed, n = False, 0
        for root in roots:
            has_rows = any(p.startswith(root + os.sep) for p in rows)
            try:
                offline = not os.path.isdir(root) or (has_rows and not os.listdir(root))
            except OSError:
                offline = True
            if offline:     # nicht eingehängt: Sterne und Bearbeitungen nicht anrühren
                self.offline.add(root)
                continue
            self.offline.discard(root)
            stack = [root]
            while stack and not self.stop:
                folder = stack.pop()
                folders.add(folder)
                try:
                    entries = list(os.scandir(folder))
                except OSError:
                    skipped.append(folder + os.sep)
                    continue
                for en in entries:
                    name = en.name
                    try:
                        name.encode("utf-8")
                        if en.is_dir(follow_symlinks=False):
                            if not name.startswith(".") and name not in SKIP_DIRS:
                                stack.append(en.path)
                            continue
                        ext = os.path.splitext(name)[1].lower()
                        kind = (KIND_PHOTO if ext in EXT_PHOTO else KIND_RAW if ext in EXT_RAW
                                else KIND_VIDEO if ext in EXT_VIDEO else None)
                        if kind is None or name.startswith("."):
                            continue
                        st = en.stat()
                    except (OSError, UnicodeEncodeError):
                        continue
                    seen.add(en.path)
                    n += 1
                    if n % 500 == 0:
                        self.status.emit(T("Durchsuche Ordner … {n} Dateien", n=num(n)))
                    row = rows.get(en.path)
                    if row is None:
                        new.append((en.path, folder, name, st.st_size, st.st_mtime, kind))
                    else:
                        if row[1] != st.st_size or int(row[2]) != int(st.st_mtime):
                            updates.append((st.st_size, st.st_mtime, row[0]))
                        if row[3]:
                            unmiss.append((row[0],))
        if self.stop:
            return
        # Verschwundene Dateien bleiben als "missing" erhalten: So finden Sterne und Bearbeitungen
        # eine außerhalb verschobene Datei wieder, erkannt an Name, Größe und Datum.
        scanned = tuple(r + os.sep for r in roots if r not in self.offline)
        skipped = tuple(skipped)
        gone, relink = [], {}
        for path, (pid, size, mtime, missing, name) in rows.items():
            if path in seen or not path.startswith(scanned) or path.startswith(skipped):
                continue
            relink[(name, size, int(mtime))] = pid
            if not missing:
                gone.append((pid,))
        inserts = []
        moved = []
        for path, folder, name, size, mtime, kind in new:
            pid = relink.pop((name, size, int(mtime)), None)
            if pid is not None:
                moved.append((pid, path, folder))
            else:
                inserts.append((path, folder, name, size, mtime, kind))
        before = {r[0] for r in con.execute("SELECT path FROM folders")}
        with con:
            for pid, path, folder in moved:
                con.execute("UPDATE photos SET path=?,folder=?,missing=0 WHERE id=?", (path, folder, pid))
            gone = [g for g in gone if g[0] not in {m[0] for m in moved}]
            con.executemany("UPDATE photos SET missing=1 WHERE id=?", gone)
            con.executemany("UPDATE photos SET missing=0 WHERE id=?", unmiss)
            con.executemany("UPDATE photos SET size=?,mtime=?,taken=NULL WHERE id=?", updates)
            con.executemany("INSERT OR IGNORE INTO photos(path,folder,name,size,mtime,kind) VALUES(?,?,?,?,?,?)", inserts)
            for r in roots:
                if r not in self.offline:
                    pre = r + os.sep
                    con.execute("DELETE FROM folders WHERE path=? OR substr(path,1,?)=?", (r, len(pre), pre))
            con.executemany("INSERT OR IGNORE INTO folders(path) VALUES(?)", [(f,) for f in folders])
            changed = bool(moved or gone or unmiss or updates or inserts or folders != before)
        if changed:
            self.changed.emit()

    def read_dates(self, con):
        todo = con.execute("SELECT id,path,kind FROM photos WHERE taken IS NULL AND missing=0").fetchall()
        last, done = time.monotonic(), 0
        batch = []
        for pid, path, kind in todo:
            if self.stop:
                break
            batch.append((0 if kind == KIND_VIDEO else read_taken(path), pid))
            done += 1
            if len(batch) >= 100:
                with con:
                    con.executemany("UPDATE photos SET taken=? WHERE id=?", batch)
                batch = []
                self.status.emit(T("Lese Aufnahmedaten … {done} von {total}", done=num(done), total=num(len(todo))))
                if time.monotonic() - last > 4:
                    last = time.monotonic()
                    self.changed.emit()
        if batch:
            with con:
                con.executemany("UPDATE photos SET taken=? WHERE id=?", batch)
        if todo:
            self.changed.emit()


# ---------------------------------------------------------------------------
# Vorschaubilder
# ---------------------------------------------------------------------------

class ThumbEngine(QObject):
    """Holt Vorschaubilder im Hintergrund. Was gerade sichtbar ist, kommt immer zuerst dran."""
    ready = pyqtSignal(int, QImage)
    WORKERS = 3

    def __init__(self):
        super().__init__()
        self.cond = threading.Condition()
        self.urgent = []
        self.background = deque()
        self.inflight = set()
        self.stopped = False
        self.local = threading.local()
        for i in range(self.WORKERS):
            threading.Thread(target=self._run, args=(i,), daemon=True).start()

    def prioritize(self, photos):
        with self.cond:
            self.urgent = [(p.id, p.path, p.kind, p.ver, p.edits) for p in reversed(photos) if p.id not in self.inflight]
            self.cond.notify_all()

    def request(self, photos):
        with self.cond:
            self.urgent += [(p.id, p.path, p.kind, p.ver, p.edits) for p in photos]
            self.cond.notify_all()

    def set_background(self, photos):
        with self.cond:
            self.background = deque((p.id, p.path, p.kind, p.ver, p.edits) for p in photos)
            self.cond.notify_all()

    def remaining(self):
        return len(self.background)

    def shutdown(self):
        with self.cond:
            self.stopped = True
            self.cond.notify_all()

    def _db(self):
        con = getattr(self.local, "con", None)
        if con is None:
            con = self.local.con = open_thumbs()
        return con

    def _run(self, worker):
        while True:
            with self.cond:
                # Der letzte Arbeiter bleibt frei für das, was gerade auf dem Bildschirm ist.
                while not self.stopped and not self.urgent and not (self.background and worker < self.WORKERS - 1):
                    self.cond.wait()
                if self.stopped:
                    return
                urgent = bool(self.urgent)
                job = self.urgent.pop() if urgent else self.background.popleft()
                if urgent:
                    self.inflight.add(job[0])
            try:
                img = self._load(job, urgent)
                if urgent:
                    self.ready.emit(job[0], img if img is not None else QImage())
            except Exception:
                if urgent:
                    self.ready.emit(job[0], QImage())
            finally:
                if urgent:
                    with self.cond:
                        self.inflight.discard(job[0])

    def _load(self, job, want_image):
        pid, path, kind, ver, edits = job
        db = self._db()
        row = db.execute("SELECT ver,data FROM thumbs WHERE id=?", (pid,)).fetchone()
        if row and row[0] == ver:
            return QImage.fromData(row[1], "JPEG") if want_image and row[1] else QImage() if want_image else None
        size = THUMB * 2 if edits else THUMB
        img = load_qimage(path, kind, size)
        if img.isNull():
            if os.path.exists(path):    # defekt, nicht nur gerade nicht erreichbar
                db.execute("INSERT OR REPLACE INTO thumbs VALUES(?,?,?)", (pid, ver, b""))
                db.commit()
            return QImage()
        if edits:
            img = array_to_qimage(render_edits(qimage_to_array(img), edits))
        if max(img.width(), img.height()) > THUMB:
            img = img.scaled(THUMB, THUMB, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        img = img.convertToFormat(QImage.Format.Format_RGB32)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "JPEG", 84)
        db.execute("INSERT OR REPLACE INTO thumbs VALUES(?,?,?)", (pid, ver, data.data()))
        db.commit()
        return img


class ThumbCache(QObject):
    """Vorschaubilder im Speicher, dahinter die Engine."""
    updated = pyqtSignal()
    LIMIT = 2500

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.pix = OrderedDict()
        self.broken = set()
        engine.ready.connect(self._ready, Qt.ConnectionType.QueuedConnection)
        self.timer = QTimer(self, singleShot=True, interval=25)
        self.timer.timeout.connect(self.updated)
        self.dirty = {}
        self.dirty_timer = QTimer(self, singleShot=True, interval=400)
        self.dirty_timer.timeout.connect(self._refresh_dirty)

    def get(self, pid):
        pm = self.pix.get(pid)
        if pm is not None:
            self.pix.move_to_end(pid)
        return pm

    def invalidate(self, photo):
        """Foto wurde bearbeitet. Das alte Bild bleibt stehen, bis das neue kurz darauf fertig ist."""
        self.broken.discard(photo.id)
        self.dirty[photo.id] = photo
        self.dirty_timer.start()

    def _refresh_dirty(self):
        self.engine.request(list(self.dirty.values()))
        self.dirty.clear()

    def _ready(self, pid, img):
        if img.isNull():
            self.broken.add(pid)
        else:
            self.broken.discard(pid)
            self.pix[pid] = QPixmap.fromImage(img)
            while len(self.pix) > self.LIMIT:
                self.pix.popitem(last=False)
        if not self.timer.isActive():
            self.timer.start()


def star_path(cx, cy, r):
    path = QPainterPath()
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.42
        a = -math.pi / 2 + i * math.pi / 5
        pts.append(QPointF(cx + rad * math.cos(a), cy + rad * math.sin(a)))
    path.addPolygon(QPolygonF(pts))
    path.closeSubpath()
    return path


def draw_stars(p, x, y, count, r=6.0):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(90, 60, 0, 200), 0.8))
    p.setBrush(QColor("#ffcf26"))
    for i in range(count):
        p.drawPath(star_path(x + r + i * (2 * r + 1), y + r, r))
    p.restore()


def draw_play(p, x, y, s=20):
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 165))
    p.drawEllipse(QRectF(x, y, s, s))
    p.setBrush(QColor("white"))
    p.drawPolygon(QPolygonF([QPointF(x + s * .38, y + s * .27), QPointF(x + s * .38, y + s * .73),
                             QPointF(x + s * .74, y + s * .5)]))
    p.restore()


# ---------------------------------------------------------------------------
# Galerie
# ---------------------------------------------------------------------------

class Section:
    __slots__ = ("key", "title", "sub", "photos", "start", "top", "rows")

    def __init__(self, key, title, sub, photos):
        self.key, self.title, self.sub, self.photos = key, title, sub, photos
        self.start = self.top = self.rows = 0


class Grid(QAbstractScrollArea):
    """Die Galerie: rechnet die Positionen aus und zeichnet nur, was sichtbar ist."""
    selectionChanged = pyqtSignal()
    activated = pyqtSignal(object)
    sectionVisible = pyqtSignal(str)
    menuRequested = pyqtSignal(QPoint)
    sizeWheel = pyqtSignal(int)
    HEADER = 30
    PAD = 12
    GAP = 8
    SECTION_GAP = 10
    CAPTION = 17

    def __init__(self, cache):
        super().__init__()
        self.cache = cache
        self.size_px = 140
        self.sections = []
        self.flat = []
        self.index_of = {}
        self.starts = []
        self.tops = []
        self.cols = 1
        self.content_h = 0
        self.selected = set()
        self.current = -1
        self.anchor = -1
        self.press_pos = None
        self.press_item = -1
        self.band = None
        self.last_section = None
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        cache.updated.connect(self.viewport().update)
        self.req = QTimer(self, singleShot=True, interval=10)
        self.req.timeout.connect(self._request_visible)
        self.head_font = QFont(self.font())
        self.head_font.setBold(True)
        self.head_font.setPointSizeF(self.font().pointSizeF() + 1)
        self.sub_font = QFont(self.font())
        self.sub_font.setPointSizeF(self.font().pointSizeF() - 0.5)
        self.caption_font = QFont(self.font())
        self.caption_font.setPointSizeF(self.font().pointSizeF() - 1)

    @property
    def cell_w(self):
        return self.size_px + self.GAP

    @property
    def thumb_h(self):
        return int(self.size_px * 0.8)     # Querformate füllen die Zeile, spart Platz auf kleinen Bildschirmen

    @property
    def cell_h(self):
        return self.thumb_h + self.CAPTION + self.GAP

    # --- Daten und Layout

    def set_sections(self, sections):
        anchor = self._first_visible_anchor()
        current_id = self.flat[self.current].id if 0 <= self.current < len(self.flat) else None
        self.sections = sections
        self.flat = []
        self.starts = []
        for s in sections:
            s.start = len(self.flat)
            self.starts.append(s.start)
            self.flat.extend(s.photos)
        self.index_of = {p.id: i for i, p in enumerate(self.flat)}
        self.selected &= set(self.index_of)
        self.current = self.index_of.get(current_id, -1)
        self.anchor = self.current
        self._layout()
        if anchor:
            i = self.index_of.get(anchor[0])
            if i is not None:
                self.verticalScrollBar().setValue(self.item_rect(i, False).top() - anchor[1])
        self.viewport().update()
        self.selectionChanged.emit()

    def _first_visible_anchor(self):
        if not self.flat:
            return None
        i = self.index_at_y(self.verticalScrollBar().value())
        if i is None or i >= len(self.flat):
            return None
        return self.flat[i].id, self.item_rect(i, False).top() - self.verticalScrollBar().value()

    def set_thumb_size(self, px):
        anchor = self._first_visible_anchor()
        self.size_px = px
        self._layout()
        if anchor:
            i = self.index_of.get(anchor[0])
            if i is not None:
                self.verticalScrollBar().setValue(self.item_rect(i, False).top() - anchor[1])
        self.viewport().update()

    def _layout(self):
        w = self.viewport().width()
        self.cols = max(1, (w - 2 * self.PAD + self.GAP) // self.cell_w)
        y = 4
        self.tops = []
        for s in self.sections:
            s.top = y
            self.tops.append(y)
            s.rows = (len(s.photos) + self.cols - 1) // self.cols
            y += self.HEADER + s.rows * self.cell_h + self.SECTION_GAP
        self.content_h = y
        bar = self.verticalScrollBar()
        bar.setRange(0, max(0, y - self.viewport().height()))
        bar.setPageStep(self.viewport().height())
        bar.setSingleStep(self.cell_h // 2)

    def resizeEvent(self, e):
        anchor = self._first_visible_anchor()
        self._layout()
        if anchor:
            i = self.index_of.get(anchor[0])
            if i is not None:
                self.verticalScrollBar().setValue(self.item_rect(i, False).top() - anchor[1])
        super().resizeEvent(e)

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    def section_of(self, i):
        return bisect.bisect_right(self.starts, i) - 1

    def item_rect(self, i, in_view=True):
        s = self.sections[self.section_of(i)]
        r, c = divmod(i - s.start, self.cols)
        y = s.top + self.HEADER + r * self.cell_h
        if in_view:
            y -= self.verticalScrollBar().value()
        return QRect(self.PAD + c * self.cell_w, y, self.size_px, self.thumb_h + self.CAPTION)

    def index_at_y(self, y):
        """Erstes Foto auf oder nach der Höhe y (Inhaltskoordinaten)."""
        if not self.sections:
            return None
        k = max(0, bisect.bisect_right(self.tops, y) - 1)
        s = self.sections[k]
        r = max(0, (y - s.top - self.HEADER) // self.cell_h)
        if r >= s.rows:
            if k + 1 < len(self.sections):
                return self.sections[k + 1].start
            return len(self.flat) - 1
        return s.start + r * self.cols

    def hit(self, pos):
        """Liefert (Foto-Index oder None, Abschnitt oder None) unter dem Mauszeiger."""
        if not self.sections:
            return None, None
        y = pos.y() + self.verticalScrollBar().value()
        k = bisect.bisect_right(self.tops, y) - 1
        if k < 0:
            return None, None
        s = self.sections[k]
        if y < s.top + self.HEADER:
            return None, s
        r = (y - s.top - self.HEADER) // self.cell_h
        c = (pos.x() - self.PAD) // self.cell_w
        if c < 0 or c >= self.cols or r >= s.rows:
            return None, None
        i = s.start + r * self.cols + c
        if i >= s.start + len(s.photos) or not self.item_rect(i).contains(pos):
            return None, None
        return i, None

    def scroll_to_section(self, key):
        for s in self.sections:
            if s.key == key:
                self.verticalScrollBar().setValue(s.top)
                return True
        return False

    def ensure_visible(self, i):
        r = self.item_rect(i)
        bar = self.verticalScrollBar()
        if r.top() < 0:
            extra = self.HEADER + 4 if i - self.sections[self.section_of(i)].start < self.cols else 4
            bar.setValue(bar.value() + r.top() - extra)
        elif r.bottom() > self.viewport().height():
            bar.setValue(bar.value() + r.bottom() - self.viewport().height() + 6)

    # --- Zeichnen

    def paintEvent(self, ev):
        p = QPainter(self.viewport())
        p.fillRect(ev.rect(), QColor(C_LIBRARY))
        if not self.sections:
            p.setPen(QColor("#666"))
            p.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter,
                       T("Keine Fotos gefunden.\n\nFüge über „Ordner hinzufügen“ einen Foto-Ordner hinzu\n"
                         "oder ändere den Filter."))
            return
        vy = self.verticalScrollBar().value()
        vh = self.viewport().height()
        k = max(0, bisect.bisect_right(self.tops, vy) - 1)
        cell_w, cell_h = self.cell_w, self.cell_h
        sel = self.selected
        flat = self.flat
        if self.last_section != k:
            self.last_section = k
            self.sectionVisible.emit(self.sections[k].key)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        while k < len(self.sections):
            s = self.sections[k]
            k += 1
            if s.top > vy + vh:
                break
            y = s.top - vy
            if y + self.HEADER > 0:
                self._paint_header(p, s, y)
            first = max(0, (vy - s.top - self.HEADER) // cell_h)
            last = min(s.rows - 1, (vy + vh - s.top - self.HEADER) // cell_h)
            for r in range(first, last + 1):
                for c in range(self.cols):
                    i = s.start + r * self.cols + c
                    if i >= s.start + len(s.photos):
                        break
                    self._paint_item(p, flat[i], i, self.PAD + c * cell_w, s.top + self.HEADER + r * cell_h - vy,
                                     flat[i].id in sel)
        if self.band:
            p.setPen(QPen(QColor(C_BLUE), 1))
            p.setBrush(QColor(59, 115, 196, 50))
            p.drawRect(self.band)
        p.end()
        if not self.req.isActive():
            self.req.start()

    def _paint_header(self, p, s, y):
        w = self.viewport().width()
        p.setPen(QColor("#1a1a1a"))
        p.setFont(self.head_font)
        title = p.fontMetrics().elidedText(s.title, Qt.TextElideMode.ElideMiddle, w // 2)
        p.drawText(self.PAD, y, w, self.HEADER - 4, Qt.AlignmentFlag.AlignVCenter, title)
        tw = p.fontMetrics().horizontalAdvance(title)
        p.setFont(self.sub_font)
        p.setPen(QColor("#666"))
        p.drawText(self.PAD + tw + 12, y, w - tw - 30, self.HEADER - 4, Qt.AlignmentFlag.AlignVCenter, s.sub)
        p.setPen(QColor("#c4c7cb"))
        p.drawLine(self.PAD, y + self.HEADER - 3, w - self.PAD, y + self.HEADER - 3)

    def _paint_item(self, p, ph, i, x, y, selected):
        size, box_h = self.size_px, self.thumb_h
        self._paint_caption(p, ph, x, y + box_h, selected)
        pm = self.cache.get(ph.id)
        if pm is None:
            target = QRect(x + 6, y + 6, size - 12, box_h - 12)
            p.fillRect(target, QColor("#e0e0e0") if ph.id not in self.cache.broken else QColor("#c9b6b6"))
            if ph.id in self.cache.broken:
                p.setPen(QColor("#744"))
                p.drawText(target, Qt.AlignmentFlag.AlignCenter, "?")
            if selected:
                p.setPen(QPen(QColor(C_BLUE), 3))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(target.adjusted(-3, -3, 3, 3))
            return
        pw, ph_h = pm.width(), pm.height()
        k = min((size - 8) / pw, (box_h - 8) / ph_h)
        w, h = max(1, int(pw * k)), max(1, int(ph_h * k))
        tx, ty = x + (size - w) // 2, y + box_h - h - 4
        if selected:
            p.fillRect(tx - 4, ty - 4, w + 8, h + 8, QColor(C_BLUE))
        else:
            p.fillRect(tx - 2, ty - 2, w + 5, h + 5, QColor("#a9a9a9"))
            p.fillRect(tx - 3, ty - 3, w + 5, h + 5, QColor("white"))
        p.drawPixmap(QRect(tx, ty, w, h), pm)
        if ph.rating:
            draw_stars(p, tx + 3, ty + h - 15, ph.rating)
        if ph.kind == KIND_VIDEO:
            draw_play(p, tx + 4, ty + 4)
        if i == self.current and self.hasFocus() and not selected:
            p.setPen(QPen(QColor(C_BLUE), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(tx - 4, ty - 4, w + 8, h + 8)

    def _paint_caption(self, p, ph, x, y, selected):
        p.setFont(self.caption_font)
        p.setPen(QColor(C_BLUE) if selected else QColor("#333"))
        text = p.fontMetrics().elidedText(ph.name, Qt.TextElideMode.ElideMiddle, self.size_px - 2)
        p.drawText(QRect(x, y, self.size_px, self.CAPTION), Qt.AlignmentFlag.AlignCenter, text)

    def _request_visible(self):
        if not self.flat:
            return
        vy = self.verticalScrollBar().value()
        vh = self.viewport().height()
        a = self.index_at_y(vy)
        b = self.index_at_y(vy + vh)
        if a is None:
            return
        extra = self.cols * 2
        b = min(len(self.flat), b + self.cols + extra)
        wanted = [self.flat[i] for i in range(a, b)] + [self.flat[i] for i in range(max(0, a - extra), a)]
        self.cache.engine.prioritize([p for p in wanted if p.id not in self.cache.pix and p.id not in self.cache.broken])

    # --- Auswahl

    def selected_photos(self):
        return [p for p in self.flat if p.id in self.selected]

    def select_only(self, i):
        self.selected = {self.flat[i].id}
        self.current = self.anchor = i
        self.viewport().update()
        self.selectionChanged.emit()

    def select_photo(self, pid):
        i = self.index_of.get(pid)
        if i is not None:
            self.select_only(i)
            self.ensure_visible(i)

    def clear_selection(self):
        self.selected = set()
        self.viewport().update()
        self.selectionChanged.emit()

    def select_all(self):
        self.selected = set(self.index_of)
        self.viewport().update()
        self.selectionChanged.emit()

    def _select_range(self, a, b, add=False):
        lo, hi = sorted((a, b))
        ids = {self.flat[i].id for i in range(lo, hi + 1)}
        self.selected = (self.selected | ids) if add else ids

    def mousePressEvent(self, e):
        self.setFocus()
        pos = e.position().toPoint()
        i, section = self.hit(pos)
        mods = e.modifiers()
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        if e.button() == Qt.MouseButton.RightButton:
            if i is not None and self.flat[i].id not in self.selected:
                self.select_only(i)
            self.menuRequested.emit(e.globalPosition().toPoint())
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        self.press_pos = pos
        self.press_item = -1 if i is None else i
        if section is not None:     # Klick auf die Überschrift wählt den ganzen Ordner
            ids = {p.id for p in section.photos}
            self.selected = self.selected | ids if ctrl else ids
            self.current = self.anchor = section.start
        elif i is None:
            if not ctrl:
                self.selected = set()
            self.band = QRect(pos, QSize(0, 0))
        elif shift and self.anchor >= 0:
            self._select_range(self.anchor, i, ctrl)
            self.current = i
        elif ctrl:
            self.selected ^= {self.flat[i].id}
            self.current = self.anchor = i
        else:
            if self.flat[i].id not in self.selected:
                self.selected = {self.flat[i].id}
            self.current = self.anchor = i
        self.viewport().update()
        self.selectionChanged.emit()

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton) or self.press_pos is None:
            return
        pos = e.position().toPoint()
        if self.band is not None:
            self.band = QRect(self.press_pos, pos).normalized()
            self._band_select()
            self.viewport().update()
            return
        if self.press_item >= 0 and (pos - self.press_pos).manhattanLength() >= QApplication.startDragDistance():
            self._start_drag()

    def _band_select(self):
        vy = self.verticalScrollBar().value()
        a = self.index_at_y(self.band.top() + vy)
        b = self.index_at_y(self.band.bottom() + vy)
        if a is None:
            return
        ids = set()
        for i in range(a, min(len(self.flat), b + self.cols)):
            if self.item_rect(i).intersects(self.band):
                ids.add(self.flat[i].id)
        if ids != self.selected:
            self.selected = ids
            self.selectionChanged.emit()

    def mouseReleaseEvent(self, e):
        pos = e.position().toPoint()
        if self.press_pos is not None and self.band is None and self.press_item >= 0 and not e.modifiers():
            if (pos - self.press_pos).manhattanLength() < QApplication.startDragDistance():
                self.select_only(self.press_item)   # Klick in eine Mehrfachauswahl
        self.band = None
        self.press_pos = None
        self.viewport().update()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.sizeWheel.emit(int(e.angleDelta().y() / 120 * 16))
        else:
            super().wheelEvent(e)

    def mouseDoubleClickEvent(self, e):
        i, _ = self.hit(e.position().toPoint())
        if i is not None:
            self.activated.emit(self.flat[i])

    def _start_drag(self):
        photos = self.selected_photos()
        self.press_pos = None
        if not photos:
            return
        mime = QMimeData()
        mime.setData(MIME, QByteArray(",".join(str(p.id) for p in photos).encode()))
        mime.setUrls([QUrl.fromLocalFile(p.path) for p in photos[:500]])
        drag = QDrag(self)
        drag.setMimeData(mime)
        pm = self.cache.get(photos[0].id)
        canvas = QPixmap(96, 96)
        canvas.fill(Qt.GlobalColor.transparent)
        q = QPainter(canvas)
        if pm:
            s = pm.scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            q.drawPixmap(0, 0, s)
        q.setRenderHint(QPainter.RenderHint.Antialiasing)
        q.setBrush(QColor(C_BLUE))
        q.setPen(Qt.PenStyle.NoPen)
        q.drawEllipse(QRectF(62, 62, 32, 32))
        q.setPen(QColor("white"))
        q.drawText(QRectF(62, 62, 32, 32), Qt.AlignmentFlag.AlignCenter, str(len(photos)))
        q.end()
        drag.setPixmap(canvas)
        # Nur "Kopieren" nach außen: So kann ein Ziehen in den Dateimanager nichts wegbewegen.
        drag.exec(Qt.DropAction.CopyAction)

    def keyPressEvent(self, e):
        key = e.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if 0 <= self.current < len(self.flat):
                self.activated.emit(self.flat[self.current])
            return
        if key == Qt.Key.Key_Escape:
            self.clear_selection()
            return
        target = self._nav_target(key)
        if target is None:
            super().keyPressEvent(e)
            return
        if not self.flat:
            return
        target = max(0, min(len(self.flat) - 1, target))
        if e.modifiers() & Qt.KeyboardModifier.ShiftModifier and self.anchor >= 0:
            self._select_range(self.anchor, target)
            self.current = target
        else:
            self.selected = {self.flat[target].id}
            self.current = self.anchor = target
        self.ensure_visible(target)
        self.viewport().update()
        self.selectionChanged.emit()

    def _nav_target(self, key):
        cur = self.current if 0 <= self.current < len(self.flat) else -1
        if key == Qt.Key.Key_Home:
            return 0
        if key == Qt.Key.Key_End:
            return len(self.flat) - 1
        if key not in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
                       Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
            return None
        if cur < 0:
            return 0
        if key == Qt.Key.Key_Left:
            return cur - 1
        if key == Qt.Key.Key_Right:
            return cur + 1
        if key == Qt.Key.Key_Up:
            return self._row_step(cur, -1)
        if key == Qt.Key.Key_Down:
            return self._row_step(cur, 1)
        rows = max(1, self.viewport().height() // self.cell_h)
        step = -1 if key == Qt.Key.Key_PageUp else 1
        for _ in range(rows):
            cur = self._row_step(cur, step)
            cur = max(0, min(len(self.flat) - 1, cur))
        return cur

    def _row_step(self, i, step):
        """Eine Zeile hoch oder runter, auch über Abschnittsgrenzen, in derselben Spalte."""
        k = self.section_of(i)
        s = self.sections[k]
        r, c = divmod(i - s.start, self.cols)
        if step < 0:
            if r > 0:
                return i - self.cols
            if k == 0:
                return i
            s = self.sections[k - 1]
            return s.start + min((s.rows - 1) * self.cols + c, len(s.photos) - 1)
        if (r + 1) * self.cols < len(s.photos):
            return min(i + self.cols, s.start + len(s.photos) - 1)
        if k + 1 >= len(self.sections):
            return i
        s = self.sections[k + 1]
        return s.start + min(c, len(s.photos) - 1)


class Tray(QWidget):
    """Die Foto-Ablage unten links: zeigt die aktuelle Auswahl."""

    def __init__(self, cache, grid):
        super().__init__()
        self.cache, self.grid = cache, grid
        self.setMinimumHeight(56)
        self.setMinimumWidth(180)
        self.photos = []
        cache.updated.connect(self.update)
        grid.selectionChanged.connect(self.refresh)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def refresh(self):
        ids = self.grid.selected
        self.count = len(ids)
        flat = self.grid.flat
        if len(ids) <= 40:
            self.photos = [p for p in (flat[self.grid.index_of[i]] for i in ids if i in self.grid.index_of)]
        else:
            self.photos = self.grid.selected_photos()[:40]
        need = [p for p in self.photos if p.id not in self.cache.pix and p.id not in self.cache.broken]
        if need:
            self.cache.engine.prioritize(need)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.fillRect(r, QColor("#f7f8fa"))
        p.setPen(QColor("#a3abb5"))
        p.drawRect(r)
        if not self.photos:
            p.setPen(QColor("#777"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, T("Ablage: nichts ausgewählt"))
            return
        x, y, s = 6, 5, self.height() - 10
        text_w = 62
        for ph in self.photos:
            if x + s + text_w > self.width():
                break
            pm = self.cache.get(ph.id)
            if pm:
                k = s / max(pm.width(), pm.height())
                w, h = int(pm.width() * k), int(pm.height() * k)
                p.drawPixmap(QRect(x + (s - w) // 2, y + (s - h) // 2, w, h), pm)
            else:
                p.fillRect(x, y, s, s, QColor("#ddd"))
            x += s + 3
        p.setPen(QColor("#333"))
        p.drawText(QRect(self.width() - text_w, 0, text_w - 6, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                   photos_text(self.count))


class FolderTree(QTreeWidget):
    """Die Ordnerliste links. Fotos lassen sich direkt hineinziehen."""
    dropped = pyqtSignal(list, str, bool)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setUniformRowHeights(True)
        self.setIndentation(13)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(False)
        self.signature = None
        self.items = {}

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(MIME):
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()

    def dragMoveEvent(self, e):
        item = self.itemAt(e.position().toPoint())
        if e.mimeData().hasFormat(MIME) and item:
            self.setCurrentItem(item)
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        item = self.itemAt(e.position().toPoint())
        if not item or not e.mimeData().hasFormat(MIME):
            return
        ids = [int(x) for x in bytes(e.mimeData().data(MIME)).decode().split(",")]
        copy = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()
        self.dropped.emit(ids, item.data(0, Qt.ItemDataRole.UserRole), copy)

    def rebuild(self, roots, folders, counts, offline):
        signature = (tuple(roots), tuple(folders), tuple(sorted(offline)))
        if signature == self.signature:
            for path, item in self.items.items():
                item.setText(0, self._label(path, counts, offline, path in roots))
            return
        self.signature = signature
        expanded = {p for p, it in self.items.items() if it.isExpanded()}
        first = not self.items
        self.clear()
        self.items = {}
        for root in sorted(roots, key=str.casefold):
            top = QTreeWidgetItem(self, [self._label(root, counts, offline, True)])
            top.setData(0, Qt.ItemDataRole.UserRole, root)
            top.setToolTip(0, root)
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            self.items[root] = top
        for path in sorted(folders, key=lambda f: [s.casefold() for s in f.split(os.sep)]):
            if path in self.items:
                continue
            parent = self.items.get(os.path.dirname(path))
            if parent is None:
                continue
            item = QTreeWidgetItem(parent, [self._label(path, counts, offline, False)])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setToolTip(0, path)
            self.items[path] = item
        for path, item in self.items.items():
            item.setExpanded(path in expanded or (first and path in roots))

    @staticmethod
    def _label(path, counts, offline, is_root):
        name = os.path.basename(path) or path
        if path in offline:
            return T("{name} (nicht erreichbar)", name=name)
        n = counts.get(path, 0)
        return f"{name} ({n})" if n else name


# ---------------------------------------------------------------------------
# Großansicht und Bearbeitung
# ---------------------------------------------------------------------------

class Canvas(QWidget):
    """Zeigt das Bild, zoomt stufenlos und zeichnet den Zuschnitt."""
    zoomRequested = pyqtSignal(QPointF)
    wheelZoom = pyqtSignal(float, QPointF)
    menuRequested = pyqtSignal(QPoint)

    def __init__(self):
        super().__init__()
        self.image = None
        self.video = False
        self.zoom = None        # None = eingepasst, sonst Bildschirmpixel je Pixel des angezeigten Bildes
        self.full = None        # volle Auflösung, sobald sie geladen ist
        self.offset = QPointF(0, 0)
        self.drag_from = None
        self.crop = None
        self.crop_ratio = None
        self.crop_mode = None
        self.grid_lines = False
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def set_image(self, img):
        if self.zoom is not None and self.full is None and (
                img is None or self.image is None or img.size() != self.image.size()):
            self.zoom = None    # Bildformat hat sich geändert (Drehen, Zuschnitt): wieder einpassen
        self.image = img
        self.update()

    def shown(self):
        return self.full if self.full is not None else self.image

    def fit_scale(self):
        r = self.image_rect()
        img = self.shown()
        return r.width() / img.width() if img is not None and not img.isNull() and img.width() else 1.0

    def set_zoom(self, zoom, anchor):
        """Zoomt so, dass der Bildpunkt unter anchor an seinem Platz bleibt."""
        img = self.shown()
        if img is None or img.isNull():
            return
        old = self.zoom if self.zoom is not None else self.fit_scale()
        origin = self.offset if self.zoom is not None else self.image_rect().topLeft()
        fit = self.fit_scale()
        if zoom <= fit * 1.001:
            self.reset_zoom()
            return
        self.offset = anchor - (anchor - origin) * (zoom / old)
        self.zoom = zoom
        self.update()

    def swap_full(self, full):
        """Die volle Auflösung ist da: gleiche Stelle, gleiche Größe, nur schärfer."""
        ratio = full.width() / max(1, self.image.width())
        self.zoom /= ratio
        self.full = full
        self.update()

    def drop_full(self):
        """Das Bild wurde bearbeitet: zurück auf die Vorschau, bis die volle Auflösung neu gerechnet ist."""
        if self.full is not None:
            self.zoom *= self.full.width() / max(1, self.image.width())
            self.full = None

    def reset_zoom(self):
        self.zoom = None
        self.full = None
        self.drag_from = None
        self.update()

    def image_rect(self):
        if self.image is None or self.image.isNull():
            return QRectF()
        iw, ih = self.image.width(), self.image.height()
        k = min(self.width() / iw, self.height() / ih, 1.0 if max(iw, ih) >= 1000 else 8.0)
        w, h = iw * k, ih * k
        return QRectF((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C_EDIT_BG))
        if self.image is None or self.image.isNull():
            return
        if self.zoom is not None:
            self._clamp_offset()
            img = self.shown()
            if self.zoom < 2:   # stärker vergrößert zeigt echte Pixel statt Matsch
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(QRectF(self.offset.x(), self.offset.y(), img.width() * self.zoom, img.height() * self.zoom), img)
            return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = self.image_rect()
        p.drawImage(r, self.image)
        if self.video:
            draw_play(p, r.center().x() - 32, r.center().y() - 32, 64)
        if self.crop is not None:
            self._paint_crop(p, r)
        elif self.grid_lines:
            p.setPen(QPen(QColor(255, 255, 255, 110), 1))
            for i in range(1, 8):
                x = r.left() + r.width() * i / 8
                y = r.top() + r.height() * i / 8
                p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
                p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))

    def _crop_rect(self, r):
        c = self.crop
        return QRectF(r.left() + c[0] * r.width(), r.top() + c[1] * r.height(),
                      (c[2] - c[0]) * r.width(), (c[3] - c[1]) * r.height())

    def _paint_crop(self, p, r):
        c = self._crop_rect(r)
        shade = QPainterPath()
        shade.addRect(r)
        hole = QPainterPath()
        hole.addRect(c)
        p.fillPath(shade.subtracted(hole), QColor(0, 0, 0, 150))
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        for i in (1, 2):
            x = c.left() + c.width() * i / 3
            y = c.top() + c.height() * i / 3
            p.drawLine(QPointF(x, c.top()), QPointF(x, c.bottom()))
            p.drawLine(QPointF(c.left(), y), QPointF(c.right(), y))
        p.setPen(QPen(QColor("white"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(c)
        p.setBrush(QColor("white"))
        for pt in (c.topLeft(), c.topRight(), c.bottomLeft(), c.bottomRight()):
            p.drawRect(QRectF(pt.x() - 4, pt.y() - 4, 8, 8))

    def _crop_handle(self, pos):
        c = self._crop_rect(self.image_rect())
        for name, pt in (("tl", c.topLeft()), ("tr", c.topRight()), ("bl", c.bottomLeft()), ("br", c.bottomRight())):
            if (pt - pos).manhattanLength() < 14:
                return name
        whole = self.crop[0] <= 0.001 and self.crop[1] <= 0.001 and self.crop[2] >= 0.999 and self.crop[3] >= 0.999
        return "move" if c.contains(pos) and not whole else "new"

    def _clamp_offset(self):
        img = self.shown()
        w, h = img.width() * self.zoom, img.height() * self.zoom
        x = (self.width() - w) / 2 if w <= self.width() else min(0, max(self.width() - w, self.offset.x()))
        y = (self.height() - h) / 2 if h <= self.height() else min(0, max(self.height() - h, self.offset.y()))
        self.offset = QPointF(x, y)

    def wheelEvent(self, e):
        steps = e.angleDelta().y() / 120
        if steps and self.crop is None and not self.video:
            self.wheelZoom.emit(1.25 ** steps, e.position())

    def contextMenuEvent(self, e):
        if self.crop is None:
            self.menuRequested.emit(e.globalPos())

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.crop is not None:
            r = self.image_rect()
            self.crop_mode = self._crop_handle(pos)
            nx, ny = (pos.x() - r.left()) / r.width(), (pos.y() - r.top()) / r.height()
            self.crop_start = (min(1, max(0, nx)), min(1, max(0, ny)), list(self.crop))
            if self.crop_mode == "new":
                self.crop = [self.crop_start[0], self.crop_start[1], self.crop_start[0], self.crop_start[1]]
            return
        if self.zoom is not None:
            self.drag_from = pos - self.offset
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self.crop is not None:
            if not e.buttons():
                shape = {"tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
                         "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
                         "move": Qt.CursorShape.SizeAllCursor, "new": Qt.CursorShape.CrossCursor}
                self.setCursor(shape[self._crop_handle(pos)])
            elif self.crop_mode:
                self._drag_crop(pos)
            return
        if self.drag_from is not None and self.zoom is not None:
            self.offset = pos - self.drag_from
            self.update()
        elif self.zoom is not None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.unsetCursor()

    def _drag_crop(self, pos):
        r = self.image_rect()
        nx = min(1.0, max(0.0, (pos.x() - r.left()) / r.width()))
        ny = min(1.0, max(0.0, (pos.y() - r.top()) / r.height()))
        sx, sy, start = self.crop_start
        x0, y0, x1, y1 = start
        mode = self.crop_mode
        if mode == "move":
            w, h = x1 - x0, y1 - y0
            x0 = min(1 - w, max(0, x0 + nx - sx))
            y0 = min(1 - h, max(0, y0 + ny - sy))
            self.crop = [x0, y0, x0 + w, y0 + h]
            self.update()
            return
        fx, fy = {"tl": (x1, y1), "tr": (x0, y1), "bl": (x1, y0), "br": (x0, y0), "new": (sx, sy)}[mode]
        if self.crop_ratio:
            # Das Seitenverhältnis gilt in Pixeln, die Koordinaten sind aber relativ zum Bild.
            aspect = self.crop_ratio * r.height() / r.width()
            w, h = abs(nx - fx), abs(ny - fy)
            if h == 0 or w / max(h, 1e-6) > aspect:
                h = w / aspect
            else:
                w = h * aspect
            limit_w = 1 - fx if nx >= fx else fx
            limit_h = 1 - fy if ny >= fy else fy
            k = min(1.0, limit_w / max(w, 1e-6), limit_h / max(h, 1e-6))
            w, h = w * k, h * k
            nx = fx + w if nx >= fx else fx - w
            ny = fy + h if ny >= fy else fy - h
        self.crop = [min(fx, nx), min(fy, ny), max(fx, nx), max(fy, ny)]
        self.update()

    def mouseReleaseEvent(self, _):
        self.crop_mode = None
        if self.drag_from is not None:
            self.drag_from = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, e):
        if self.crop is None:
            self.zoomRequested.emit(e.position())


class Filmstrip(QWidget):
    """Der Filmstreifen über dem Bild."""
    clicked = pyqtSignal(int)

    def __init__(self, cache):
        super().__init__()
        self.cache = cache
        self.seq = []
        self.index = 0
        self.setFixedHeight(62)
        self.setObjectName("filmbar")
        cache.updated.connect(self.update)

    def set_position(self, seq, index):
        self.seq, self.index = seq, index
        self.update()

    def _slots(self):
        w = 60
        n = self.width() // w
        half = n // 2
        for k in range(-half, half + 1):
            i = self.index + k
            if 0 <= i < len(self.seq):
                yield i, self.width() // 2 + k * w - w // 2, w

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1f1f1f"))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        need = []
        for i, x, w in self._slots():
            ph = self.seq[i]
            pm = self.cache.get(ph.id)
            s = 52
            if pm:
                k = s / max(pm.width(), pm.height())
                tw, th = int(pm.width() * k), int(pm.height() * k)
                p.drawPixmap(QRect(x + (w - tw) // 2, 5 + (s - th) // 2, tw, th), pm)
            else:
                p.fillRect(x + 4, 5, s, s, QColor("#3a3a3a"))
                if ph.id not in self.cache.broken:
                    need.append(ph)
            if i == self.index:
                p.setPen(QPen(QColor("#8fb8f0"), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(x + 2, 3, w - 4, 56)
        if need:
            self.cache.engine.prioritize(need)

    def mousePressEvent(self, e):
        x = int(e.position().x())
        for i, sx, w in self._slots():
            if sx <= x < sx + w:
                self.clicked.emit(i)
                return


class PreviewLoader(QThread):
    """Lädt Großansichten vor, aktuelles Bild zuerst."""
    ready = pyqtSignal(int, QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cond = threading.Condition()
        self.queue = []
        self.stopped = False

    def request(self, jobs):
        with self.cond:
            self.queue = list(jobs)
            self.cond.notify()

    def shutdown(self):
        with self.cond:
            self.stopped = True
            self.cond.notify()
        self.wait(1500)

    def run(self):
        while True:
            with self.cond:
                while not self.queue and not self.stopped:
                    self.cond.wait()
                if self.stopped:
                    return
                pid, path, kind = self.queue.pop(0)
            try:
                img = load_qimage(path, kind, PREVIEW)
            except Exception:
                img = QImage()
            self.ready.emit(pid, img)


class PathLabel(QLabel):
    """Zeigt einen Pfad. Passt er nicht in die Zeile, wird die Mitte gekürzt, der Tooltip bleibt vollständig."""

    def __init__(self):
        super().__init__()
        self.path = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def set_path(self, path):
        self.path = path
        self.setToolTip(path)
        self._fit()

    def _fit(self):
        self.setText(self.fontMetrics().elidedText(self.path, Qt.TextElideMode.ElideMiddle, self.width() - 2))

    def resizeEvent(self, e):
        self._fit()
        super().resizeEvent(e)


class Dial(QWidget):
    """Beschrifteter Schieberegler. Doppelklick stellt ihn zurück."""
    moved = pyqtSignal(int)
    pressed = pyqtSignal()
    released = pyqtSignal()

    def __init__(self, title, lo, hi):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(1)
        self.label = QLabel(title)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(lo, hi)
        lay.addWidget(self.label)
        lay.addWidget(self.slider)
        self.slider.valueChanged.connect(self.moved)
        self.slider.sliderPressed.connect(self.pressed)
        self.slider.sliderReleased.connect(self.released)
        self.slider.installEventFilter(self)

    def set_quiet(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(int(v))
        self.slider.blockSignals(False)

    def eventFilter(self, obj, ev):
        if ev.type() == ev.Type.MouseButtonDblClick:
            self.pressed.emit()
            self.slider.setValue(0)
            self.released.emit()
            return True
        return False


# Die wichtigsten Felder oben im EXIF-Reiter: Überschrift, dann (Bezeichnung, Felder, Einheit).
# Von mehreren Feldern gilt das erste vorhandene.
EXIF_SECTIONS = (
    ("Aufnahme", (
        ("Datum", ("DateTimeOriginal", "CreateDate"), ""),
        ("Hersteller", ("Make",), ""),
        ("Kamera", ("Model",), ""),
        ("Bildgröße", ("ImageSize",), ""),
        ("Dauer", ("Duration",), ""),
        ("Bildrate", ("VideoFrameRate",), " fps"),
        ("Belichtung", ("ExposureTime",), " s"),
        ("Blende", ("FNumber",), ""),
        ("ISO", ("ISO",), ""),
        ("Brennweite", ("FocalLength",), ""),
        ("Kleinbild", ("FocalLengthIn35mmFormat",), ""),
        ("Korrektur", ("ExposureCompensation",), " EV"),
        ("Weißabgleich", ("WhiteBalance",), ""),
        ("Firmware", ("Software",), ""),
    )),
    ("Ort", (
        ("Position", ("GPSPosition",), ""),
        ("Höhe ü. Meer", ("AbsoluteAltitude",), " m"),
        ("Höhe ü. Meer", ("GPSAltitude",), ""),
        ("Höhe ü. Start", ("RelativeAltitude",), " m"),
    )),
    ("Drohne", (
        ("Gieren", ("FlightYawDegree",), "°"),
        ("Nicken", ("FlightPitchDegree",), "°"),
        ("Rollen", ("FlightRollDegree",), "°"),
        ("Gimbal Gieren", ("GimbalYawDegree",), "°"),
        ("Gimbal Nicken", ("GimbalPitchDegree",), "°"),
        ("Gimbal Rollen", ("GimbalRollDegree",), "°"),
        ("Tempo X", ("SpeedX",), " m/s"),
        ("Tempo Y", ("SpeedY",), " m/s"),
        ("Tempo Z", ("SpeedZ",), " m/s"),
    )),
)


def read_exif(path):
    """Liest alle Metadaten mit exiftool. Gibt ein Wörterbuch zurück oder einen Fehlertext."""
    cmd = tool("exiftool") + ["-j", "-G1", "-c", "%.6f", "-d", T("%d.%m.%Y") + " %H:%M:%S", path]
    try:
        run = subprocess.run(cmd, capture_output=True, timeout=20, **NO_WINDOW)
        return json.loads(run.stdout)[0]
    except FileNotFoundError:
        return T("exiftool ist nicht installiert (Paket perl-image-exiftool).")
    except subprocess.TimeoutExpired:
        return T("exiftool hat zu lange gebraucht.")
    except (OSError, ValueError, IndexError):
        return T("Die Metadaten konnten nicht gelesen werden.")


def exif_html(data):
    """Baut den Text für den EXIF-Reiter. Die Werte stammen aus der Datei und werden maskiert."""
    if isinstance(data, str):
        return f"<p>{html.escape(data)}</p>"

    def head(title):
        return f"<p style='margin:9px 0 2px 0'><b>{html.escape(title)}</b></p>"

    def table(rows):
        cells = "".join(f"<tr><td style='color:#555;padding-right:6px'>{html.escape(k)}</td>"
                        f"<td>{html.escape(v)}</td></tr>" for k, v in rows)
        return f"<table cellspacing='0' cellpadding='1'>{cells}</table>"

    fields = {}
    groups = {}
    for key, value in data.items():
        group, sep, tag = key.partition(":")
        if not sep or group in ("ExifTool", "System"):
            continue
        value = str(value)
        fields.setdefault(tag, value)
        if not value.startswith("(Binary data"):
            groups.setdefault(group, []).append((tag, value))
    out = []
    for title, entries in EXIF_SECTIONS:
        rows, seen = [], set()
        for label, tags, unit in entries:
            value = next((fields[t] for t in tags if t in fields), None)
            if value is None or label in seen:
                continue
            seen.add(label)
            rows.append((T(label), value.replace(" Above Sea Level", "") + unit))
        if rows:
            out.append(head(T(title)) + table(rows))
    if not groups:
        return T("<p>Keine Metadaten gefunden.</p>")
    out.append("<hr>" + head(T("Alle Daten")))
    for group, rows in groups.items():
        out.append(f"<p style='margin:7px 0 1px 0;color:#555'><i>{html.escape(group)}</i></p>" + table(rows))
    return "".join(out)


class EditView(QWidget):
    """Die Großansicht mit den Schnellkorrekturen."""
    back = pyqtSignal(object)
    fullReady = pyqtSignal(object, QImage)
    exifReady = pyqtSignal(str, object)
    TAB_EXIF = 2
    MAX_ZOOM = 8.0      # in Bezug auf die volle Auflösung

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.seq = []
        self.index = 0
        self.photo = None
        self.base = None
        self.base_id = None
        self.previews = OrderedDict()
        self.geo_cache = None
        self.undo_stack = {}
        self.loader = PreviewLoader(self)
        self.loader.ready.connect(self._preview_ready)
        self.loader.start()
        self.render_timer = QTimer(self, singleShot=True, interval=0)
        self.render_timer.timeout.connect(self.render)
        self.full_token = None
        self.full_sizes = {}
        self.fullReady.connect(self._full_ready, Qt.ConnectionType.QueuedConnection)
        self.full_timer = QTimer(self, singleShot=True, interval=300)
        self.full_timer.timeout.connect(self._request_full)
        self.exif_cache = OrderedDict()
        self.wanted_tab = 0     # bleibt erhalten, wenn ein Video die Korrekturen sperrt
        self.exifReady.connect(self._exif_ready, Qt.ConnectionType.QueuedConnection)
        self.exif_timer = QTimer(self, singleShot=True, interval=120)  # nicht beim schnellen Durchblättern
        self.exif_timer.timeout.connect(self._read_exif)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        film = QWidget()
        film.setObjectName("filmbar")
        film.setStyleSheet("#filmbar { background: #1f1f1f; }")
        fl = QHBoxLayout(film)
        fl.setContentsMargins(8, 0, 0, 0)
        self.back_btn = QPushButton(T("◀  Zurück zur Bibliothek"))
        self.back_btn.clicked.connect(self.leave)
        fl.addWidget(self.back_btn)
        self.film = Filmstrip(win.cache)
        self.film.clicked.connect(self.goto)
        fl.addWidget(self.film, 1)
        outer.addWidget(film)

        mid = QHBoxLayout()
        mid.setSpacing(0)
        outer.addLayout(mid, 1)
        panel = QWidget()
        panel.setObjectName("editpanel")
        panel.setFixedWidth(276)
        mid.addWidget(panel)
        self.canvas = Canvas()
        self.canvas.zoomRequested.connect(self.toggle_zoom)
        self.canvas.wheelZoom.connect(self.zoom_by)
        self.canvas.menuRequested.connect(win.photo_menu)
        mid.addWidget(self.canvas, 1)

        pl = QVBoxLayout(panel)
        pl.setContentsMargins(6, 6, 6, 6)
        self.tabs = QTabWidget()
        pl.addWidget(self.tabs, 1)

        fix = QWidget()
        fv = QVBoxLayout(fix)
        fv.setSpacing(5)
        self.crop_btn = QPushButton(T("Zuschneiden (C)"))
        self.crop_btn.clicked.connect(self.start_crop)
        fv.addWidget(self.crop_btn)
        self.crop_box = QWidget()
        cb = QVBoxLayout(self.crop_box)
        cb.setContentsMargins(0, 0, 0, 0)
        self.ratio = QComboBox()
        self.ratio.addItem(T("Freies Format"), None)
        for text, val in ((T("Originalformat"), -1.0), ("3 : 2", 1.5), ("2 : 3", 2 / 3), ("4 : 3", 4 / 3), ("3 : 4", .75),
                          ("1 : 1", 1.0), ("16 : 9", 16 / 9)):
            self.ratio.addItem(text, val)
        self.ratio.currentIndexChanged.connect(self._ratio_changed)
        cb.addWidget(self.ratio)
        row = QHBoxLayout()
        ok = QPushButton(T("Übernehmen"))
        ok.clicked.connect(self.apply_crop)
        no = QPushButton(T("Abbrechen"))
        no.clicked.connect(self.cancel_crop)
        row.addWidget(ok)
        row.addWidget(no)
        cb.addLayout(row)
        rem = QPushButton(T("Zuschnitt entfernen"))
        rem.clicked.connect(self.remove_crop)
        cb.addWidget(rem)
        self.crop_box.hide()
        fv.addWidget(self.crop_box)
        self.auto_btn = QPushButton(T("Automatik (A)"))
        self.auto_btn.clicked.connect(self.auto_all)
        self.contrast_btn = QPushButton(T("Auto-Kontrast"))
        self.contrast_btn.setCheckable(True)
        self.contrast_btn.clicked.connect(self.toggle_contrast)
        self.color_btn = QPushButton(T("Auto-Farbe"))
        self.color_btn.setCheckable(True)
        self.color_btn.clicked.connect(self.toggle_color)
        for b in (self.auto_btn, self.contrast_btn, self.color_btn):
            fv.addWidget(b)
        self.dials = {}
        self.d_fill = self._dial(fv, "fill", T("Aufhellen"), 0, 100, 100)
        self.d_str = self._dial(fv, "straighten", T("Begradigen"), -100, 100, 10)
        self.d_str.pressed.connect(lambda: self._grid(True))
        self.d_str.released.connect(lambda: self._grid(False))
        fv.addStretch(1)
        self.tabs.addTab(fix, T("Korrekturen"))

        tune = QWidget()
        tv = QVBoxLayout(tune)
        tv.setSpacing(5)
        self._dial(tv, "high", T("Lichter"), 0, 100, 100)
        self._dial(tv, "shad", T("Schatten"), 0, 100, 100)
        self._dial(tv, "temp", T("Farbtemperatur"), -100, 100, 100)
        self._dial(tv, "sat", T("Sättigung"), -100, 100, 100)
        tv.addStretch(1)
        self.tabs.addTab(tune, T("Feinabstimmung"))

        self.exif_view = QTextBrowser()
        self.exif_view.setFrameShape(QFrame.Shape.NoFrame)
        self.exif_view.setStyleSheet("QTextBrowser { background: #f2f3f5; color: #1c1c1c; font-size: 8pt; }")
        self.exif_view.setOpenLinks(False)
        self.tabs.addTab(self.exif_view, "EXIF")
        self.tabs.currentChanged.connect(lambda i: self._show_exif())
        self.tabs.tabBarClicked.connect(self._tab_clicked)

        row = QHBoxLayout()
        self.undo_btn = QPushButton(T("Rückgängig"))
        self.undo_btn.clicked.connect(self.undo)
        self.reset_btn = QPushButton(T("Alles zurück"))
        self.reset_btn.clicked.connect(self.reset_edits)
        row.addWidget(self.undo_btn)
        row.addWidget(self.reset_btn)
        pl.addLayout(row)

        bar = QWidget()
        bar.setObjectName("editbar")
        barv = QVBoxLayout(bar)
        barv.setContentsMargins(8, 3, 8, 3)
        barv.setSpacing(3)
        pathrow = QHBoxLayout()
        self.path_label = PathLabel()
        pathrow.addWidget(self.path_label, 1)
        self.copy_btn = QPushButton(T("Pfad kopieren"))
        self.copy_btn.setToolTip(T("Vollständige Adresse in die Zwischenablage kopieren"))
        self.copy_btn.clicked.connect(self.copy_path)
        pathrow.addWidget(self.copy_btn)
        barv.addLayout(pathrow)
        bl = QHBoxLayout()
        barv.addLayout(bl)
        self.info = QLabel()
        bl.addWidget(self.info, 1)
        for text, tip, fn in (("⟲", T("Links drehen (Strg+Umschalt+R)"), lambda: win.rotate(-1)),
                              ("⟳", T("Rechts drehen (Strg+R)"), lambda: win.rotate(1))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            bl.addWidget(b)
        self.star_btn = QPushButton("★")
        self.star_btn.setToolTip(T("Stern setzen oder entfernen (Tasten 0 bis 5)"))
        self.star_btn.clicked.connect(lambda: win.set_rating(0 if self.photo and self.photo.rating else 1))
        bl.addWidget(self.star_btn)
        out = QPushButton("−")
        out.setToolTip(T("Verkleinern (Taste − oder Mausrad)"))
        out.clicked.connect(lambda: self.zoom_by(1 / 1.25))
        bl.addWidget(out)
        self.zoom_label = QLabel("100 %")
        self.zoom_label.setFixedWidth(46)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(self.zoom_label)
        into = QPushButton("+")
        into.setToolTip(T("Vergrößern (Taste + oder Mausrad)"))
        into.clicked.connect(lambda: self.zoom_by(1.25))
        bl.addWidget(into)
        fit = QPushButton(T("Einpassen"))
        fit.setToolTip(T("Ganzes Bild zeigen (Taste F)"))
        fit.clicked.connect(self.zoom_fit)
        bl.addWidget(fit)
        zoom = QPushButton("100 % (Z)")
        zoom.clicked.connect(lambda: self.toggle_zoom(None))
        bl.addWidget(zoom)
        self.open_with_btn = QPushButton(T("Öffnen mit"))
        self.open_with_btn.setMenu(QMenu(self.open_with_btn))
        self.open_with_btn.menu().aboutToShow.connect(
            lambda: win.fill_open_with(self.open_with_btn.menu()))
        bl.addWidget(self.open_with_btn)
        self.export_btn = QPushButton(T("Exportieren …"))
        self.export_btn.clicked.connect(win.export_selection)
        bl.addWidget(self.export_btn)
        outer.addWidget(bar)
        for w in self.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _dial(self, layout, key, title, lo, hi, scale):
        d = Dial(title, lo, hi)
        d.moved.connect(lambda v, k=key, s=scale: self._set_value(k, v / s))
        d.pressed.connect(self._push_undo)
        layout.addWidget(d)
        self.dials[key] = (d, scale)
        return d

    def _grid(self, on):
        self.canvas.grid_lines = on
        self.canvas.update()

    # --- Navigation

    def open(self, seq, photo):
        self.seq = list(seq)
        self.index = self.seq.index(photo) if photo in self.seq else 0
        self.show_current()
        self.setFocus()

    def show_current(self):
        if not self.seq:
            self.leave()
            return
        self.photo = self.seq[self.index]
        self.cancel_crop()
        self.canvas.reset_zoom()
        self.full_token = None
        self.geo_cache = None
        ph = self.photo
        self.film.set_position(self.seq, self.index)
        self.canvas.video = ph.kind == KIND_VIDEO
        for w in (self.undo_btn, self.reset_btn):
            w.setEnabled(ph.kind != KIND_VIDEO)
        for i in range(self.TAB_EXIF):
            self.tabs.setTabEnabled(i, ph.kind != KIND_VIDEO)
        if ph.kind != KIND_VIDEO:
            self.tabs.setCurrentIndex(self.wanted_tab)
        self._sync_controls()
        self._show_exif()
        cached = self.previews.get(ph.id)
        if cached is not None:
            self.base, self.base_id = cached, ph.id
            self.render()
        else:
            self.base, self.base_id = None, None
            pm = self.win.cache.get(ph.id)     # sofort das kleine Bild, das scharfe kommt gleich
            self.canvas.set_image(pm.toImage() if pm else None)
        self._prefetch()

    # --- EXIF

    def _tab_clicked(self, i):
        if self.tabs.isTabEnabled(i):
            self.wanted_tab = i

    def _show_exif(self):
        """Liest erst, wenn der Reiter sichtbar ist, damit das Blättern schnell bleibt."""
        if self.photo is None or self.tabs.currentIndex() != self.TAB_EXIF:
            return
        data = self.exif_cache.get(self.photo.path)
        if data is not None:
            self.exif_view.setHtml(exif_html(data))
            return
        self.exif_view.setHtml(T("<p>Lese Metadaten …</p>"))
        self.exif_timer.start()

    def _read_exif(self):
        if self.photo is None or self.tabs.currentIndex() != self.TAB_EXIF:
            return
        path = self.photo.path
        threading.Thread(target=lambda: self.exifReady.emit(path, read_exif(path)), daemon=True).start()

    def _exif_ready(self, path, data):
        self.exif_cache[path] = data
        while len(self.exif_cache) > 64:
            self.exif_cache.popitem(last=False)
        if self.photo and self.photo.path == path:
            self._show_exif()

    def _prefetch(self):
        jobs = []
        for k in (0, 1, -1, 2, -2):
            i = self.index + k
            if 0 <= i < len(self.seq):
                ph = self.seq[i]
                if ph.id not in self.previews:
                    jobs.append((ph.id, ph.path, ph.kind))
        self.loader.request(jobs)

    def _preview_ready(self, pid, img):
        if img.isNull():
            return
        self.previews[pid] = qimage_to_array(img)
        while len(self.previews) > 9:
            self.previews.popitem(last=False)
        if self.photo and pid == self.photo.id and self.base_id != pid:
            self.base, self.base_id = self.previews[pid], pid
            self.geo_cache = None
            self.render()

    def goto(self, i):
        if 0 <= i < len(self.seq) and i != self.index:
            self.index = i
            self.show_current()

    def step(self, d):
        self.goto(self.index + d)

    def drop_current(self):
        """Das aktuelle Foto ist weg (verschoben oder gelöscht): zum nächsten springen."""
        if not self.seq:
            return
        del self.seq[self.index]
        self.index = min(self.index, len(self.seq) - 1)
        self.show_current()

    def leave(self):
        self.cancel_crop()
        self.canvas.reset_zoom()
        self.full_token = None
        self.back.emit(self.photo)

    # --- Darstellung

    def render(self):
        ph = self.photo
        if ph is None or self.base is None or self.base_id != ph.id:
            return
        e = ph.edits or {}
        cropping = self.canvas.crop is not None
        key = (ph.id, e.get("rot", 0), e.get("straighten", 0), None if cropping else tuple(e.get("crop") or ()))
        if self.geo_cache is None or self.geo_cache[0] != key:
            self.geo_cache = (key, geometry(self.base, e, not cropping))
        img = array_to_qimage(tone(self.geo_cache[1], e))
        if self.canvas.zoom is not None and self.full_token != (ph.id, ph.ver):
            # Bearbeitet, während hineingezoomt ist: Die volle Auflösung passt nicht mehr
            self.canvas.drop_full()
            self.full_token = None
            self.full_timer.start()
        self.canvas.set_image(img)
        self._update_info()
        self._update_zoom_label()

    def copy_path(self):
        if self.photo:
            QApplication.clipboard().setText(self.photo.path)
            self.copy_btn.setText(T("Kopiert ✓"))
            QTimer.singleShot(1500, lambda: self.copy_btn.setText(T("Pfad kopieren")))

    def _update_info(self):
        ph = self.photo
        self.path_label.set_path(ph.path)
        date = time.strftime(T("%d.%m.%Y") + " %H:%M", time.localtime(ph.date))
        size = ph.size / 1048576
        stars = "★" * ph.rating
        self.info.setText(f"{ph.name}   ·   {date}   ·   {size:.1f} MB   ·   " + T("{i} von {n}", i=self.index + 1, n=len(self.seq)) + f"   {stars}")

    def refresh_photo(self):
        """Von außen geändert (Stern, Drehung)."""
        self.geo_cache = None
        self._sync_controls()
        self.render()
        if self.base is None:
            self._update_info()

    def _sync_controls(self):
        e = (self.photo.edits if self.photo else None) or {}
        for key, (d, scale) in self.dials.items():
            d.set_quiet(e.get(key, 0) * scale)
        self.contrast_btn.setChecked("levels" in e)
        self.color_btn.setChecked("gains" in e)
        if self.photo:
            self._update_info()

    # --- Zoom

    def _preview_factor(self):
        """Wie viel größer das Original gegenüber der Vorschau ist."""
        ph = self.photo
        if self.base is None:
            return 1.0
        size = self.full_sizes.get(ph.id)
        if size is None:
            s = QImageReader(ph.path).size()
            size = self.full_sizes[ph.id] = max(s.width(), s.height())
        return max(1.0, size / max(self.base.shape[:2])) if size > 0 else 1.0

    def _can_zoom(self):
        return (self.photo is not None and self.photo.kind != KIND_VIDEO and self.base is not None
                and self.canvas.crop is None)

    def zoom_by(self, factor, pos=None):
        if not self._can_zoom():
            return
        c = self.canvas
        current = c.zoom if c.zoom is not None else c.fit_scale()
        limit = self.MAX_ZOOM * (1 if c.full is not None else self._preview_factor())
        self._apply_zoom(min(limit, current * factor), pos)

    def zoom_fit(self):
        self.canvas.reset_zoom()
        self.full_token = None
        self._update_zoom_label()

    def toggle_zoom(self, pos):
        """Einpassen und 100 % im Wechsel."""
        if not self._can_zoom():
            return
        if self.canvas.zoom is not None:
            self.zoom_fit()
            return
        self._apply_zoom(self._preview_factor(), pos)

    def _apply_zoom(self, zoom, pos):
        c = self.canvas
        c.set_zoom(zoom, pos if pos is not None else QPointF(c.rect().center()))
        if c.zoom is None:
            self.full_token = None
        elif c.full is None and c.zoom > 1.0:
            self._request_full()    # Über die Vorschau hinaus: Original im Hintergrund nachladen
        self._update_zoom_label()

    def _request_full(self):
        ph = self.photo
        if ph is None or self.canvas.zoom is None or self.canvas.full is not None:
            return
        token = (ph.id, ph.ver)
        if token != self.full_token:
            self.full_token = token
            threading.Thread(target=self._load_full, args=(token, ph.path, ph.kind, ph.edits), daemon=True).start()

    def _load_full(self, token, path, kind, edits):
        try:
            img = load_qimage(path, kind)
            if edits and not img.isNull():
                img = array_to_qimage(render_edits(qimage_to_array(img), edits))
        except Exception:
            img = QImage()
        self.fullReady.emit(token, img)

    def _full_ready(self, token, img):
        ph = self.photo
        if img.isNull() or ph is None or token != (ph.id, ph.ver) or token != self.full_token or self.canvas.zoom is None:
            return
        self.canvas.swap_full(img)
        self._update_zoom_label()

    def _update_zoom_label(self):
        c = self.canvas
        if self.photo is None or self.base is None or c.image is None:
            self.zoom_label.setText("")
            return
        zoom = c.zoom if c.zoom is not None else c.fit_scale()
        pct = zoom if c.full is not None else zoom / self._preview_factor()
        self.zoom_label.setText(f"{pct * 100:.0f} %")

    def file_changed(self, photo):
        """Die Datei wurde außerhalb geändert, z. B. in PhotoCraft gespeichert."""
        self.previews.pop(photo.id, None)
        self.full_sizes.pop(photo.id, None)
        if self.photo is photo:
            self.show_current()

    # --- Bearbeitung

    def _push_undo(self):
        if self.photo:
            self.undo_stack.setdefault(self.photo.id, []).append(dict(self.photo.edits or {}))

    def undo(self):
        stack = self.undo_stack.get(self.photo.id) if self.photo else None
        if stack:
            self.win.store_edits(self.photo, stack.pop())
            self.refresh_photo()

    def reset_edits(self):
        if self.photo and self.photo.edits:
            self._push_undo()
            self.win.store_edits(self.photo, {})
            self.refresh_photo()

    def _set_value(self, key, value):
        if not self.photo:
            return
        e = dict(self.photo.edits or {})
        if value:
            e[key] = value
        else:
            e.pop(key, None)
        self.win.store_edits(self.photo, e)
        self.render_timer.start()

    def _analysis_source(self):
        """Bild vor den Tonkorrekturen, darauf rechnen die Automatiken."""
        return geometry(self.base, self.photo.edits or {}) if self.base is not None else None

    def toggle_contrast(self):
        self._toggle_auto("levels", auto_levels)

    def toggle_color(self):
        self._toggle_auto("gains", auto_gains)

    def _toggle_auto(self, key, fn):
        a = self._analysis_source()
        if a is None:
            return
        self._push_undo()
        e = dict(self.photo.edits or {})
        if key in e:
            del e[key]
        else:
            e[key] = fn(a)
        self.win.store_edits(self.photo, e)
        self.refresh_photo()

    def auto_all(self):
        a = self._analysis_source()
        if a is None:
            return
        self._push_undo()
        e = dict(self.photo.edits or {})
        e["levels"], e["gains"] = auto_levels(a), auto_gains(a)
        self.win.store_edits(self.photo, e)
        self.refresh_photo()

    def start_crop(self):
        ph = self.photo
        if ph is None or ph.kind == KIND_VIDEO or self.base is None or self.canvas.crop is not None:
            return
        self.canvas.reset_zoom()
        self.full_token = None
        self.wanted_tab = 0
        self.tabs.setCurrentIndex(0)
        self.crop_box.show()
        self.crop_btn.hide()
        self.canvas.crop = list((ph.edits or {}).get("crop") or (0.0, 0.0, 1.0, 1.0))
        self.ratio.setCurrentIndex(0)
        self.geo_cache = None
        self.render()

    def _ratio_changed(self):
        val = self.ratio.currentData()
        if val == -1.0 and self.canvas.image is not None:
            val = self.canvas.image.width() / max(1, self.canvas.image.height())
        self.canvas.crop_ratio = val
        if val and self.canvas.crop is not None and self.canvas.image is not None:
            # Größten mittigen Ausschnitt im gewählten Format setzen
            iw, ih = self.canvas.image.width(), self.canvas.image.height()
            w, h = 1.0, iw / val / ih
            if h > 1:
                w, h = val * ih / iw, 1.0
            self.canvas.crop = [(1 - w) / 2, (1 - h) / 2, (1 + w) / 2, (1 + h) / 2]
            self.canvas.update()

    def apply_crop(self):
        c = self.canvas.crop
        if c is None:
            return
        self.canvas.crop = None
        self._close_crop_box()
        if c[2] - c[0] > 0.01 and c[3] - c[1] > 0.01:
            self._push_undo()
            e = dict(self.photo.edits or {})
            if c[0] <= 0.001 and c[1] <= 0.001 and c[2] >= 0.999 and c[3] >= 0.999:
                e.pop("crop", None)
            else:
                e["crop"] = [round(v, 5) for v in c]
            self.win.store_edits(self.photo, e)
        self.refresh_photo()

    def remove_crop(self):
        if self.canvas.crop is None:
            return
        self.canvas.crop = None
        self._close_crop_box()
        if (self.photo.edits or {}).get("crop"):
            self._push_undo()
            e = dict(self.photo.edits)
            del e["crop"]
            self.win.store_edits(self.photo, e)
        self.refresh_photo()

    def cancel_crop(self):
        if self.canvas.crop is None:
            return
        self.canvas.crop = None
        self._close_crop_box()
        self.geo_cache = None
        self.render()

    def _close_crop_box(self):
        self.crop_box.hide()
        self.crop_btn.show()
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

    def keyPressEvent(self, e):
        key = e.key()
        if key == Qt.Key.Key_Escape:
            if self.canvas.crop is not None:
                self.cancel_crop()
            elif self.canvas.zoom is not None:
                self.zoom_fit()
            else:
                self.leave()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.canvas.crop is not None:
                self.apply_crop()
            elif self.photo and self.photo.kind == KIND_VIDEO:
                QDesktopServices.openUrl(QUrl.fromLocalFile(self.photo.path))
        elif self.canvas.crop is not None:
            return
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_Space, Qt.Key.Key_PageDown):
            self.step(1)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Backspace, Qt.Key.Key_PageUp):
            self.step(-1)
        elif key == Qt.Key.Key_Home:
            self.goto(0)
        elif key == Qt.Key.Key_End:
            self.goto(len(self.seq) - 1)
        elif key == Qt.Key.Key_C:
            self.start_crop()
        elif key == Qt.Key.Key_A:
            self.auto_all()
        elif key == Qt.Key.Key_Z:
            self.toggle_zoom(None)
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(1.25)
        elif key == Qt.Key.Key_Minus:
            self.zoom_by(1 / 1.25)
        elif key == Qt.Key.Key_F:
            self.zoom_fit()
        else:
            super().keyPressEvent(e)


# ---------------------------------------------------------------------------
# Dialoge
# ---------------------------------------------------------------------------

class MoveDialog(QDialog):
    """Ordner per Tippen finden: Tasten M, ein paar Buchstaben, Enter."""

    def __init__(self, parent, folders, count, roots):
        super().__init__(parent)
        self.setWindowTitle(T("Verschieben"))
        self.resize(520, 420)
        self.roots = roots
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(T("1 Foto verschieben nach:") if count == 1 else T("{n} Fotos verschieben nach:", n=num(count))))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(T("Ordner suchen …"))
        lay.addWidget(self.edit)
        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        for path in folders:
            it = QListWidgetItem(self._display(path))
            it.setData(Qt.ItemDataRole.UserRole, path)
            self.list.addItem(it)
        self.edit.textChanged.connect(self._filter)
        self.edit.installEventFilter(self)
        self.list.itemActivated.connect(lambda _: self.accept())
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.list.setCurrentRow(0)

    def _display(self, path):
        for r in self.roots:
            if path == r or path.startswith(r + os.sep):
                return os.path.join(os.path.basename(r), os.path.relpath(path, r)).removesuffix(os.sep + ".")
        return path

    def _filter(self, text):
        words = text.casefold().split()
        first = None
        for i in range(self.list.count()):
            it = self.list.item(i)
            show = all(w in it.text().casefold() for w in words)
            it.setHidden(not show)
            if show and first is None:
                first = it
        if first:
            self.list.setCurrentItem(first)

    def eventFilter(self, obj, ev):
        if ev.type() == ev.Type.KeyPress and ev.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 1 if ev.key() == Qt.Key.Key_Down else -1
            row = self.list.currentRow() + step
            while 0 <= row < self.list.count():
                if not self.list.item(row).isHidden():
                    self.list.setCurrentRow(row)
                    break
                row += step
            return True
        return False

    def target(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it and not it.isHidden() else None


class ExportDialog(QDialog):
    def __init__(self, parent, count, folder):
        super().__init__(parent)
        self.setWindowTitle(T("Exportieren"))
        lay = QFormLayout(self)
        lay.addRow(QLabel(T("1 Foto wird mit den Korrekturen als neue Datei gespeichert.\nDie Originale bleiben unverändert.") if count == 1
                          else T("{n} Fotos werden mit den Korrekturen als neue Dateien gespeichert.\nDie Originale bleiben unverändert.",
                                 n=num(count))))
        row = QHBoxLayout()
        self.folder = QLineEdit(folder)
        row.addWidget(self.folder, 1)
        pick = QPushButton(T("Wählen …"))
        pick.clicked.connect(self._pick)
        row.addWidget(pick)
        lay.addRow(T("Zielordner:"), row)
        self.size = QComboBox()
        for text, val in ((T("Originalgröße"), 0), (T("{n} Pixel", n=3000), 3000), (T("{n} Pixel", n=2048), 2048), (T("{n} Pixel", n=1600), 1600),
                          (T("{n} Pixel", n=1024), 1024)):
            self.size.addItem(text, val)
        lay.addRow(T("Längste Seite:"), self.size)
        self.quality = QComboBox()
        for text, val in ((T("Hoch (92)"), 92), (T("Sehr hoch (97)"), 97), (T("Mittel (82)"), 82)):
            self.quality.addItem(text, val)
        lay.addRow(T("JPEG-Qualität:"), self.quality)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addRow(bb)

    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, T("Zielordner"), self.folder.text())
        if d:
            self.folder.setText(d)


def unique_path(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem} ({n}){ext}"):
        n += 1
    return f"{stem} ({n}){ext}"


def export_photo(p, dest, max_side, quality):
    """Schreibt eine neue Datei. Ohne Korrekturen und Verkleinerung einfach eine Kopie."""
    stem, ext = os.path.splitext(p.name)
    if p.kind == KIND_VIDEO or (not p.edits and not max_side and p.kind == KIND_PHOTO):
        out = unique_path(os.path.join(dest, p.name))
        shutil.copy2(p.path, out)
        return out
    im, exif = load_pil_full(p.path, p.kind)
    a = render_edits(np.asarray(im), p.edits or {})
    im = Image.fromarray(np.ascontiguousarray(a))
    if max_side and max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = unique_path(os.path.join(dest, stem + ".jpg"))
    kwargs = {"quality": quality, "subsampling": 0 if quality >= 90 else -1}
    if exif:
        kwargs["exif"] = exif
    im.save(out, "JPEG", **kwargs)
    return out


class Exporter(QThread):
    progress = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, parent, photos, dest, max_side, quality):
        super().__init__(parent)
        self.photos, self.dest, self.max_side, self.quality = photos, dest, max_side, quality
        self.stop = False

    def run(self):
        for i, p in enumerate(self.photos):
            if self.stop:
                return
            try:
                export_photo(p, self.dest, self.max_side, self.quality)
            except Exception as ex:
                self.failed.emit(f"{p.name}: {ex}")
            self.progress.emit(i + 1)


def _desktop_entry(path):
    """Liest den Abschnitt [Desktop Entry] einer .desktop-Datei."""
    entry, active = {}, False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    active = line == "[Desktop Entry]"
                elif active and "=" in line:
                    key, value = line.split("=", 1)
                    entry[key.strip()] = value.strip()
    except OSError:
        return None
    return entry


def installed_apps():
    """Alle grafischen Programme, die Dateien entgegennehmen, auch Flatpaks."""
    home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    dirs = [home] + os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    dirs += [os.path.expanduser("~/.local/share/flatpak/exports/share"), "/var/lib/flatpak/exports/share"]
    if FLATPAK:     # Im Flatpak liegen die Programme des Systems unter /run/host
        dirs = [os.path.expanduser("~/.local/share")] + ["/run/host" + d for d in ("/usr/local/share", "/usr/share")] + dirs[1:]
    apps = {}
    for d in dirs:
        folder = os.path.join(d, "applications")
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if not name.endswith(".desktop") or name in apps or name in ("mattpic.desktop", "com.mathiasree.MattPic.desktop"):
                continue
            e = _desktop_entry(os.path.join(folder, name))
            if not e or e.get("Type") != "Application" or "Exec" not in e:
                continue
            if "true" in (e.get("NoDisplay"), e.get("Hidden"), e.get("Terminal")):
                continue
            if not any(code in e["Exec"] for code in ("%f", "%F", "%u", "%U")):
                continue
            apps[name] = {"id": name[:-8], "name": e.get(f"Name[{i18n.language()}]") or e.get("Name", name[:-8]), "exec": e["Exec"],
                          "icon": e.get("Icon", ""), "mime": set(filter(None, e.get("MimeType", "").split(";"))),
                          "kde": "kde" in name}
    return sorted(apps.values(), key=lambda a: a["name"].casefold())


def build_commands(app, paths):
    """Setzt die Dateien in die Exec-Zeile ein. %f und %u nehmen nur eine Datei, also je Datei ein Aufruf."""
    tokens = shlex.split(app["exec"])
    single = any(t in ("%f", "%u") for t in tokens)
    commands = []
    for group in ([[p] for p in paths] if single else [paths]):
        cmd = []
        for t in tokens:
            if t in ("%f", "%F"):
                cmd += group
            elif t in ("%u", "%U"):
                cmd += [QUrl.fromLocalFile(p).toString() for p in group]
            elif t in ("%i", "%c", "%k"):
                continue
            else:
                cmd.append(t)
        commands.append(cmd)
    return commands




# ---------------------------------------------------------------------------
# Hauptfenster
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        os.makedirs(DATA_DIR, exist_ok=True)
        self.settings = settings_store()
        self.con = open_library()
        self.thumbs_con = open_thumbs()
        self.photos = {}
        self.roots = []
        self.folders = []
        self.undo_stack = []
        self.offline = set()
        self.scanner = None
        self.rescan_pending = False
        self.apps = None
        self.watch_external = False
        self.engine = ThumbEngine()
        self.cache = ThumbCache(self.engine)
        self.setWindowTitle(APP)
        self.setWindowIcon(QIcon(os.path.join(HERE, "mattpic.svg")))
        self._build_ui()
        self._build_menu()
        self.reload()
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            # Erster Start: 1280×720, auf kleinen Bildschirmen (z. B. 1024×768) passend verkleinert
            avail = QApplication.primaryScreen().availableGeometry()
            w, h = min(1280, int(avail.width() * .94)), min(720, int(avail.height() * .9))
            self.setGeometry(avail.x() + (avail.width() - w) // 2, avail.y() + (avail.height() - h) // 2, w, h)
        QTimer.singleShot(50, self._after_show)

    def _after_show(self):
        if not self.roots:
            self.status(T("Noch keine Ordner: Über „Ordner hinzufügen“ geht es los."))
        self.start_scan()

    # --- Oberfläche

    def _build_ui(self):
        self.grid = Grid(self.cache)
        self.tree = FolderTree()
        self.tray = Tray(self.cache, self.grid)
        self.edit = EditView(self)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        lib = QWidget()
        ll = QVBoxLayout(lib)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)
        self.stack.addWidget(lib)
        self.stack.addWidget(self.edit)

        bar = QWidget()
        bar.setObjectName("toolbar")
        tl = QHBoxLayout(bar)
        tl.setContentsMargins(8, 4, 8, 4)
        tl.setSpacing(6)
        add = QPushButton(T("＋  Ordner hinzufügen"))
        add.clicked.connect(self.add_root)
        add.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tl.addWidget(add)
        tl.addSpacing(12)
        tl.addWidget(QLabel(T("Gruppieren:")))
        self.group = QComboBox()
        self.group.addItem(T("Nach Ordner"), "folder")
        self.group.addItem(T("Nach Monat"), "month")
        self.group.addItem(T("Nach Jahr"), "year")
        tl.addWidget(self.group)
        tl.addWidget(QLabel(T("Sortieren:")))
        self.sort = QComboBox()
        for text, val in ((T("Datum, neueste zuerst"), "date_desc"), (T("Datum, älteste zuerst"), "date_asc"),
                          (T("Name"), "name"), (T("Größe"), "size"), (T("Sterne"), "rating")):
            self.sort.addItem(text, val)
        tl.addWidget(self.sort)
        tl.addStretch(1)
        tl.addWidget(QLabel(T("Mindestens:")))
        self.min_stars = QComboBox()
        self.min_stars.addItem(T("alle"), 0)
        for i in range(1, 6):
            self.min_stars.addItem("★" * i, i)
        tl.addWidget(self.min_stars)
        self.search = QLineEdit()
        self.search.setPlaceholderText(T("Suchen …"))
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(190)
        tl.addWidget(self.search)
        for w in (self.group, self.sort, self.min_stars):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ll.addWidget(bar)

        split = QSplitter()
        split.setChildrenCollapsible(False)
        split.setHandleWidth(1)
        split.addWidget(self.tree)
        split.addWidget(self.grid)
        split.setStretchFactor(1, 1)
        split.setSizes([230, 1000])
        ll.addWidget(split, 1)

        bottom = QWidget()
        bottom.setObjectName("bottombar")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(8, 5, 8, 5)
        bl.setSpacing(5)
        self.tray.setFixedWidth(330)
        bl.addWidget(self.tray)
        for text, tip, fn in (("⟲", T("Links drehen (Strg+Umschalt+R)"), lambda: self.rotate(-1)),
                              ("⟳", T("Rechts drehen (Strg+R)"), lambda: self.rotate(1))):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            bl.addWidget(b)
        star = QPushButton("★")
        star.setToolTip(T("Stern setzen oder entfernen (Tasten 0 bis 5)"))
        star.clicked.connect(self._toggle_star)
        bl.addWidget(star)
        move = QPushButton(T("Verschieben (M)"))
        move.clicked.connect(self.move_dialog)
        bl.addWidget(move)
        export = QPushButton(T("Exportieren (E)"))
        export.clicked.connect(self.export_selection)
        bl.addWidget(export)
        trash = QPushButton(T("Papierkorb"))
        trash.clicked.connect(self.trash_selection)
        bl.addWidget(trash)
        bl.addStretch(1)
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(72, 256)
        self.size_slider.setFixedWidth(140)
        self.size_slider.setToolTip(T("Größe der Vorschaubilder"))
        bl.addWidget(self.size_slider)
        for w in bottom.findChildren(QWidget):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ll.addWidget(bottom)

        s = self.settings
        self.grid.size_px = int(s.value("thumb", 140))
        self.size_slider.setValue(self.grid.size_px)
        self.group.setCurrentIndex(max(0, self.group.findData(s.value("group", "folder"))))
        self.sort.setCurrentIndex(max(0, self.sort.findData(s.value("sort", "date_desc"))))

        self.status_label = QLabel()
        self.statusBar().addWidget(self.status_label, 1)
        self.count_label = QLabel()
        self.statusBar().addPermanentWidget(self.count_label)
        self.search_timer = QTimer(self, singleShot=True, interval=90)
        self.search_timer.timeout.connect(self.apply_view)
        self.search.textChanged.connect(lambda _: self.search_timer.start())
        self.search.returnPressed.connect(self.grid.setFocus)
        self.search.installEventFilter(self)
        self.group.currentIndexChanged.connect(self.apply_view)
        self.sort.currentIndexChanged.connect(self.apply_view)
        self.min_stars.currentIndexChanged.connect(self.apply_view)
        self.size_slider.valueChanged.connect(self.grid.set_thumb_size)
        self.grid.sizeWheel.connect(lambda d: self.size_slider.setValue(self.size_slider.value() + d))
        self.grid.activated.connect(self.open_photo)
        self.grid.menuRequested.connect(self._grid_menu)
        self.grid.sectionVisible.connect(self._section_visible)
        self.tree.itemClicked.connect(self._tree_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.tree.dropped.connect(self._dropped)
        self.edit.back.connect(self._back_to_library)
        self.thumb_status = QTimer(self, interval=1000)
        self.thumb_status.timeout.connect(self._update_counts)
        self.thumb_status.start()

    def _build_menu(self):
        def action(menu, text, fn, key=None):
            a = QAction(text, self)
            a.triggered.connect(lambda _=False: fn())
            if key:
                a.setShortcut(QKeySequence(key))
                a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            menu.addAction(a)
            return a

        m = self.menuBar().addMenu(T("&Datei"))
        action(m, T("Ordner hinzufügen …"), self.add_root, "Ctrl+O")
        action(m, T("Ordner neu einlesen"), self.start_scan, "F5")
        m.addSeparator()
        action(m, T("Exportieren …"), self.export_selection, "E")
        m.addSeparator()
        action(m, T("Beenden"), self.close, "Ctrl+Q")
        m = self.menuBar().addMenu(T("&Bearbeiten"))
        action(m, T("Rückgängig"), self.undo, "Ctrl+Z")
        m.addSeparator()
        action(m, T("Alles auswählen"), self.grid.select_all, "Ctrl+A")
        action(m, T("Auswahl aufheben"), self.grid.clear_selection, "Ctrl+D")
        action(m, T("Suchen"), self._focus_search, "Ctrl+F")
        m = self.menuBar().addMenu(T("&Foto"))
        for i in range(6):
            action(m, T("Keine Sterne") if i == 0 else "★" * i, lambda v=i: self.set_rating(v), str(i))
        m.addSeparator()
        action(m, T("Rechts drehen"), lambda: self.rotate(1), "Ctrl+R")
        action(m, T("Links drehen"), lambda: self.rotate(-1), "Ctrl+Shift+R")
        m.addSeparator()
        action(m, T("In Ordner verschieben …"), self.move_dialog, "M")
        action(m, T("In den Papierkorb"), self.trash_selection, "Delete")
        action(m, T("Im Dateimanager zeigen"), self.reveal)
        open_with = m.addMenu(T("Öffnen mit"))
        open_with.aboutToShow.connect(lambda: self.fill_open_with(open_with))
        m = self.menuBar().addMenu(T("&Hilfe"))
        action(m, T("Tastenkürzel"), self.show_help, "F1")
        lm = m.addMenu(T("Sprache der Oberfläche"))
        group = QActionGroup(lm)
        current = self.settings.value("ui_lang", "")
        system = i18n.LANGUAGES[i18n.pick_language(QLocale.system().uiLanguages())]
        for code, name in [("", T("Systemsprache ({lang})", lang=system))] + list(i18n.LANGUAGES.items()):
            a = lm.addAction(name)
            a.setCheckable(True)
            a.setChecked(code == current)
            group.addAction(a)
            a.triggered.connect(lambda _=False, code=code: self.set_ui_language(code))
            if not code:
                lm.addSeparator()
        m.addSeparator()
        action(m, T("Über Matt|Pic"), self.show_about)

    def set_ui_language(self, code):
        self.settings.setValue("ui_lang", code)
        new = code or i18n.pick_language(QLocale.system().uiLanguages())
        if new != i18n.language():
            i18n.set_language(new)      # nur für diese Meldung, die Menüs folgen nach dem Neustart
            QMessageBox.information(self, T("Sprache der Oberfläche"),
                                    T("Die neue Sprache gilt nach einem Neustart von Matt|Pic."))

    def show_about(self):
        QMessageBox.about(self, T("Über Matt|Pic"),
                          f"<h3>Matt|Pic {APP_VERSION}</h3><p>" + T("Fotos schnell sortieren und bearbeiten.") +
                          "</p><p>© 2026 Mathias Ree · GPL-3.0-or-later<br>"
                          "<a href='https://github.com/mathiasree/mattpic'>github.com/mathiasree/mattpic</a></p>")

    def eventFilter(self, obj, ev):
        if obj is self.search and ev.type() == ev.Type.KeyPress and ev.key() == Qt.Key.Key_Escape:
            self.search.clear()
            self.grid.setFocus()
            return True
        return super().eventFilter(obj, ev)

    def _focus_search(self):
        if self.stack.currentWidget() is not self.edit:
            self.search.setFocus()
            self.search.selectAll()

    def status(self, text):
        self.status_label.setText(text)

    def _update_counts(self):
        n = len(self.grid.flat)
        text = photos_text(n)
        if self.engine.remaining():
            text = T("Vorschaubilder: noch {n}", n=num(self.engine.remaining())) + "   ·   " + text
        self.count_label.setText(text)

    # --- Daten

    def reload(self):
        """Liest die Datenbank neu ein. Bestehende Foto-Objekte bleiben erhalten."""
        rows = self.con.execute("SELECT id,path,folder,name,size,mtime,taken,kind,rating,edits,missing FROM photos").fetchall()
        fresh = {}
        for r in rows:
            p = self.photos.get(r[0])
            changed_outside = p is not None and int(p.mtime) != int(r[5])
            if p is None:
                p = Photo()
            p.id, p.path, p.folder, p.name, p.size, p.mtime, p.taken, p.kind, p.rating = r[:9]
            p.edits = json.loads(r[9]) if r[9] else None
            p.missing = r[10]
            fresh[r[0]] = p
            if changed_outside:
                self.cache.invalidate(p)
                self.edit.file_changed(p)
        self.photos = fresh
        self.roots = [r[0] for r in self.con.execute("SELECT path FROM roots")]
        self.folders = [r[0] for r in self.con.execute("SELECT path FROM folders")]
        self.apply_view()
        self.refresh_tree()
        self._queue_background()

    def refresh_tree(self):
        counts = {}
        for p in self.photos.values():
            if not p.missing:
                counts[p.folder] = counts.get(p.folder, 0) + 1
        self.tree.rebuild(self.roots, self.folders, counts, self.offline)

    def _queue_background(self):
        known = dict(self.thumbs_con.execute("SELECT id,ver FROM thumbs"))
        todo = [p for p in self.photos.values() if not p.missing and known.get(p.id) != p.ver
                and not any(p.path.startswith(r + os.sep) for r in self.offline)]
        todo.sort(key=lambda p: -p.date)
        self.engine.set_background(todo)

    def apply_view(self):
        minimum = self.min_stars.currentData() or 0
        words = self.search.text().casefold().split()
        photos = [p for p in self.photos.values() if not p.missing and p.rating >= minimum]
        if words:
            photos = [p for p in photos if all(w in p.path.casefold() for w in words)]
        order = self.sort.currentData()
        keys = {"date_desc": (lambda p: -p.date), "date_asc": (lambda p: p.date),
                "name": (lambda p: p.name.casefold()), "size": (lambda p: -p.size),
                "rating": (lambda p: (-p.rating, -p.date))}
        photos.sort(key=keys[order])
        mode = self.group.currentData()
        groups = {}
        if mode == "folder":
            for p in photos:
                groups.setdefault(p.folder, []).append(p)
            items = []
            for folder, ps in groups.items():
                newest = max(p.date for p in ps)
                oldest = min(p.date for p in ps)
                when = time.strftime(T("%d.%m.%Y"), time.localtime(newest))
                if time.strftime("%Y%m%d", time.localtime(oldest)) != time.strftime("%Y%m%d", time.localtime(newest)):
                    when = T("{a} bis {b}", a=time.strftime(T("%d.%m.%Y"), time.localtime(oldest)), b=when)
                sub = f"{when}   ·   {photos_text(len(ps))}"
                items.append((newest, Section(folder, os.path.basename(folder), sub, ps)))
            if order == "date_asc":
                items.sort(key=lambda t: t[0])
            elif order == "name":
                items.sort(key=lambda t: t[1].title.casefold())
            else:
                items.sort(key=lambda t: -t[0])
            sections = [s for _, s in items]
        else:
            fmt = "%Y-%m" if mode == "month" else "%Y"
            for p in photos:
                groups.setdefault(time.strftime(fmt, time.localtime(p.date)), []).append(p)
            sections = []
            for key in sorted(groups, reverse=order != "date_asc"):
                ps = groups[key]
                title = f"{T(MONTHS[int(key[5:]) - 1])} {key[:4]}" if mode == "month" else key
                sections.append(Section(key, title, photos_text(len(ps)), ps))
        self.grid.set_sections(sections)
        self._update_counts()

    def store_edits(self, p, edits):
        p.edits = edits or None
        self.con.execute("UPDATE photos SET edits=? WHERE id=?", (edits_json(p.edits) or None, p.id))
        self.con.commit()
        self.cache.invalidate(p)
        self.grid.viewport().update()
        self.edit.film.update()

    # --- Scan

    def start_scan(self):
        if self.scanner and self.scanner.isRunning():
            self.rescan_pending = True
            return
        self.scanner = Scanner(self)
        self.scanner.offline = set(self.offline)
        self.scanner.changed.connect(self._scan_changed)
        self.scanner.status.connect(self.status)
        self.scanner.finished.connect(self._scan_finished)
        self.scanner.start(QThread.Priority.LowPriority)

    def _scan_changed(self):
        self.offline = set(self.scanner.offline) if self.scanner else self.offline
        self.reload()

    def _scan_finished(self):
        self.offline = set(self.scanner.offline)
        self.refresh_tree()
        if self.offline:
            self.status(T("Nicht erreichbar: ") + ", ".join(os.path.basename(r) for r in self.offline))
        if self.rescan_pending:
            self.rescan_pending = False
            self.start_scan()

    def add_root(self):
        d = QFileDialog.getExistingDirectory(self, T("Foto-Ordner hinzufügen"), os.path.expanduser("~"))
        if d:
            self.add_root_path(os.path.normpath(d))

    def add_root_path(self, d):
        d = os.path.abspath(d)
        for r in self.roots:
            if d == r or d.startswith(r + os.sep):
                self.status(T("Der Ordner gehört schon zur Bibliothek: {path}", path=r))
                return
        with self.con:
            for r in self.roots:
                if r.startswith(d + os.sep):
                    self.con.execute("DELETE FROM roots WHERE path=?", (r,))
            self.con.execute("INSERT OR IGNORE INTO roots VALUES(?)", (d,))
        self.reload()
        self.start_scan()

    def remove_root(self, root):
        answer = QMessageBox.question(self, T("Ordner entfernen"),
                                      T("„{name}“ aus Matt|Pic entfernen?\n\nDie Dateien bleiben unberührt. Sterne und Korrekturen dieses Ordners gehen verloren.",
                                        name=os.path.basename(root)))
        if answer != QMessageBox.StandardButton.Yes:
            return
        pre = root + os.sep
        with self.con:
            self.con.execute("DELETE FROM roots WHERE path=?", (root,))
            self.con.execute("DELETE FROM folders WHERE path=? OR substr(path,1,?)=?", (root, len(pre), pre))
            self.con.execute("DELETE FROM photos WHERE substr(path,1,?)=?", (len(pre), pre))
        self.offline.discard(root)
        self.reload()

    # --- Baum

    def _tree_clicked(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if self.group.currentData() != "folder":
            self.group.setCurrentIndex(0)
        self.tree_jump = True
        if not self.grid.scroll_to_section(path):
            # Ordner ohne eigene Fotos: zum ersten Unterordner mit Fotos springen
            pre = path + os.sep
            for s in self.grid.sections:
                if s.key.startswith(pre):
                    self.grid.scroll_to_section(s.key)
                    break
        self.tree_jump = False

    def _section_visible(self, key):
        if self.group.currentData() != "folder" or getattr(self, "tree_jump", False):
            return
        item = self.tree.items.get(key)
        if item is not None and not self.tree.underMouse():
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)
            self.tree.blockSignals(False)

    def _tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        m = QMenu(self)
        m.addAction(T("Neuer Unterordner …"), lambda: self.new_folder(path))
        m.addAction(T("Im Dateimanager öffnen"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
        if path in self.roots:
            m.addSeparator()
            m.addAction(T("Aus Matt|Pic entfernen …"), lambda: self.remove_root(path))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def new_folder(self, parent):
        name, ok = QInputDialog.getText(self, T("Neuer Ordner"), T("Name:"))
        name = name.strip()
        if not ok or not name:
            return
        path = os.path.join(parent, name)
        if os.sep in name or name in (".", ".."):
            self.status(T("Ungültiger Ordnername"))
            return
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as ex:
            QMessageBox.warning(self, APP, T("Ordner konnte nicht angelegt werden:") + f"\n{ex}")
            return
        with self.con:
            self.con.execute("INSERT OR IGNORE INTO folders VALUES(?)", (path,))
        self.folders.append(path)
        self.refresh_tree()
        if parent in self.tree.items:
            self.tree.items[parent].setExpanded(True)

    # --- Aktionen auf Fotos

    def in_editor(self):
        return self.stack.currentWidget() is self.edit

    def targets(self):
        if self.in_editor():
            return [self.edit.photo] if self.edit.photo else []
        return self.grid.selected_photos()

    def _toggle_star(self):
        photos = self.targets()
        if photos:
            self.set_rating(0 if all(p.rating for p in photos) else 1)

    def set_rating(self, value):
        photos = self.targets()
        if not photos:
            return
        old = [(p, p.rating) for p in photos]
        self._write_ratings([(p, value) for p in photos])

        def undo():
            self._write_ratings(old)
        self.undo_stack.append(undo)
        if self.in_editor():
            self.edit.refresh_photo()
        elif self.min_stars.currentData() or self.sort.currentData() == "rating":
            self.apply_view()
        self.grid.viewport().update()

    def _write_ratings(self, pairs):
        with self.con:
            self.con.executemany("UPDATE photos SET rating=? WHERE id=?", [(v, p.id) for p, v in pairs])
        for p, v in pairs:
            p.rating = v
        self.grid.viewport().update()

    def rotate(self, turns):
        photos = [p for p in self.targets() if p.kind != KIND_VIDEO]
        if not photos:
            return
        old = [(p, p.edits) for p in photos]
        for p in photos:
            self.store_edits(p, rotated_edits(p.edits, turns))

        def undo():
            for p, e in old:
                self.store_edits(p, e)
            if self.in_editor():
                self.edit.refresh_photo()
        self.undo_stack.append(undo)
        if self.in_editor():
            self.edit.refresh_photo()

    def undo(self):
        if self.in_editor() and self.edit.undo_stack.get(self.edit.photo.id if self.edit.photo else None):
            self.edit.undo()
        elif self.undo_stack:
            self.undo_stack.pop()()
        else:
            self.status(T("Nichts mehr rückgängig zu machen"))

    def move_dialog(self):
        photos = self.targets()
        if not photos:
            return
        folders = sorted(self.folders, key=str.casefold)
        dlg = MoveDialog(self, folders, len(photos), self.roots)
        if dlg.exec() and dlg.target():
            self.transfer(photos, dlg.target(), False)

    def _dropped(self, ids, folder, copy):
        photos = [self.photos[i] for i in ids if i in self.photos]
        self.transfer(photos, folder, copy)

    def transfer(self, photos, folder, copy):
        """Verschiebt oder kopiert Dateien. Sterne und Korrekturen ziehen beim Verschieben mit um."""
        photos = [p for p in photos if copy or p.folder != folder]
        if not photos:
            return
        progress = None
        if len(photos) > 15:
            progress = QProgressDialog(T("Kopiere …") if copy else T("Verschiebe …"), T("Abbrechen"), 0, len(photos), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
        done, errors = [], []
        for i, p in enumerate(photos):
            if progress:
                progress.setValue(i)
                if progress.wasCanceled():
                    break
            dst = unique_path(os.path.join(folder, p.name))
            try:
                if copy:
                    shutil.copy2(p.path, dst)
                else:
                    self.con.execute("DELETE FROM photos WHERE path=? AND missing=1", (dst,))
                    shutil.move(p.path, dst)
                    done.append((p, p.path, p.folder, p.name))
                    self._relocate(p, dst)
            except OSError as ex:
                errors.append(f"{p.name}: {ex}")
        self.con.commit()
        if progress:
            progress.close()
        if errors:
            QMessageBox.warning(self, APP, T("Nicht alles hat geklappt:") + "\n\n" + "\n".join(errors[:12]))
        if copy:
            self.status(T("{n} kopiert", n=len(photos) - len(errors)))
            self.start_scan()
            return
        if done:
            self.undo_stack.append(lambda: self._undo_move(done))
            self.status(T("{n} nach „{folder}“ verschoben. Strg+Z macht es rückgängig.", n=len(done), folder=os.path.basename(folder)))
            self._after_removal({p.id for p, *_ in done})

    def _relocate(self, p, dst):
        p.path, p.folder, p.name = dst, os.path.dirname(dst), os.path.basename(dst)
        self.con.execute("UPDATE photos SET path=?,folder=?,name=? WHERE id=?", (p.path, p.folder, p.name, p.id))

    def _undo_move(self, done):
        errors = []
        for p, src, _, _ in done:
            try:
                self.con.execute("DELETE FROM photos WHERE path=? AND missing=1", (src,))
                back = unique_path(src)
                shutil.move(p.path, back)
                self._relocate(p, back)
            except OSError as ex:
                errors.append(f"{p.name}: {ex}")
        self.con.commit()
        if errors:
            QMessageBox.warning(self, APP, "\n".join(errors[:12]))
        self.apply_view()
        self.refresh_tree()
        self.status(T("{n} zurückverschoben", n=len(done) - len(errors)))

    def _after_removal(self, ids):
        current = self.edit.photo.id if self.in_editor() and self.edit.photo else None
        self.apply_view()
        self.refresh_tree()
        if current in ids:
            self.edit.drop_current()

    def trash_selection(self):
        photos = self.targets()
        if not photos:
            return
        done, errors = [], []
        for p in photos:
            ok, where = QFile.moveToTrash(p.path)
            if ok:
                done.append((p, p.path, where))
                p.missing = 1
            else:
                errors.append(p.name)
        with self.con:
            self.con.executemany("UPDATE photos SET missing=1 WHERE id=?", [(p.id,) for p, *_ in done])
        if errors:
            QMessageBox.warning(self, APP, T("Konnte nicht in den Papierkorb (z. B. auf Netzlaufwerken):") + "\n\n" + "\n".join(errors[:12]))
        if done:
            self.undo_stack.append(lambda: self._undo_trash(done))
            self.status(T("{n} im Papierkorb. Strg+Z holt sie zurück.", n=len(done)))
            self._after_removal({p.id for p, *_ in done})

    def _undo_trash(self, done):
        errors = []
        for p, src, where in done:
            try:
                shutil.move(where, src)
                if WINDOWS:
                    info = os.path.join(os.path.dirname(where), "$I" + os.path.basename(where)[2:])
                else:
                    info = os.path.join(os.path.dirname(os.path.dirname(where)), "info", os.path.basename(where) + ".trashinfo")
                if os.path.exists(info):
                    os.remove(info)
                p.missing = 0
                self.con.execute("UPDATE photos SET missing=0 WHERE id=?", (p.id,))
            except OSError as ex:
                errors.append(f"{p.name}: {ex}")
        self.con.commit()
        if errors:
            QMessageBox.warning(self, APP, "\n".join(errors[:12]))
        self.apply_view()
        self.refresh_tree()

    def reveal(self):
        photos = self.targets()
        if photos and WINDOWS:
            QProcess.startDetached("explorer.exe", ["/select," + os.path.normpath(photos[0].path)])
        elif photos and MAC:
            QProcess.startDetached("open", ["-R", photos[0].path])
        elif photos:
            QDesktopServices.openUrl(QUrl.fromLocalFile(photos[0].folder))

    def export_selection(self):
        photos = self.targets()
        if not photos:
            self.status(T("Erst Fotos auswählen"))
            return
        default = self.settings.value("export_dir", os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation), "MattPic-Export"))
        dlg = ExportDialog(self, len(photos), default)
        if not dlg.exec():
            return
        dest = os.path.normpath(os.path.expanduser(dlg.folder.text().strip()))
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as ex:
            QMessageBox.warning(self, APP, T("Zielordner geht nicht:") + f"\n{ex}")
            return
        self.settings.setValue("export_dir", dest)
        progress = QProgressDialog(T("Exportiere …"), T("Abbrechen"), 0, len(photos), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(200)
        worker = Exporter(self, photos, dest, dlg.size.currentData(), dlg.quality.currentData())
        errors = []
        worker.failed.connect(errors.append)
        worker.progress.connect(progress.setValue)
        progress.canceled.connect(lambda: setattr(worker, "stop", True))

        def finished():
            progress.close()
            if errors:
                QMessageBox.warning(self, APP, T("Nicht alles hat geklappt:") + "\n\n" + "\n".join(errors[:12]))
            self.status(T("{n} exportiert nach {dest}", n=len(photos) - len(errors), dest=dest))
        worker.finished.connect(finished)
        worker.start()

    def show_help(self):
        box = QMessageBox(self)
        box.setWindowTitle(T("Tastenkürzel"))
        box.setText(T(i18n.HELP_KEY))
        box.exec()

    def _grid_menu(self, pos):
        if self.grid.selected:
            self.photo_menu(pos)

    def photo_menu(self, pos):
        if not self.targets():
            return
        m = QMenu(self)
        if not self.in_editor():
            m.addAction(T("Öffnen"), lambda: self.open_photo(self.grid.selected_photos()[0]))
        self.fill_open_with(m.addMenu(T("Öffnen mit")))
        m.addSeparator()
        m.addAction(T("In Ordner verschieben …"), self.move_dialog)
        m.addAction(T("Exportieren …"), self.export_selection)
        m.addAction(T("Im Dateimanager zeigen"), self.reveal)
        m.addSeparator()
        m.addAction(T("In den Papierkorb"), self.trash_selection)
        m.exec(pos)

    def fill_open_with(self, menu):
        """Baut das Untermenü: PhotoCraft zuerst, dann was zum Dateityp passt, dann alle anderen."""
        menu.clear()
        photos = self.targets()
        if not photos:
            menu.addAction(T("Erst ein Foto auswählen")).setEnabled(False)
            return
        if WINDOWS or MAC:
            path = os.path.normpath(photos[0].path)
            menu.addAction(T("Standardprogramm"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(path)))
            menu.addAction(T("Anderes Programm …"),
                           lambda: self._windows_open_as(path) if WINDOWS else self._mac_open_with([p.path for p in photos]))
            return
        mime = QMimeDatabase().mimeTypeForFile(photos[0].path).name()
        if self.apps is None:
            self.apps = installed_apps()

        def add(app):
            menu.addAction(QIcon.fromTheme(app["icon"]), app["name"], lambda a=app: self.open_with(a))
        pinned = [a for a in self.apps if "photocraft" in a["id"]] if photos[0].kind != KIND_VIDEO else []
        fitting = [a for a in self.apps if a not in pinned and (mime in a["mime"] or mime.split("/")[0] + "/*" in a["mime"])]
        for app in pinned + fitting:
            add(app)
        if pinned or fitting:
            menu.addSeparator()
        menu.addAction(T("Anderes Programm …"), self._open_with_other)

    def _windows_open_as(self, path):
        """Der Windows-eigene Dialog „Öffnen mit“."""
        self.watch_external = True
        QProcess.startDetached("rundll32.exe", ["shell32.dll,OpenAs_RunDLL", path])

    def _mac_open_with(self, paths):
        """macOS: Programm im Ordner „Programme“ wählen und die Fotos mit `open -a` darin öffnen."""
        app, _ = QFileDialog.getOpenFileName(self, T("Öffnen mit"), "/Applications", "*.app")
        if app:
            self.watch_external = True
            QProcess.startDetached("open", ["-a", app] + paths[:30])

    def _open_with_other(self):
        names = [a["name"] for a in self.apps]
        name, ok = QInputDialog.getItem(self, T("Öffnen mit"), T("Programm:"), names, 0, False)
        if ok:
            self.open_with(self.apps[names.index(name)])

    def open_with(self, app):
        photos = self.targets()[:30]
        started = False
        for cmd in build_commands(app, [p.path for p in photos]):
            if FLATPAK:     # Aus dem Flatpak heraus startet das System das andere Programm
                cmd = ["flatpak-spawn", "--host"] + cmd
            started = QProcess.startDetached(cmd[0], cmd[1:])[0] or started
        if started:
            self.watch_external = True
            self.status(T("In {app} geöffnet. Speicherst du dort, kommt die Änderung hier automatisch an.", app=app["name"]))
        else:
            QMessageBox.warning(self, APP, T("{app} ließ sich nicht starten.", app=app["name"]))

    def changeEvent(self, e):
        # Zurück aus dem anderen Programm: nachsehen, ob dort gespeichert wurde
        if e.type() == QEvent.Type.ActivationChange and self.isActiveWindow() and self.watch_external:
            self.start_scan()
        super().changeEvent(e)

    # --- Ansichten

    def open_photo(self, photo):
        selected = self.grid.selected_photos()
        seq = selected if len(selected) > 1 and photo in selected else self.grid.flat
        self.stack.setCurrentWidget(self.edit)
        self.edit.open(seq, photo)

    def _back_to_library(self, photo):
        self.stack.setCurrentWidget(self.grid.parentWidget().parentWidget())
        self.grid.setFocus()
        if photo is not None:
            self.grid.select_photo(photo.id)

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("thumb", self.grid.size_px)
        self.settings.setValue("group", self.group.currentData())
        self.settings.setValue("sort", self.sort.currentData())
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop = True
            self.scanner.wait(1500)
        self.engine.shutdown()
        self.edit.loader.shutdown()
        super().closeEvent(e)


def log_exception(kind, value, tb):
    """PyQt beendet das Programm bei einem Fehler in einem Ereignis. Stattdessen melden und weiterarbeiten."""
    text = "".join(traceback.format_exception(kind, value, tb))
    sys.stderr.write(text)
    try:
        with open(os.path.join(DATA_DIR, "fehler.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S\n") + text + "\n")
    except OSError:
        pass
    for w in QApplication.topLevelWidgets():
        if isinstance(w, MainWindow):
            w.status(T("Interner Fehler: {error} (Details in fehler.log)", error=value))


def migrate_from_photomathias():
    """Übernimmt Datenbank und Einstellungen aus der Zeit, als das Programm PhotoMathias hieß."""
    if WINDOWS or MAC:
        return
    old = os.path.expanduser("~/.local/share/photomathias")
    if not os.environ.get("MATTPIC_DATA") and not os.path.exists(DATA_DIR) and os.path.isdir(old):
        try:
            os.rename(old, DATA_DIR)
        except OSError:
            pass
    cfg = os.path.expanduser("~/.config")
    old_cfg, new_cfg = os.path.join(cfg, "PhotoMathias", "PhotoMathias.conf"), os.path.join(cfg, APP_ID, APP_ID + ".conf")
    if not FLATPAK and os.path.isfile(old_cfg) and not os.path.exists(new_cfg):
        try:
            os.makedirs(os.path.dirname(new_cfg), exist_ok=True)
            shutil.copy2(old_cfg, new_cfg)
        except OSError:
            pass


def main():
    migrate_from_photomathias()
    sys.excepthook = log_exception
    Image.MAX_IMAGE_PIXELS = None
    QImageReader.setAllocationLimit(0)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP)
    app.setApplicationVersion(APP_VERSION)
    app.setDesktopFileName(os.environ.get("FLATPAK_ID") or "mattpic")
    # Sprache: im Menü gewählt, sonst die des Computers
    ui_lang = settings_store().value("ui_lang", "")
    i18n.set_language(ui_lang or i18n.pick_language(QLocale.system().uiLanguages()))
    qt_tr = QTranslator(app)
    for d in (QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath), "/app/translations", "/usr/share/qt6/translations"):
        if qt_tr.load(f"qtbase_{i18n.QT_TRANSLATION[i18n.language()]}", d):
            app.installTranslator(qt_tr)
            break
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    # Großansichten nur so groß wie der Bildschirm: Das hält Laden und Regler flott.
    global PREVIEW
    screen = app.primaryScreen().size() * app.primaryScreen().devicePixelRatio()
    PREVIEW = min(2560, max(1280, screen.width(), screen.height()))
    win = MainWindow()
    win.show()
    code = app.exec()
    win.settings.sync()
    os._exit(code)      # Hintergrund-Threads nicht abwarten, die Datenbank ist längst geschrieben


if __name__ == "__main__":
    main()
