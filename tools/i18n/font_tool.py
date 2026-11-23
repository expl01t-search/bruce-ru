#!/usr/bin/env python3
"""GLCD 5x8 font helper for the Russian localisation of Bruce.

Commands:
  dump <chars>        print glyphs of the given characters (from the current font) as ASCII art
  dumpcodes <a> <b>   print glyphs for byte codes a..b (decimal or 0x..)
  patch               write Cyrillic glyphs from cyrillic_glyphs.txt into lib/TFT_eSPI/Fonts/glcdfont.c
  preview <text>      render a UTF-8 string with the patched font as ASCII art

Encoding used by the firmware (single byte, so String::length() == number of glyphs):
  U+0410..U+042F (А..Я) -> 0x80..0x9F
  U+0430..U+044F (а..я) -> 0xA0..0xBF
  Ё/ё are folded to Е/е.

TFT_eSPI quirk: with _cp437 == false, drawChar() reads glyph (c + 1) for every code c > 175,
so codes 0xB0..0xBF live at glyph indices 0xB1..0xC0.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FONT_C = os.path.join(ROOT, "lib", "TFT_eSPI", "Fonts", "glcdfont.c")
GLYPHS_TXT = os.path.join(HERE, "cyrillic_glyphs.txt")

UPPER = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOWER = "абвгдежзийклмнопрстуфхцчшщъыьэюя"


def code_for(ch):
    """Firmware byte code for a character (ASCII passes through)."""
    o = ord(ch)
    if ch in ("Ё",):
        return 0x80 + UPPER.index("Е")
    if ch in ("ё",):
        return 0xA0 + LOWER.index("е")
    if 0x410 <= o <= 0x42F:
        return 0x80 + (o - 0x410)
    if 0x430 <= o <= 0x44F:
        return 0xA0 + (o - 0x430)
    if o < 0x80:
        return o
    raise ValueError("unsupported character %r (U+%04X)" % (ch, o))


def glyph_index(code):
    """Index into font[] actually read by TFT_eSPI::drawChar for byte code `code`."""
    return code + 1 if code > 175 else code


def read_font():
    src = open(FONT_C, encoding="utf-8").read()
    body = src[src.index("{") + 1: src.rindex("}")]
    vals = [int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", body)]
    assert len(vals) == 256 * 5, len(vals)
    return [vals[i * 5:(i + 1) * 5] for i in range(256)]


def write_font(glyphs):
    src = open(FONT_C, encoding="utf-8").read()
    head = src[: src.index("{") + 1]
    tail = src[src.rindex("}"):]
    lines = []
    for i, g in enumerate(glyphs):
        sep = "," if i < 255 else ""
        lines.append("\t" + ", ".join("0x%02X" % b for b in g) + sep)
    with open(FONT_C, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + "\n" + "\n".join(lines) + "\n" + tail)


def glyph_rows(cols):
    rows = []
    for r in range(8):
        rows.append("".join("#" if (c >> r) & 1 else "." for c in cols))
    return rows


def rows_to_cols(rows):
    assert len(rows) == 8, rows
    cols = [0] * 5
    for r, line in enumerate(rows):
        assert len(line) == 5, (r, line)
        for c, ch in enumerate(line):
            if ch == "#":
                cols[c] |= 1 << r
    return cols


def render(text, glyphs):
    out = [""] * 8
    for ch in text:
        cols = glyphs[glyph_index(code_for(ch))]
        rows = glyph_rows(cols)
        for r in range(8):
            out[r] += rows[r] + "."
    return "\n".join(out)


def parse_glyph_file(latin_glyphs):
    """cyrillic_glyphs.txt: blocks of `= <letter>` followed by 8 rows of 5 chars (# or .).
    `= <letter> @<latin>` copies the glyph of an ASCII character from the original font."""
    result = {}
    cur = None
    rows = []

    def flush():
        if cur is not None and rows:
            result[cur] = rows_to_cols(rows)

    for raw in open(GLYPHS_TXT, encoding="utf-8"):
        line = raw.rstrip("\n").rstrip("\r")
        if not line.strip() or line.startswith(";"):
            continue
        if line.startswith("="):
            flush()
            spec = line[1:].split()
            cur = spec[0]
            rows = []
            if len(spec) > 1 and spec[1].startswith("@"):
                result[cur] = list(latin_glyphs[ord(spec[1][1])])
                cur = None
            continue
        rows.append(line.strip())
    flush()
    return result


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    glyphs = read_font()
    if cmd == "dump":
        for ch in argv[1]:
            print("=", ch)
            print("\n".join(glyph_rows(glyphs[glyph_index(code_for(ch))])))
    elif cmd == "dumpcodes":
        a, b = int(argv[1], 0), int(argv[2], 0)
        for code in range(a, b + 1):
            print("= code 0x%02X (glyph %d)" % (code, glyph_index(code)))
            print("\n".join(glyph_rows(glyphs[glyph_index(code)])))
    elif cmd == "patch":
        defs = parse_glyph_file(glyphs)
        missing = [ch for ch in UPPER + LOWER if ch not in defs]
        if missing:
            print("missing glyph definitions:", "".join(missing))
            return 2
        for ch in UPPER + LOWER:
            glyphs[glyph_index(code_for(ch))] = defs[ch]
        write_font(glyphs)
        print("patched %d glyphs into %s" % (len(UPPER + LOWER), FONT_C))
    elif cmd == "preview":
        print(render(argv[1], glyphs))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
