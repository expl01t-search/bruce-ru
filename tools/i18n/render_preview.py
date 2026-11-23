#!/usr/bin/env python3
"""Render Bruce screens (240x135, rotation 3) with the patched GLCD font and the Russian
dictionary, mimicking display.cpp layout rules, to check glyphs and text fit visually.

Usage: render_preview.py <out.png>
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font_tool  # noqa: E402
import gen_i18n  # noqa: E402

W, H = 240, 135
LW, LH = 6, 8
FP, FM, FG = 1, 2, 3
PRI = (160, 0, 255)      # Bruce default purple
BG = (0, 0, 0)
SEC = (200, 160, 255)
WHITE = (255, 255, 255)
RED = (220, 0, 0)

GLYPHS = font_tool.read_font()
TABLES, ERR, _ = gen_i18n.load_all()
assert not ERR, ERR


def tr(text):
    """Exact-match translation (enough for previews) -> firmware bytes."""
    b = text.encode("utf-8")
    core = b.strip(b" \n")
    v = TABLES["="].get(core)
    if v is None:
        return b
    lead = b[: len(b) - len(b.lstrip(b" \n"))]
    trail = b[len(b.rstrip(b" \n")):]
    return lead + v + trail


def upper(b):
    return bytes(c - 32 if 97 <= c <= 122 else (c - 0x20 if 0xA0 <= c <= 0xBF else c) for c in b)


class Canvas:
    def __init__(self):
        self.px = [[BG] * W for _ in range(H)]

    def rect(self, x, y, w, h, col):
        for yy in range(max(0, y), min(H, y + h)):
            row = self.px[yy]
            for xx in range(max(0, x), min(W, x + w)):
                row[xx] = col

    def frame(self, x, y, w, h, col):
        self.rect(x, y, w, 1, col)
        self.rect(x, y + h - 1, w, 1, col)
        self.rect(x, y, 1, h, col)
        self.rect(x + w - 1, y, 1, h, col)

    def char(self, x, y, code, size, col, bg=None):
        if code < 32:
            return
        cols = GLYPHS[font_tool.glyph_index(code)]
        for i in range(6):
            line = cols[i] if i < 5 else 0
            for j in range(8):
                on = (line >> j) & 1
                if on or bg is not None:
                    self.rect(x + i * size, y + j * size, size, size, col if on else bg)

    def text(self, x, y, b, size, col, bg=None):
        for k, c in enumerate(b):
            self.char(x + k * 6 * size, y, c, size, col, bg)

    def centre(self, cx, y, b, size, col, bg=None):
        self.text(cx - len(b) * 6 * size // 2, y, b, size, col, bg)


def submenu(title, labels, index):
    """drawSubmenu(): title FP top-left, selected label FG (or FM if long), neighbours FM."""
    c = Canvas()
    c.frame(1, 1, W - 2, H - 2, PRI)
    c.text(10, 5, b"BRUCE 1.15", FP, PRI)
    c.text(10, 20, tr(title), FP, PRI)
    sel = tr(labels[index])
    sz = FG if len(sel) <= W // (LW * FG) - 1 else FM
    top, bottom = 20 + LH * FP + 4, H - 2
    middle = top + (bottom - top) // 2
    pitch = FG * LH + FP * (LH // 2)
    for k in (-1, 1):
        idx = (index + k) % len(labels)
        c.centre(W // 2, middle + k * pitch - FM * LH // 2, tr(labels[idx]), FM, SEC)
    c.centre(W // 2, middle - sz * LH // 2, sel, sz, PRI)
    c.rect(W // 2 - len(sel) * sz * LW // 2, middle + sz * LH // 2 + 1, len(sel) * sz * LW, 1, PRI)
    return c


def listmenu(labels, index):
    """drawOptions(): bordered list, rows of FM text, selected row highlighted with '>'."""
    c = Canvas()
    row = FM * LH + 4
    c.frame(1, 1, W - 2, H - 2, PRI)
    y = 10
    for i, lab in enumerate(labels[:6]):
        t = (b">" if i == index else b" ") + tr(lab)
        t = t[: (W - 2 - 10) // (LW * FM) - 1]
        if i == index:
            c.rect(3, y + 2, W - 6, FM * LH + 2, PRI)
            c.text(6, y + 4, t, FM, BG, PRI)
        else:
            c.text(6, y + 4, t, FM, WHITE)
        y += row
    return c


def stripe(msg, fg=WHITE, bgcol=RED):
    """displayRedStripe(): FM when it fits on one line, otherwise FP with word wrap."""
    c = Canvas()
    t = tr(msg)
    pad = 5
    if len(t) * LW * FM < W - 2 * FM * LW:
        size, maxc = FM, (W - 2 * pad) // (LW * FM)
    else:
        size, maxc = FP, (W - 2 * pad) // (LW * FP)
    lines, rest = [], t
    while rest:
        if len(rest) <= maxc:
            lines.append(rest)
            break
        cut = max((i for i in range(maxc) if rest[i:i + 1] in (b" ", b"-", b"_")), default=-1)
        if cut <= 0:
            cut = maxc
        lines.append(rest[:cut])
        rest = rest[cut + 1:]
    lh = LH * size + 2
    box = len(lines) * lh + 8
    c.rect(pad, H // 2 - box // 2, W - 2 * pad, box, bgcol)
    y0 = H // 2 - len(lines) * lh // 2
    for i, ln in enumerate(lines):
        c.centre(W // 2, y0 + i * lh, ln, size, fg, bgcol)
    return c


def mainmenu(name):
    """MenuItemInterface::draw(): icon area + centred title in FM, cut to 18 chars."""
    c = Canvas()
    c.frame(1, 1, W - 2, H - 2, PRI)
    c.text(10, 5, b"12:34", FP, PRI)
    c.frame(W // 2 - 30, 25, 60, 60, PRI)
    t = tr(name)[: (W - 16) // (LW * FM)]
    c.centre(W // 2, H - 30, t, FM, PRI)
    c.text(12, 50, b"<", FG, PRI)
    c.text(W - 30, 50, b">", FG, PRI)
    return c


def title_screen(title, lines):
    c = Canvas()
    c.frame(1, 1, W - 2, H - 2, PRI)
    t = upper(tr(title))
    size = FM
    while size > FP and len(t) * size * LW > W - 10:
        size -= 1
    c.text((W - len(t) * size * LW) // 2, 10, t, size, PRI)
    y = 10 + FM * LH + 6
    for ln in lines:
        c.text(5, y, tr(ln), FP, WHITE)
        y += LH * FP + 2
    return c


def write_png(path, canvases, scale=2, cols=2):
    rows = (len(canvases) + cols - 1) // cols
    gap = 6
    tw = cols * W * scale + (cols + 1) * gap
    th = rows * H * scale + (rows + 1) * gap
    img = [[(60, 60, 60)] * tw for _ in range(th)]
    for n, cv in enumerate(canvases):
        ox = gap + (n % cols) * (W * scale + gap)
        oy = gap + (n // cols) * (H * scale + gap)
        for y in range(H):
            for x in range(W):
                p = cv.px[y][x]
                for dy in range(scale):
                    r = img[oy + y * scale + dy]
                    for dx in range(scale):
                        r[ox + x * scale + dx] = p
    raw = b"".join(b"\x00" + bytes(v for p in row for v in p) for row in img)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", tw, th, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main():
    out = sys.argv[1]
    screens = [
        mainmenu("Config"),
        submenu("Config", ["Display & UI", "Audio Config", "System Config", "Power", "About", "Main Menu"], 0),
        listmenu(["Brightness", "Dim Time", "Orientation", "Menu Layout", "UI Color", "Language: Russian"], 5),
        submenu("WiFi", ["Connect to Wifi", "WiFi Pass Recovery", "Evil Portal", "Wifi Atks", "Back"], 1),
        stripe("Are you sure you want\nto Factory Reset?\nAll data will be lost!".replace("\n", " ")),
        stripe("Cannot open file", WHITE, (0, 120, 0)),
        title_screen("Device Info", ["Bruce Version: ", "Free heap: ", "Battery: ", "SD Card free: "]),
        listmenu(["Scan Hosts", "ARP Spoofing", "DHCP Starvation", "MAC Flooding", "Station Deauth", "Back"], 0),
    ]
    write_png(out, screens)
    print("wrote", out)


if __name__ == "__main__":
    main()
