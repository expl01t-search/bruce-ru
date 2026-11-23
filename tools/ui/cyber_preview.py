#!/usr/bin/env python3
"""Pixel-exact previews of the "КИБЕР" (cyberpunk) UI for Bruce on M5StickC Plus2.

This file is also the layout SPEC for the C++ implementation (src/core/ui_cyber.*):
every coordinate, size and colour below is what the firmware draws.

Screen 240x135 (rotation 3), TFT_eSPI GLCD font 5x8 (+ Cyrillic at 0x80..0xBF),
text sizes FP=1 (6x8 px cell), FM=2 (12x16), FG=3 (18x24). Colours are RGB565.

Usage: cyber_preview.py <out_dir> [scale]
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "i18n"))
import font_tool  # noqa: E402
import gen_i18n  # noqa: E402

W, H = 240, 135
FP, FM, FG = 1, 2, 3


def c565(hexrgb):
    """Quantise to RGB565 the way the panel shows it."""
    r, g, b = int(hexrgb[1:3], 16), int(hexrgb[3:5], 16), int(hexrgb[5:7], 16)
    v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    r5, g6, b5 = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return ((r5 * 527 + 23) >> 6, (g6 * 259 + 33) >> 6, (b5 * 527 + 23) >> 6), v


# ---------------- palette (default "Киберпанк" preset) ----------------
PALETTE = {
    "BG":      "#03050A",  # screen background
    "PANEL":   "#0A1222",  # status bar / footer / panels
    "GRID":    "#14263A",  # rails, separators, scrollbar track
    "DIM":     "#4E7088",  # secondary text, hints, inactive items
    "TEXT":    "#D6F4FF",  # main text
    "CYAN":    "#00E5FF",  # primary accent  (bruceConfig.priColor)
    "MAGENTA": "#FF2E88",  # secondary accent (bruceConfig.secColor)
    "YELLOW":  "#F2E205",  # warning
    "GREEN":   "#2BFF88",  # success
    "RED":     "#FF3344",  # error
    "INK":     "#03050A",  # text on filled accent
}
COL = {k: c565(v)[0] for k, v in PALETTE.items()}

GLYPHS = font_tool.read_font()
TABLES, ERR, _ = gen_i18n.load_all()
assert not ERR, ERR


def tr(text):
    b = text.encode("utf-8")
    v = TABLES["="].get(b.strip(b" "))
    return v if v is not None else b


def up(b):
    return bytes(c - 32 if 97 <= c <= 122 else (c - 0x20 if 0xA0 <= c <= 0xBF else c) for c in b)


class Canvas:
    def __init__(self, bg=COL["BG"]):
        self.px = [[bg] * W for _ in range(H)]

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def rect(self, x, y, w, h, c):
        for yy in range(max(0, y), min(H, y + h)):
            row = self.px[yy]
            for xx in range(max(0, x), min(W, x + w)):
                row[xx] = c

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def frame(self, x, y, w, h, c):
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def cutframe(self, x, y, w, h, cut, c, fill=None):
        """Rectangle with 45-degree cut top-left and bottom-right corners (the house shape)."""
        for yy in range(h):
            l = cut - yy if yy < cut else 0
            r = (yy - (h - 1 - cut)) if yy > h - 1 - cut else 0
            if fill is not None:
                self.rect(x + l, y + yy, w - l - r, 1, fill)
            self.put(x + l, y + yy, c)
            self.put(x + w - 1 - r, y + yy, c)
        self.hline(x + cut, y, w - cut, c)
        self.hline(x, y + h - 1, w - cut, c)

    def brackets(self, x, y, w, h, n, c):
        """Corner brackets just outside a box: the 'targeting' frame."""
        for (cx, cy, dx, dy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
            self.hline(min(cx, cx + dx * (n - 1)), cy, n, c)
            self.vline(cx, min(cy, cy + dy * (n - 1)), n, c)

    def char(self, x, y, code, s, c, bg=None):
        cols = GLYPHS[font_tool.glyph_index(code)]
        for i in range(6):
            line = cols[i] if i < 5 else 0
            for j in range(8):
                if (line >> j) & 1:
                    self.rect(x + i * s, y + j * s, s, s, c)
                elif bg is not None:
                    self.rect(x + i * s, y + j * s, s, s, bg)

    def text(self, x, y, b, s, c, bg=None):
        for k, ch in enumerate(b):
            self.char(x + k * 6 * s, y, ch, s, c, bg)
        return x + len(b) * 6 * s

    def centre(self, cx, y, b, s, c, bg=None):
        return self.text(cx - len(b) * 6 * s // 2, y, b, s, c, bg)

    def right(self, rx, y, b, s, c, bg=None):
        return self.text(rx - len(b) * 6 * s, y, b, s, c, bg)


# ---------------- shared chrome ----------------
STATUS_H = 13       # status bar 0..12, rail on y=13
CONTENT_Y = 16
FOOTER_Y = 124      # footer 124..134, rail on y=123


def status_bar(c, time=b"21:47", bat=87, tags=(b"SD", b"WIFI")):
    c.rect(0, 0, W, STATUS_H, COL["PANEL"])
    c.text(4, 3, time, FP, COL["CYAN"])
    # radio / storage tags, centred, active = cyan
    total = sum(len(t) * 6 for t in tags) + 6 * (len(tags) - 1)
    x = W // 2 - total // 2
    for t in tags:
        x = c.text(x, 3, t, FP, COL["DIM"]) + 6
    # battery: "87%" + 14x7 cell
    c.right(W - 22, 3, b"%d%%" % bat, FP, COL["CYAN"])
    bx, by = W - 19, 3
    c.frame(bx, by, 14, 7, COL["CYAN"])
    c.rect(bx + 14, by + 2, 1, 3, COL["CYAN"])
    c.rect(bx + 2, by + 2, max(1, 10 * bat // 100), 3, COL["CYAN"] if bat > 15 else COL["RED"])
    # neon rail: magenta line with a cyan lead segment
    c.hline(0, STATUS_H, W, COL["MAGENTA"])
    c.hline(0, STATUS_H, 36, COL["CYAN"])
    c.hline(W - 12, STATUS_H, 12, COL["CYAN"])


def footer(c, hint):
    c.hline(0, FOOTER_Y - 1, W, COL["GRID"])
    c.rect(0, FOOTER_Y, W, H - FOOTER_Y, COL["PANEL"])
    c.centre(W // 2, FOOTER_Y + 2, hint, FP, COL["DIM"])


# Plus2 buttons: PWR = prev (up), side B = next (down), M5 = select, PWR+B together = back/escape
HINT_MENU = gen_i18n.encode_ru("\x1e\x1f ВЫБОР  M5 ОК  PWR+B НАЗАД", "hint")


def header(c, title, counter=None):
    """List header: '>' + TITLE in caps, counter on the right, separator rail."""
    y = CONTENT_Y + 1
    c.text(4, y, b">", FP, COL["MAGENTA"])
    c.text(14, y, up(tr(title)), FP, COL["CYAN"])
    if counter:
        c.right(W - 4, y, counter, FP, COL["DIM"])
    c.hline(4, y + 10, W - 8, COL["GRID"])
    c.hline(4, y + 10, 18, COL["CYAN"])


# ---------------- screens ----------------
def boot(progress=0.7):
    c = Canvas()
    # scanlines
    for y in range(0, H, 2):
        c.hline(0, y, W, (6, 10, 20))
    logo = b"BRUCE"
    s = 4
    lx = W // 2 - len(logo) * 6 * s // 2
    c.text(lx - 2, 29, logo, s, COL["MAGENTA"])   # chromatic aberration: magenta up-left,
    c.text(lx + 2, 31, logo, s, COL["CYAN"])      # cyan down-right, white on top
    c.text(lx, 30, logo, s, COL["TEXT"])
    # one glitch band: a 2px slice of the logo shifted right by 8px
    band = [row[:] for row in c.px[46:48]]
    for i, row in enumerate(band):
        c.px[46 + i] = [COL["BG"]] * 8 + row[:-8]
    c.centre(W // 2, 66, tr("PREDATORY FIRMWARE"), FP, COL["MAGENTA"])
    # segmented progress
    segs, sw, gap = 24, 6, 2
    total = segs * (sw + gap) - gap
    x0 = W // 2 - total // 2
    for i in range(segs):
        on = i < int(segs * progress)
        c.rect(x0 + i * (sw + gap), 84, sw, 5, COL["CYAN"] if on else COL["GRID"])
    c.brackets(x0 - 4, 81, total + 8, 11, 4, COL["DIM"])
    c.text(x0, 98, tr("Booting") + b"...", FP, COL["DIM"])
    c.right(x0 + total, 98, b"%d%%" % int(progress * 100), FP, COL["CYAN"])
    c.centre(W // 2, 120, b"v1.17 // RU", FP, COL["GRID"])
    return c


def icon_wifi(c, cx, cy, col):
    """Placeholder pixel icon (firmware keeps Bruce's own vector icons, recoloured)."""
    for r, t in ((18, 2), (12, 2), (6, 2)):
        for dx in range(-r, r + 1):
            for dy in range(-r, 1):
                d2 = dx * dx + dy * dy
                if (r - t) ** 2 <= d2 <= r * r and dy <= -abs(dx) * 0.55:
                    c.put(cx + dx, cy + dy, col)
    c.rect(cx - 2, cy - 2, 4, 4, col)


def icon_gear(c, cx, cy, col):
    import math
    for a in range(0, 360, 2):
        for rr in range(9, 13):
            c.put(int(cx + rr * math.cos(math.radians(a))), int(cy + rr * math.sin(math.radians(a))), col)
    for k in range(8):
        a = math.radians(k * 45)
        for rr in range(13, 18):
            for w in (-2, -1, 0, 1, 2):
                c.put(int(cx + rr * math.cos(a) - w * math.sin(a)), int(cy + rr * math.sin(a) + w * math.cos(a)), col)
    for a in range(0, 360, 3):
        for rr in range(0, 4):
            c.put(int(cx + rr * math.cos(math.radians(a))), int(cy + rr * math.sin(math.radians(a))), col)


def main_menu(name="WiFi", idx=1, total=16, prev="Config", nxt="BLE", icon=icon_wifi):
    c = Canvas()
    status_bar(c)
    y = CONTENT_Y + 1
    c.text(4, y, b"//", FP, COL["MAGENTA"])
    c.text(18, y, up(tr("Main Menu")), FP, COL["DIM"])
    cnt = b"%02d/%02d" % (idx, total)
    c.right(W - 4, y, cnt, FP, COL["CYAN"])
    # icon chamber: cut-corner box + magenta targeting brackets
    bx, by, bw, bh = 86, 33, 68, 50
    c.cutframe(bx, by, bw, bh, 7, COL["CYAN"], fill=COL["PANEL"])
    c.brackets(bx - 4, by - 3, bw + 8, bh + 6, 5, COL["MAGENTA"])
    icon(c, bx + bw // 2, by + bh // 2 + (6 if icon is icon_wifi else 0), COL["CYAN"])
    # neighbours: small arrows + names of the previous / next module
    c.text(14, 50, b"\x11", FM, COL["MAGENTA"])
    c.text(W - 14 - 12, 50, b"\x10", FM, COL["MAGENTA"])
    c.text(4, 72, tr(prev)[:11], FP, COL["DIM"])
    c.right(W - 4, 72, tr(nxt)[:11], FP, COL["DIM"])
    # title + underline + cursor
    t = tr(name)
    tx = W // 2 - (len(t) + 1) * 12 // 2
    end = c.text(tx, 92, t, FM, COL["TEXT"])
    c.rect(end + 2, 92 + 12, 9, 3, COL["MAGENTA"])  # blinking block cursor "_"
    c.hline(tx, 110, end - tx, COL["CYAN"])
    c.hline(tx - 8, 110, 6, COL["MAGENTA"])
    footer(c, HINT_MENU)
    return c


ROW_H, ROWS_Y, ROWS_N = 18, 31, 5


def list_screen(title, items, sel, top=0, disabled=(), scroll_label=None):
    c = Canvas()
    status_bar(c)
    header(c, title, b"%d/%d" % (sel + 1, len(items)))
    for k in range(ROWS_N):
        i = top + k
        if i >= len(items):
            break
        y = ROWS_Y + k * ROW_H
        lab = tr(items[i])
        if i == sel:
            # selected: cyan bar with cut right corner, magenta tab, ink text
            c.rect(4, y, 3, ROW_H - 2, COL["MAGENTA"])
            for yy in range(ROW_H - 2):
                cut = max(0, yy - (ROW_H - 2 - 6))
                c.rect(8, y + yy, 222 - cut, 1, COL["CYAN"])
            shown = (scroll_label or lab)[:17]
            c.text(12, y + 1, shown, FM, COL["INK"])
            c.text(218, y + 5, b"\x10", FP, COL["INK"])
        else:
            col = COL["DIM"] if i in disabled else COL["TEXT"]
            c.text(9, y + 5, b"\x07", FP, COL["GRID"] if i in disabled else COL["MAGENTA"])
            if len(lab) > 17:  # too long: 16 chars + dim ".." (the selected row scrolls instead)
                end = c.text(18, y + 1, lab[:16], FM, col)
                c.text(end + 1, y + 8, b"..", FP, COL["DIM"])
            else:
                c.text(18, y + 1, lab, FM, col)
    # scrollbar
    tr_y, tr_h = ROWS_Y, ROWS_N * ROW_H - 2
    c.vline(236, tr_y, tr_h, COL["GRID"])
    if len(items) > ROWS_N:
        th = max(6, tr_h * ROWS_N // len(items))
        ty = tr_y + (tr_h - th) * top // max(1, len(items) - ROWS_N)
        c.rect(235, ty, 3, th, COL["CYAN"])
    footer(c, HINT_MENU)
    return c


TOAST = {
    "error":   ("RED",     b"[!] ", "Error"),
    "warning": ("YELLOW",  b"[?] ", "Warning"),
    "info":    ("CYAN",    b"[i] ", "Info"),
    "success": ("GREEN",   b"[+] ", "Success"),
    "line":    ("MAGENTA", b"[>] ", "Message"),
}
EXTRA = {"Warning": "ВНИМАНИЕ", "Info": "ИНФО", "Success": "ГОТОВО", "Message": "СООБЩЕНИЕ", "Error": "ОШИБКА"}


def enc_ru(s):
    return gen_i18n.encode_ru(s, "preview")


def wrap(b, maxc):
    lines, rest = [], b
    while rest:
        if len(rest) <= maxc:
            lines.append(rest)
            break
        cut = max((i for i in range(maxc) if rest[i:i + 1] == b" "), default=maxc)
        lines.append(rest[:cut])
        rest = rest[cut + 1:]
    return lines


def toast(kind, msg, under=None):
    c = under or Canvas()
    if under is None:
        status_bar(c)
        footer(c, enc_ru("ЛЮБАЯ КНОПКА - ДАЛЕЕ"))
    colname, tag, word = TOAST[kind]
    col = COL[colname]
    t = tr(msg)
    size = FM if len(t) <= 16 else FP
    lines = wrap(t, 17 if size == FM else 34)
    lh = 8 * size + 3
    bw, bh = 220, 16 + len(lines) * lh + 8
    bx, by = (W - bw) // 2, (CONTENT_Y + FOOTER_Y) // 2 - bh // 2 + 2
    c.cutframe(bx, by, bw, bh, 6, col, fill=COL["PANEL"])
    head = tag + enc_ru(EXTRA[word])
    c.rect(bx + 8, by - 4, len(head) * 6 + 8, 11, col)
    c.text(bx + 12, by - 2, head, FP, COL["INK"])
    for i, ln in enumerate(lines):
        c.centre(W // 2, by + 14 + i * lh, ln, size, COL["TEXT"])
    c.brackets(bx - 3, by - 3, bw + 6, bh + 6, 4, COL["DIM"])
    return c


def dialog(msg, buttons, sel):
    c = Canvas()
    status_bar(c)
    header(c, "Confirm")
    lines = msg.split("\n")
    for i, ln in enumerate(lines):
        c.centre(W // 2, 38 + i * 18, enc_ru(ln), FM, COL["TEXT"])
    bw, gap = 66, 8
    x0 = W // 2 - (len(buttons) * bw + (len(buttons) - 1) * gap) // 2
    for i, b in enumerate(buttons):
        x = x0 + i * (bw + gap)
        lab = enc_ru(b)
        if i == sel:
            c.cutframe(x, 94, bw, 22, 5, COL["CYAN"], fill=COL["CYAN"])
            c.centre(x + bw // 2, 97, lab, FM, COL["INK"])
        else:
            c.cutframe(x, 94, bw, 22, 5, COL["DIM"])
            c.centre(x + bw // 2, 97, lab, FM, COL["TEXT"])
    footer(c, enc_ru("\x11\x10 ВЫБОР   M5 OK"))
    return c


def progress(msg, frac):
    c = Canvas()
    status_bar(c)
    header(c, "Running, Wait")
    c.centre(W // 2, 44, tr(msg), FM, COL["TEXT"])
    segs, sw, gap = 20, 9, 2
    total = segs * (sw + gap) - gap
    x0 = W // 2 - total // 2
    for i in range(segs):
        on = i < int(segs * frac)
        c.rect(x0 + i * (sw + gap), 72, sw, 10, COL["CYAN"] if on else COL["GRID"])
    c.brackets(x0 - 4, 68, total + 8, 18, 5, COL["MAGENTA"])
    c.text(x0, 92, b"2.1/3.4 MB", FP, COL["DIM"])
    c.right(x0 + total, 92, b"%d%%" % int(frac * 100), FM, COL["MAGENTA"])
    footer(c, enc_ru("PWR+B ОТМЕНА"))
    return c


def info_screen():
    c = Canvas()
    status_bar(c)
    header(c, "Device Info")
    rows = [("Bruce Version:", b"1.17-ru"), ("Free heap:", b"112 KB"), ("Free PSRAM:", b"1.9 MB"),
            ("Battery:", b"87% 4.05V"), ("SD Card free:", b"--"), ("MAC addr:", b"00:4B:12:C4:8A:28"),
            ("Rotation:", b"3")]
    y = 31
    for k, v in rows:
        c.text(6, y, tr(k), FP, COL["DIM"])
        c.right(W - 6, y, v, FP, COL["TEXT"])
        c.hline(6, y + 10, W - 12, (10, 20, 32))
        y += 13
    footer(c, enc_ru("PWR+B НАЗАД"))
    return c


def overlay_menu():
    """Compact context menu (drawOptions with border) floating over a running tool."""
    c = info_screen()
    # dim the background
    for yy in range(H):
        for xx in range(W):
            r, g, b = c.px[yy][xx]
            c.px[yy][xx] = (r // 3, g // 3, b // 3)
    items = ["Save", "Rename", "Delete", "Back"]
    bx, by, bw = 30, 20, 180
    bh = 14 + len(items) * 18 + 4
    c.cutframe(bx, by, bw, bh, 6, COL["MAGENTA"], fill=COL["PANEL"])
    c.text(bx + 10, by + 4, up(enc_ru("ДЕЙСТВИЯ")), FP, COL["MAGENTA"])
    for i, it in enumerate(items):
        y = by + 15 + i * 18
        if i == 0:
            c.rect(bx + 4, y, bw - 8, 16, COL["CYAN"])
            c.text(bx + 10, y + 1, tr(it), FM, COL["INK"])
        else:
            c.text(bx + 10, y + 1, tr(it), FM, COL["TEXT"])
    return c


def palette_sheet():
    c = Canvas()
    names = ["BG", "PANEL", "GRID", "DIM", "TEXT", "CYAN", "MAGENTA", "YELLOW", "GREEN", "RED"]
    for i, n in enumerate(names):
        x = 6 + (i % 5) * 46
        y = 8 + (i // 5) * 62
        c.rect(x, y, 40, 36, COL[n])
        c.frame(x, y, 40, 36, COL["GRID"])
        c.text(x, y + 40, n.encode()[:7], FP, COL["TEXT"])
        c.text(x, y + 50, PALETTE[n][1:].encode(), FP, COL["DIM"])
    return c


def font_sheet():
    c = Canvas()
    status_bar(c)
    c.text(6, 20, b"FP 6x8:", FP, COL["DIM"])
    c.text(60, 20, enc_ru("подсказки, статус"), FP, COL["TEXT"])
    c.text(6, 36, b"FM:", FP, COL["DIM"])
    c.text(30, 32, enc_ru("Пункт меню"), FM, COL["TEXT"])
    c.text(6, 62, b"FG:", FP, COL["DIM"])
    c.text(30, 56, enc_ru("Заголовок"), FG, COL["CYAN"])
    c.text(6, 88, enc_ru("Символы:"), FP, COL["DIM"])
    c.text(60, 86, b"\x10 \x11 \x1e \x1f \x07 \x04", FM, COL["MAGENTA"])
    c.text(6, 108, enc_ru("АБВГДЕЖЗИЙКЛМНОП абвгдежзийклмноп"), FP, COL["TEXT"])
    return c


def write_png(path, cv, scale=3):
    tw, th = W * scale, H * scale
    rows = []
    for y in range(H):
        line = bytearray()
        for x in range(W):
            line += bytes(cv.px[y][x]) * scale
        rows.extend([b"\x00" + bytes(line)] * scale)
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", tw, th, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def screens():
    cfg = ["Display & UI", "Audio Config", "System Config", "Power", "About", "Main Menu"]
    wifi = ["Connect to Wifi", "WiFi Pass Recovery", "Evil Portal", "Wifi Atks", "Channel Analyzer",
            "Wardriving", "Back"]
    return {
        "01_boot": boot(0.7),
        "02_main_wifi": main_menu("WiFi", 1, 16, "Config", "BLE", icon_wifi),
        "03_main_config": main_menu("Config", 16, 16, "Wire Tools", "WiFi", icon_gear),
        "04_list_config": list_screen("Config", cfg, 0),
        "05_list_wifi": list_screen("WiFi", wifi, 1, top=0, disabled=(5,)),
        "06_toast_error": toast("error", "Cannot open file"),
        "07_toast_success": toast("success", "File saved!"),
        "08_toast_warning": toast("warning", "Key delay is below 50ms. You may experience issues with missing keys."),
        "09_toast_info": toast("info", "Connecting..."),
        "10_dialog": dialog("Сброс настроек?\nВсе данные удалятся", ["ДА", "НЕТ"], 1),
        "11_progress": progress("Uploading...", 0.62),
        "12_info": info_screen(),
        "13_overlay_menu": overlay_menu(),
        "14_palette": palette_sheet(),
        "15_type": font_sheet(),
    }


def main():
    out = sys.argv[1]
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    os.makedirs(out, exist_ok=True)
    for name, cv in screens().items():
        write_png(os.path.join(out, name + ".png"), cv, scale)
    for k, v in PALETTE.items():
        print("%-8s %s  rgb565=0x%04X" % (k, v, c565(v)[1]))
    print("wrote", len(screens()), "screens to", out)


if __name__ == "__main__":
    main()
