#!/usr/bin/env python3
""""ФОСФОР" UI for Bruce RU on M5StickC Plus2 - pixel-exact previews AND layout spec.

Monochrome green phosphor terminal: square double-line boxes, inverse-video selection,
block cursor, dashed rails, CRT scanlines. Screen 240x135, GLCD 5x8 font + Cyrillic,
text sizes FP=1 (6x8), FM=2 (12x16), FG=3. Colours are RGB565.

Usage: fosfor_preview.py <out_dir> [scale]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cyber_preview as cp  # noqa: E402

W, H, FP, FM, FG = cp.W, cp.H, cp.FP, cp.FM, cp.FG
tr, up, enc, wrap = cp.tr, cp.up, cp.enc_ru, cp.wrap

PALETTE = {
    "BG":    "#000A03",  # screen
    "PANEL": "#00160A",  # filled boxes (toasts, popup)
    "GRID":  "#0A3A1A",  # rails, inner frame lines, leaders
    "DIM":   "#2F8F4E",  # secondary text, hints
    "TEXT":  "#A8FFC0",  # main text
    "PRI":   "#39FF6A",  # phosphor green: accents, selection (bruceConfig.priColor)
    "SEC":   "#C8FF3A",  # lime: numbers, highlights (bruceConfig.secColor)
    "RED":   "#FF5A3C",  # error
    "AMBER": "#FFD23C",  # warning
    "MINT":  "#7DFFDE",  # info
    "INK":   "#000A03",  # text on inverse selection
}
P = {k: cp.c565(v)[0] for k, v in PALETTE.items()}
SCAN = 0.72  # odd rows dimmed to this factor (CRT scanlines)

HINT = enc("\x1e\x1f ВЫБОР  M5 ОК  PWR+B НАЗАД")


# ---------------- primitives ----------------
def canvas():
    return cp.Canvas(P["BG"])


def dashed(c, x, y, w, col, on=2, off=2):
    for xx in range(x, x + w):
        if (xx - x) % (on + off) < on:
            c.put(xx, y, col)


def scanlines(c):
    for y in range(1, H, 2):
        c.px[y] = [(int(r * SCAN), int(g * SCAN), int(b * SCAN)) for (r, g, b) in c.px[y]]


def dbox(c, x, y, w, h, outer, inner=None, fill=None):
    """The house shape: square box, outer line + inner line 2px inside."""
    if fill is not None:
        c.rect(x, y, w, h, fill)
    c.frame(x, y, w, h, outer)
    c.frame(x + 2, y + 2, w - 4, h - 4, inner if inner is not None else outer)


def battery(c, x, y, pct):
    c.frame(x, y, 14, 7, P["PRI"])
    c.rect(x + 14, y + 2, 1, 3, P["PRI"])
    c.rect(x + 2, y + 2, max(1, 10 * pct // 100), 3, P["PRI"] if pct > 15 else P["RED"])


def chrome(c, hint=HINT, tags=b"[SD] [WIFI]"):
    """Status line (y 0-12) + dashed rail y13; hint line y126 + dashed rail y123."""
    c.text(4, 3, b"21:47", FP, P["PRI"])
    c.centre(W // 2, 3, tags, FP, P["DIM"])
    c.right(W - 22, 3, b"87%", FP, P["PRI"])
    battery(c, W - 19, 3, 87)
    dashed(c, 0, 13, W, P["DIM"])
    dashed(c, 0, 123, W, P["GRID"])
    c.centre(W // 2, 126, hint, FP, P["DIM"])


def header(c, title, counter=None):
    """'[ TITLE ]' at y17, counter right, solid separator y27."""
    c.text(4, 17, b"[ " + up(tr(title)) + b" ]", FP, P["PRI"])
    if counter:
        c.right(W - 4, 17, counter, FP, P["DIM"])
    c.hline(4, 27, W - 8, P["GRID"])


# ---------------- screens ----------------
def boot():
    c = canvas()
    lines = [(b"BRUCE OS v1.17-ru", P["TEXT"], None),
             (b"> init display .....", P["DIM"], (b"OK", P["PRI"])),
             (b"> mount littlefs ...", P["DIM"], (b"OK", P["PRI"])),
             (b"> sd card ..........", P["DIM"], (b"--", P["AMBER"])),
             (b"> load bruce.conf ..", P["DIM"], (b"OK", P["PRI"])),
             (b"> lang ru ..........", P["DIM"], (b"OK", P["PRI"]))]
    y = 6
    for txt, col, st in lines:
        end = c.text(6, y, txt, FP, col)
        if st:
            c.text(end + 6, y, st[0], FP, st[1])
        y += 11
    t = tr("PREDATORY FIRMWARE")
    end = c.text(6, 80, t, FM, P["PRI"])
    c.rect(end + 4, 80, 10, 15, P["PRI"])
    c.text(6, 108, b"[" + b"#" * 13 + b"." * 6 + b"] 70%", FP, P["DIM"])
    c.text(12, 108, b"#" * 13, FP, P["PRI"])
    scanlines(c)
    return c


def short(b, n):
    """Cut to n chars on a word boundary ('Проводные инстр.' -> 'Проводные'), else end with '.'."""
    if len(b) <= n:
        return b
    cut = b[:n]
    sp = cut.rfind(b" ")
    return cut[:sp] if sp > 2 else cut[:n - 1] + b"."


def main_menu(name, idx, total, prev, nxt, icon):
    c = canvas()
    chrome(c)
    c.text(4, 17, b"$ ls /bruce", FP, P["DIM"])
    c.right(W - 4, 17, b"%02d/%02d" % (idx, total), FP, P["SEC"])
    bx, by, bw, bh = 82, 30, 76, 54
    dbox(c, bx, by, bw, bh, P["PRI"], P["GRID"])
    icon(c, bx + bw // 2, by + bh // 2 + (7 if icon is cp.icon_wifi else 0), P["PRI"])
    c.text(6, 52, b"<<", FM, P["DIM"])
    c.right(W - 6, 52, b">>", FM, P["DIM"])
    c.text(6, 72, short(tr(prev), 11), FP, P["DIM"])
    c.right(W - 6, 72, short(tr(nxt), 11), FP, P["DIM"])
    t = b"> " + up(tr(name))
    tx = W // 2 - (len(t) + 1) * 12 // 2
    end = c.text(tx, 92, t, FM, P["PRI"])
    c.rect(end + 2, 92, 10, 15, P["PRI"])  # blinking block cursor
    scanlines(c)
    return c


ROW_Y, ROW_H, ROWS = 31, 18, 5


def list_screen(title, items, sel, top=0, disabled=()):
    c = canvas()
    chrome(c)
    header(c, title, b"%02d/%02d" % (sel + 1, len(items)))
    for k in range(ROWS):
        i = top + k
        if i >= len(items):
            break
        y = ROW_Y + k * ROW_H
        lab = tr(items[i])
        if i == sel:
            c.rect(2, y, W - 12, 16, P["PRI"])                # inverse video bar
            c.text(4, y + 1, b">" + lab[:17], FM, P["INK"])   # scrolls if longer
        elif i in disabled:
            c.text(4, y + 1, b" " + lab[:17], FM, P["DIM"])
        elif len(lab) > 17:
            end = c.text(4, y + 1, b" " + lab[:15], FM, P["TEXT"])
            c.text(end + 1, y + 8, b"..", FP, P["DIM"])
        else:
            c.text(4, y + 1, b" " + lab, FM, P["TEXT"])
    # scroll hints: arrows lit only when there is more in that direction
    c.text(W - 8, ROW_Y, b"\x1e", FP, P["PRI"] if top > 0 else P["GRID"])
    c.text(W - 8, ROW_Y + ROWS * ROW_H - 10, b"\x1f", FP, P["PRI"] if top + ROWS < len(items) else P["GRID"])
    scanlines(c)
    return c


TOAST = {  # kind: (colour, banner)
    "error":   ("RED",   "*** ОШИБКА ***"),
    "warning": ("AMBER", "!!! ВНИМАНИЕ !!!"),
    "info":    ("MINT",  "--- ИНФО ---"),
    "success": ("PRI",   "+++ ГОТОВО +++"),
    "line":    ("SEC",   ">>> СООБЩЕНИЕ"),
}


def toast(kind, msg, code=None, under=None):
    c = under if under is not None else canvas()
    if under is None:
        chrome(c, enc("ЛЮБАЯ КНОПКА - ДАЛЕЕ"))
    col = P[TOAST[kind][0]]
    t = tr(msg)
    lines = wrap(t, 32)
    bh = 30 + len(lines) * 10 + (10 if code else 0)
    bx, bw = 12, 216
    by = (16 + 122) // 2 - bh // 2
    dbox(c, bx, by, bw, bh, col, col, fill=P["PANEL"])
    c.centre(W // 2, by + 8, enc(TOAST[kind][1]), FP, col)
    for i, ln in enumerate(lines):
        c.centre(W // 2, by + 22 + i * 10, ln, FP, P["TEXT"])
    if code:
        c.centre(W // 2, by + 22 + len(lines) * 10, code, FP, P["DIM"])
    if under is None:
        scanlines(c)
    return c


def dialog():
    c = canvas()
    chrome(c, enc("\x11\x10 ВЫБОР  M5 ОК"))
    header(c, "Confirm")
    c.text(6, 36, enc("Сброс настроек?"), FM, P["TEXT"])
    c.text(6, 58, enc("> Все данные удалятся."), FP, P["DIM"])
    c.text(6, 68, enc("> Действие необратимо."), FP, P["DIM"])
    c.text(30, 96, enc("[ ДА ]"), FM, P["TEXT"])
    c.rect(124, 94, 88, 20, P["PRI"])
    c.text(130, 96, enc(">НЕТ<"), FM, P["INK"])
    scanlines(c)
    return c


def progress():
    c = canvas()
    chrome(c, enc("PWR+B ОТМЕНА"))
    header(c, "Running, Wait")
    c.text(6, 36, tr("Uploading..."), FM, P["TEXT"])
    c.text(6, 62, b"[" + b"#" * 11 + b"." * 6 + b"]", FM, P["DIM"])
    c.text(18, 62, b"#" * 11, FM, P["PRI"])
    c.text(6, 88, b"2.1/3.4 MB", FP, P["DIM"])
    c.text(6, 99, b"ETA 0:14", FP, P["DIM"])
    c.right(W - 6, 86, b"62%", FM, P["SEC"])
    scanlines(c)
    return c


def info_rows(c, rows, y0=32):
    """'key ....... value' with dotted leaders (FP)."""
    for n, (k, v) in enumerate(rows):
        y = y0 + n * 12
        kx = c.text(6, y, tr(k), FP, P["DIM"])
        vx = W - 6 - len(v) * 6
        x = kx + 3
        while x < vx - 6:
            c.put(x + 2, y + 6, P["GRID"])
            x += 4
        c.text(vx, y, v, FP, P["TEXT"])


def info_screen():
    c = canvas()
    chrome(c, enc("PWR+B НАЗАД"))
    header(c, "Device Info")
    info_rows(c, [("Bruce Version:", b"1.17-ru"), ("Free heap:", b"112 KB"), ("Free PSRAM:", b"1.9 MB"),
                  ("Battery:", b"87% 4.05V"), ("SD Card free:", b"--"), ("MAC addr:", b"00:4B:12:C4:8A:28"),
                  ("Rotation:", b"3")])
    scanlines(c)
    return c


def overlay_menu():
    c = canvas()
    chrome(c, enc("PWR+B НАЗАД"))
    header(c, "Device Info")
    info_rows(c, [("Bruce Version:", b"1.17-ru"), ("Free heap:", b"112 KB"), ("Free PSRAM:", b"1.9 MB"),
                  ("Battery:", b"87% 4.05V"), ("SD Card free:", b"--"), ("MAC addr:", b"00:4B:12:C4:8A:28"),
                  ("Rotation:", b"3")])
    for yy in range(16, 122):  # dim what is underneath
        c.px[yy] = [(r // 4, g // 4, b // 4) for (r, g, b) in c.px[yy]]
    items = ["Save", "Rename", "Delete", "Back"]
    bx, by, bw = 30, 20, 180
    bh = 16 + len(items) * 18 + 4
    dbox(c, bx, by, bw, bh, P["PRI"], P["GRID"], fill=P["PANEL"])
    c.text(bx + 8, by + 5, b"[ " + up(enc("действия")) + b" ]", FP, P["PRI"])
    for i, it in enumerate(items):
        y = by + 16 + i * 18
        if i == 0:
            c.rect(bx + 4, y, bw - 8, 16, P["PRI"])
            c.text(bx + 6, y + 1, b">" + tr(it), FM, P["INK"])
        else:
            c.text(bx + 6, y + 1, b" " + tr(it), FM, P["TEXT"])
    scanlines(c)
    return c


def type_sheet():
    c = canvas()
    chrome(c)
    c.text(6, 18, b"FP", FP, P["SEC"])
    c.text(24, 18, enc("подсказки, статус, логи"), FP, P["TEXT"])
    c.text(6, 34, b"FM", FP, P["SEC"])
    c.text(24, 30, enc("Пункт меню"), FM, P["TEXT"])
    c.text(6, 58, b"FG", FP, P["SEC"])
    c.text(24, 52, enc("ЗАГОЛОВОК"), FG, P["PRI"])
    c.text(6, 84, enc("символы"), FP, P["DIM"])
    c.text(56, 81, b"> < # . \x1e \x1f [ ]", FM, P["PRI"])
    c.text(6, 104, enc("АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"), FP, P["TEXT"])
    c.text(6, 113, enc("абвгдежзийклмнопрстуфхцчшщъыьэюя"), FP, P["TEXT"])
    scanlines(c)
    return c


def palette_sheet():
    c = canvas()
    names = ["BG", "PANEL", "GRID", "DIM", "TEXT", "PRI", "SEC", "RED", "AMBER", "MINT"]
    for i, n in enumerate(names):
        x = 6 + (i % 5) * 46
        y = 8 + (i // 5) * 62
        c.rect(x, y, 40, 36, P[n])
        c.frame(x, y, 40, 36, P["GRID"])
        c.text(x, y + 40, n.encode()[:7], FP, P["TEXT"])
        c.text(x, y + 50, PALETTE[n][1:].encode(), FP, P["DIM"])
    scanlines(c)
    return c


def screens():
    cfg = ["Display & UI", "Audio Config", "System Config", "Power", "About", "Main Menu"]
    wifi = ["Connect to Wifi", "WiFi Pass Recovery", "Evil Portal", "Wifi Atks", "Channel Analyzer",
            "Wardriving", "Back"]
    return {
        "F01_boot": boot(),
        "F02_main_wifi": main_menu("WiFi", 1, 16, "Config", "BLE", cp.icon_wifi),
        "F03_main_config": main_menu("Config", 16, 16, "Wire Tools", "WiFi", cp.icon_gear),
        "F04_list_config": list_screen("Config", cfg, 0),
        "F05_list_wifi": list_screen("WiFi", wifi, 1, top=0, disabled=(3,)),
        "F06_toast_error": toast("error", "Cannot open file", b"ERR 0x02 ENOENT"),
        "F07_toast_success": toast("success", "File saved!", b"/BruceRF/garage.sub"),
        "F08_toast_warning": toast("warning", "Key delay is below 50ms. You may experience issues with missing keys."),
        "F09_toast_info": toast("info", "Connecting...", b"SSID: HomeNet"),
        "F10_dialog": dialog(),
        "F11_progress": progress(),
        "F12_info": info_screen(),
        "F13_overlay_menu": overlay_menu(),
        "F14_type": type_sheet(),
        "F15_palette": palette_sheet(),
    }


def main():
    out = sys.argv[1]
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    os.makedirs(out, exist_ok=True)
    s = screens()
    for name, cv in s.items():
        cp.write_png(os.path.join(out, name + ".png"), cv, scale)
    for k, v in PALETTE.items():
        print("%-6s %s  rgb565=0x%04X" % (k, v, cp.c565(v)[1]))
    print("wrote", len(s), "screens to", out)


if __name__ == "__main__":
    main()
