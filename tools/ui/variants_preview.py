#!/usr/bin/env python3
"""Two alternative UI directions for Bruce RU (pixel-exact, 240x135, GLCD 5x8 + Cyrillic, RGB565).

  B "ФОСФОР"   - monochrome green CRT terminal: square boxes, inverse selection, scanlines.
  C "HUD-2077" - yellow/black combat HUD with red accents: slanted tabs, hazard stripes.

Usage: variants_preview.py <out_dir> [scale]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cyber_preview as cp  # noqa: E402

W, H, FP, FM, FG = cp.W, cp.H, cp.FP, cp.FM, cp.FG
tr, up, enc = cp.tr, cp.up, cp.enc_ru


def pal(d):
    return {k: cp.c565(v)[0] for k, v in d.items()}


PAL_B = {"BG": "#000A03", "PANEL": "#00160A", "GRID": "#0A3A1A", "DIM": "#2F8F4E", "TEXT": "#A8FFC0",
         "PRI": "#39FF6A", "SEC": "#C8FF3A", "RED": "#FF5A3C", "YEL": "#FFD23C", "GREEN": "#39FF6A",
         "INFO": "#7DFFDE", "INK": "#000A03"}
PAL_C = {"BG": "#0B0B08", "PANEL": "#17150A", "GRID": "#3A3410", "DIM": "#9A8C3C", "TEXT": "#F4EFD6",
         "PRI": "#FCEE0A", "SEC": "#FF003C", "RED": "#FF003C", "YEL": "#FCEE0A", "GREEN": "#5CFF3A",
         "INFO": "#00F0FF", "INK": "#0B0B08"}


# ---------------- extra primitives ----------------
def dashed(c, x, y, w, col, on=2, off=2):
    for xx in range(x, x + w):
        if (xx - x) % (on + off) < on:
            c.put(xx, y, col)


def scanlines(c, k=0.72):
    for y in range(1, H, 2):
        c.px[y] = [(int(r * k), int(g * k), int(b * k)) for (r, g, b) in c.px[y]]


def para(c, x, y, w, h, slant, col, left=True, right=True):
    """Parallelogram-ish bar: edges slanted by `slant` px over its height (HUD tabs)."""
    for yy in range(h):
        off = slant * (h - 1 - yy) // max(1, h - 1)
        l = x + (off if left else 0)
        r = x + w - (slant - off if right else 0)
        c.rect(l, y + yy, r - l, 1, col)


def hazard(c, x, y, w, h, a, b, period=8):
    for yy in range(h):
        for xx in range(w):
            c.put(x + xx, y + yy, a if ((xx + yy) // (period // 2)) % 2 == 0 else b)


def cut4(c, x, y, w, h, cut, col, fill=None, thick=1):
    """Box with all four corners cut (octagon-ish), optional fill, 1-2 px outline."""
    for t in range(thick):
        xx, yy, ww, hh, cc = x + t, y + t, w - 2 * t, h - 2 * t, cut
        for r in range(hh):
            if r < cc:
                d = cc - r
            elif r > hh - 1 - cc:
                d = r - (hh - 1 - cc)
            else:
                d = 0
            if fill is not None and t == 0:
                c.rect(xx + d, yy + r, ww - 2 * d, 1, fill)
            c.put(xx + d, yy + r, col)
            c.put(xx + ww - 1 - d, yy + r, col)
        c.hline(xx + cc, yy, ww - 2 * cc, col)
        c.hline(xx + cc, yy + hh - 1, ww - 2 * cc, col)


def battery(c, x, y, pct, col, low):
    c.frame(x, y, 14, 7, col)
    c.rect(x + 14, y + 2, 1, 3, col)
    c.rect(x + 2, y + 2, max(1, 10 * pct // 100), 3, col if pct > 15 else low)


HINT = enc("\x1e\x1f ВЫБОР  M5 ОК  PWR+B НАЗАД")


# =====================================================================
# Variant B: "ФОСФОР" (green phosphor terminal)
# =====================================================================
class B:
    P = pal(PAL_B)

    @classmethod
    def canvas(cls):
        return cp.Canvas(cls.P["BG"])

    @classmethod
    def chrome(cls, c, hint=HINT):
        P = cls.P
        c.text(4, 3, b"21:47", FP, P["PRI"])
        c.centre(W // 2, 3, b"[SD] [WIFI]", FP, P["DIM"])
        c.right(W - 22, 3, b"87%", FP, P["PRI"])
        battery(c, W - 19, 3, 87, P["PRI"], P["RED"])
        dashed(c, 0, 13, W, P["DIM"])
        dashed(c, 0, 123, W, P["GRID"])
        c.centre(W // 2, 126, hint, FP, P["DIM"])

    @classmethod
    def header(cls, c, title, counter=None):
        P = cls.P
        t = b"[ " + up(tr(title)) + b" ]"
        c.text(4, 17, t, FP, P["PRI"])
        if counter:
            c.right(W - 4, 17, counter, FP, P["DIM"])
        c.hline(4, 27, W - 8, P["GRID"])

    @classmethod
    def boot(cls):
        P = cls.P
        c = cls.canvas()
        lines = [(b"BRUCE OS v1.17-ru", P["TEXT"], None),
                 (b"> init display .....", P["DIM"], (b"OK", P["PRI"])),
                 (b"> mount littlefs ...", P["DIM"], (b"OK", P["PRI"])),
                 (b"> sd card ..........", P["DIM"], (b"--", P["YEL"])),
                 (b"> load bruce.conf ..", P["DIM"], (b"OK", P["PRI"])),
                 (b"> lang ru ..........", P["DIM"], (b"OK", P["PRI"]))]
        y = 6
        for txt, col, st in lines:
            end = c.text(6, y, txt, FP, col)
            if st:
                c.text(end + 6, y, st[0], FP, st[1])
            y += 11
        c.text(6, 80, tr("PREDATORY FIRMWARE"), FM, P["PRI"])
        c.rect(6 + len(tr("PREDATORY FIRMWARE")) * 12 + 4, 80, 10, 15, P["PRI"])  # block cursor
        bar = b"[" + b"#" * 13 + b"." * 6 + b"] 70%"
        c.text(6, 108, bar, FP, P["DIM"])
        c.text(12, 108, b"#" * 13, FP, P["PRI"])
        scanlines(c)
        return c

    @classmethod
    def main_menu(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c)
        c.text(4, 17, b"$ ls /bruce", FP, P["DIM"])
        c.right(W - 4, 17, b"01/16", FP, P["PRI"])
        bx, by, bw, bh = 82, 30, 76, 54
        c.frame(bx, by, bw, bh, P["PRI"])
        c.frame(bx + 2, by + 2, bw - 4, bh - 4, P["GRID"])
        cp.icon_wifi(c, bx + bw // 2, by + bh // 2 + 7, P["PRI"])
        c.text(6, 52, b"<<", FM, P["DIM"])
        c.right(W - 6, 52, b">>", FM, P["DIM"])
        c.text(6, 72, tr("Config")[:11], FP, P["DIM"])
        c.right(W - 6, 72, b"BLE", FP, P["DIM"])
        t = b"> " + tr("WiFi").upper()
        tx = W // 2 - (len(t) + 1) * 12 // 2
        end = c.text(tx, 92, t, FM, P["PRI"])
        c.rect(end + 2, 92, 10, 15, P["PRI"])
        scanlines(c)
        return c

    @classmethod
    def list_screen(cls):
        P = cls.P
        items = ["Connect to Wifi", "WiFi Pass Recovery", "Evil Portal", "Wifi Atks", "Channel Analyzer",
                 "Wardriving", "Back"]
        sel = 1
        c = cls.canvas()
        cls.chrome(c)
        cls.header(c, "WiFi", b"02/07")
        for k in range(5):
            y = 31 + k * 18
            lab = tr(items[k])
            if k == sel:
                c.rect(2, y, W - 12, 16, P["PRI"])
                c.text(4, y + 1, b">" + lab[:17], FM, P["INK"])
            else:
                if len(lab) > 17:
                    end = c.text(4, y + 1, b" " + lab[:15], FM, P["TEXT"])
                    c.text(end + 1, y + 8, b"..", FP, P["DIM"])
                else:
                    c.text(4, y + 1, b" " + lab, FM, P["TEXT"])
        c.text(W - 8, 31, b"\x1e", FP, P["GRID"])
        c.text(W - 8, 111, b"\x1f", FP, P["PRI"])
        scanlines(c)
        return c

    @classmethod
    def toast(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("ЛЮБАЯ КНОПКА - ДАЛЕЕ"))
        bx, by, bw, bh = 12, 38, 216, 52
        c.rect(bx, by, bw, bh, P["BG"])
        c.frame(bx, by, bw, bh, P["RED"])
        c.frame(bx + 2, by + 2, bw - 4, bh - 4, P["RED"])
        c.centre(W // 2, by + 8, enc("*** ОШИБКА ***"), FP, P["RED"])
        c.centre(W // 2, by + 26, tr("Cannot open file"), FP, P["TEXT"])
        c.centre(W // 2, by + 38, b"ERR 0x02 ENOENT", FP, P["DIM"])
        scanlines(c)
        return c

    @classmethod
    def dialog(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("\x11\x10 ВЫБОР  M5 ОК"))
        cls.header(c, "Confirm")
        c.text(6, 38, enc("Сброс настроек?"), FM, P["TEXT"])
        c.text(6, 58, enc("Все данные удалятся."), FP, P["DIM"])
        c.text(6, 68, enc("Действие необратимо."), FP, P["DIM"])
        c.text(30, 96, enc("[ ДА ]"), FM, P["TEXT"])
        c.rect(124, 94, 88, 20, P["PRI"])
        c.text(130, 96, enc(">НЕТ<"), FM, P["INK"])
        scanlines(c)
        return c

    @classmethod
    def progress(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("PWR+B ОТМЕНА"))
        cls.header(c, "Running, Wait")
        c.text(6, 38, tr("Uploading..."), FM, P["TEXT"])
        c.text(6, 66, b"[" + b"#" * 11 + b"." * 6 + b"]", FM, P["DIM"])
        c.text(18, 66, b"#" * 11, FM, P["PRI"])
        c.text(6, 90, b"2.1/3.4 MB  ETA 0:14", FP, P["DIM"])
        c.right(W - 6, 88, b"62%", FM, P["SEC"])
        scanlines(c)
        return c


# =====================================================================
# Variant C: "HUD-2077" (yellow/black combat HUD)
# =====================================================================
class C:
    P = pal(PAL_C)

    @classmethod
    def canvas(cls):
        return cp.Canvas(cls.P["BG"])

    @classmethod
    def chrome(cls, c, hint=HINT):
        P = cls.P
        c.rect(0, 0, W, 13, P["PANEL"])
        para(c, 0, 0, 44, 13, 6, P["PRI"], left=False)
        c.text(4, 3, b"21:47", FP, P["INK"])
        c.centre(W // 2, 3, b"SD // WIFI", FP, P["DIM"])
        c.right(W - 22, 3, b"87", FP, P["PRI"])
        battery(c, W - 19, 3, 87, P["PRI"], P["RED"])
        c.rect(0, 13, W, 2, P["PRI"])
        c.rect(150, 13, 30, 2, P["SEC"])
        # footer: hazard tab + hints
        c.rect(0, 124, W, 11, P["PANEL"])
        hazard(c, 0, 124, 20, 11, P["PRI"], P["BG"])
        c.text(26, 126, hint, FP, P["DIM"])

    @classmethod
    def header(cls, c, title, counter=None):
        P = cls.P
        t = up(tr(title))
        w = len(t) * 6 + 16
        para(c, 2, 18, w, 11, 5, P["PRI"], left=False)
        c.text(7, 20, t, FP, P["INK"])
        c.text(w + 6, 20, b"//", FP, P["SEC"])
        if counter:
            c.right(W - 4, 20, counter, FP, P["PRI"])

    @classmethod
    def boot(cls):
        P = cls.P
        c = cls.canvas()
        hazard(c, 0, 0, W, 6, P["PRI"], P["BG"])
        hazard(c, 0, H - 6, W, 6, P["PRI"], P["BG"])
        logo = b"BRUCE"
        lx = W // 2 - len(logo) * 24 // 2
        c.text(lx + 3, 27, logo, 4, P["SEC"])
        c.text(lx, 24, logo, 4, P["PRI"])
        # diagonal red slash through the logo
        for i in range(70):
            c.rect(150 - i, 20 + i // 2 * 1, 3, 1, P["SEC"]) if i < 0 else None
        c.rect(0, 40, 12, 2, P["SEC"])
        c.rect(W - 12, 40, 12, 2, P["SEC"])
        t = tr("PREDATORY FIRMWARE")
        w = len(t) * 6 + 20
        para(c, W // 2 - w // 2, 62, w, 12, 6, P["SEC"])
        c.centre(W // 2, 64, t, FP, P["TEXT"])
        segs = 30
        for i in range(segs):
            col = P["PRI"] if i < 21 else P["GRID"]
            para(c, 20 + i * 7, 88, 6, 8, 2, col, left=True, right=False)
        c.text(20, 102, tr("Booting") + b"...", FP, P["DIM"])
        c.right(W - 20, 100, b"70%", FM, P["PRI"])
        return c

    @classmethod
    def main_menu(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c)
        c.text(6, 20, b"01", FG, P["SEC"])
        c.text(6, 46, b"/16", FP, P["DIM"])
        c.text(6, 60, enc("МОДУЛЬ"), FP, P["DIM"])
        bx, by, bw, bh = 82, 22, 76, 60
        cut4(c, bx, by, bw, bh, 9, P["PRI"], fill=P["PANEL"], thick=2)
        c.rect(bx + bw - 14, by + bh - 3, 10, 3, P["SEC"])
        cp.icon_wifi(c, bx + bw // 2, by + bh // 2 + 7, P["PRI"])
        # vertical navigation column: previous module above, next below
        c.right(W - 4, 24, tr("Config")[:11], FP, P["DIM"])
        c.text(W - 18, 34, b"\x1e", FM, P["DIM"])
        c.text(W - 18, 56, b"\x1f", FM, P["PRI"])
        c.right(W - 4, 76, b"BLE", FP, P["TEXT"])
        t = up(tr("WiFi"))
        c.centre(W // 2, 92, t, FM, P["PRI"])
        tw = len(t) * 12
        c.rect(W // 2 - tw // 2, 110, tw, 2, P["SEC"])
        c.rect(W // 2 + tw // 2 + 4, 110, 4, 2, P["PRI"])
        return c

    @classmethod
    def list_screen(cls):
        P = cls.P
        items = ["Connect to Wifi", "WiFi Pass Recovery", "Evil Portal", "Wifi Atks", "Channel Analyzer",
                 "Wardriving", "Back"]
        sel = 1
        c = cls.canvas()
        cls.chrome(c)
        cls.header(c, "WiFi", b"02-07")
        for k in range(5):
            y = 33 + k * 18
            lab = tr(items[k])
            c.text(4, y + 5, b"%02d" % (k + 1), FP, P["SEC"] if k == sel else P["DIM"])
            if k == sel:
                para(c, 18, y, 214, 16, 5, P["PRI"])
                c.text(26, y + 1, lab[:16], FM, P["INK"])
                c.rect(226, y + 4, 4, 8, P["SEC"])
            else:
                c.text(22, y + 1, lab[:17], FM, P["TEXT"])
        for i in range(7):
            c.rect(236, 34 + i * 12, 3, 8, P["PRI"] if i in (1, 2) else P["GRID"])
        return c

    @classmethod
    def toast(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("ЛЮБАЯ КНОПКА - ДАЛЕЕ"))
        bx, by, bw, bh = 10, 40, 220, 50
        cut4(c, bx, by, bw, bh, 7, P["RED"], fill=P["PANEL"], thick=2)
        t = enc("ОШИБКА")
        para(c, bx + 10, by - 6, len(t) * 6 + 18, 12, 5, P["RED"])
        c.text(bx + 18, by - 4, t, FP, P["TEXT"])
        c.centre(W // 2, by + 16, tr("Cannot open file"), FP, P["TEXT"])
        hazard(c, bx + 12, by + bh - 12, 40, 5, P["RED"], P["PANEL"])
        c.right(bx + bw - 12, by + bh - 14, b"E02", FP, P["DIM"])
        return c

    @classmethod
    def dialog(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("\x11\x10 ВЫБОР  M5 ОК"))
        cls.header(c, "Confirm")
        c.centre(W // 2, 42, enc("Сброс настроек?"), FM, P["TEXT"])
        c.centre(W // 2, 62, enc("Все данные удалятся"), FP, P["DIM"])
        para(c, 26, 92, 84, 20, 6, P["GRID"])
        c.centre(68, 95, enc("ДА"), FM, P["TEXT"])
        para(c, 130, 92, 84, 20, 6, P["PRI"])
        c.centre(172, 95, enc("НЕТ"), FM, P["INK"])
        return c

    @classmethod
    def progress(cls):
        P = cls.P
        c = cls.canvas()
        cls.chrome(c, enc("PWR+B ОТМЕНА"))
        cls.header(c, "Running, Wait")
        c.text(6, 40, tr("Uploading..."), FM, P["TEXT"])
        c.rect(6, 66, 228, 16, P["GRID"])
        hazard(c, 6, 66, int(228 * 0.62), 16, P["PRI"], (120, 110, 0), period=10)
        c.frame(4, 64, 232, 20, P["PRI"])
        c.text(6, 92, b"2.1/3.4 MB", FP, P["DIM"])
        c.right(W - 6, 90, b"62%", FG, P["SEC"])
        return c


SCREENS = ["boot", "main_menu", "list_screen", "toast", "dialog", "progress"]


def main():
    out = sys.argv[1]
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    os.makedirs(out, exist_ok=True)
    n = 0
    for tag, cls in (("B", B), ("C", C)):
        for i, name in enumerate(SCREENS, 1):
            cp.write_png(os.path.join(out, "%s%d_%s.png" % (tag, i, name)), getattr(cls, name)(), scale)
            n += 1
    print("wrote", n, "screens to", out)


if __name__ == "__main__":
    main()
