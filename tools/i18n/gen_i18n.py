#!/usr/bin/env python3
"""Compile tools/i18n/ru.tsv into src/core/i18n_ru_data.h.

ru.tsv format (UTF-8), one entry per line, fields separated by a TAB:
    <type> <TAB> <english> <TAB> <russian>
  type:  =  exact string   (also used for printf format strings)
         ^  prefix         ("Connecting to " + ssid)
         $  suffix         (n + " networks")
  Escapes inside fields: \\n \\t \\\\
  Lines starting with '#' and empty lines are ignored.
  Russian text may use Ё/ё (folded to Е/е), «» (-> "), – — (-> -), … (-> ...).

Checks performed (any error aborts the build):
  * every Russian character is encodable in the firmware's single-byte encoding
  * printf conversion specifiers are identical (same order) in key and translation
  * no empty translations
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TSV = os.path.join(HERE, "ru.tsv")
OUT = os.path.join(ROOT, "src", "core", "i18n_ru_data.h")

UPPER = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
LOWER = "абвгдежзийклмнопрстуфхцчшщъыьэюя"
REPL = {"Ё": "Е", "ё": "е", "«": '"', "»": '"', "–": "-", "—": "-", "…": "...", "№": "N",
        " ": " ", "’": "'", "‘": "'", "“": '"', "”": '"', "×": "x", "°": "*"}
FMT_RE = re.compile(r"%(?:[-+ #0]*\d*(?:\.\d+)?(?:hh|h|ll|l|z|j|t|L)?[diouxXeEfgGcsp]|%)")


def unescape(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", "\\": "\\"}.get(n, "\\" + n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def encode_ru(text, where):
    """UTF-8 Russian text -> firmware bytes."""
    res = bytearray()
    for ch in text:
        ch = REPL.get(ch, ch)
        for c in ch:
            o = ord(c)
            if c in UPPER:
                res.append(0x80 + UPPER.index(c))
            elif c in LOWER:
                res.append(0xA0 + LOWER.index(c))
            elif o < 0x80:
                res.append(o)
            else:
                raise ValueError("%s: unsupported character %r (U+%04X)" % (where, c, o))
    return bytes(res)


def encode_key(text, where):
    # keys are the English literals exactly as the C++ sources contain them (UTF-8)
    return text.encode("utf-8")


def c_literal(b):
    out = ['"']
    for byte in b:
        ch = chr(byte)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "?":
            out.append("\\?")  # avoid trigraphs
        elif 32 <= byte < 127:
            out.append(ch)
        else:
            out.append("\\%03o" % byte)
    out.append('"')
    return "".join(out)


def lower_bytes(b):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in b)


def load(path=TSV):
    tables = {"=": {}, "^": {}, "$": {}}
    auto_exact = {}
    errors = []
    dup = 0
    for no, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n").rstrip("\r")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        where = "%s:%d" % (os.path.basename(path), no)
        if len(parts) != 3 or parts[0] not in tables:
            errors.append("%s: expected '<type>\\t<english>\\t<russian>'" % where)
            continue
        typ, en, ru = parts[0], unescape(parts[1]), unescape(parts[2])
        if typ == "=":
            # tr() looks up the text without its surrounding blanks and puts them back itself
            en, ru = en.strip(" \t\r\n"), ru.strip(" \t\r\n")
        else:
            # prefix/suffix: the value gets exactly the key's surrounding blanks
            # (editors tend to drop trailing spaces at the end of a line)
            core = en.strip(" \t\r\n")
            lead = en[: len(en) - len(en.lstrip(" \t\r\n"))]
            trail = en[len(en.rstrip(" \t\r\n")):] if core else ""
            ru = lead + ru.strip(" \t\r\n") + trail
        if not en or not ru.strip():
            errors.append("%s: empty key or translation" % where)
            continue
        try:
            kb = encode_key(en, where)
            vb = encode_ru(ru, where)
        except ValueError as e:
            errors.append(str(e))
            continue
        if FMT_RE.findall(en) != FMT_RE.findall(ru):
            errors.append("%s: printf specifiers differ: %r vs %r" % (where, FMT_RE.findall(en), FMT_RE.findall(ru)))
            continue
        if kb in tables[typ]:
            dup += 1
        tables[typ][kb] = vb
        if typ in "^$":
            # the same fragment is often printed on its own: add a trimmed exact entry too
            ke, ve = kb.strip(b" \t\r\n"), vb.strip(b" \t\r\n")
            if ke and ve and ke not in tables["="]:
                auto_exact[ke] = ve
    for k, v in auto_exact.items():
        tables["="].setdefault(k, v)
    return tables, errors, dup


def emit_table(lines, name, items):
    if not items:
        lines.append("static const int %s_COUNT = 0;" % name)
        lines.append('static const char *const %s_KEYS[1] = {""};' % name)
        lines.append('static const char *const %s_VALS[1] = {""};' % name)
        return
    lines.append("static const int %s_COUNT = %d;" % (name, len(items)))
    lines.append("static const char *const %s_KEYS[] = {" % name)
    lines.extend("    %s," % c_literal(k) for k, _ in items)
    lines.append("};")
    lines.append("static const char *const %s_VALS[] = {" % name)
    lines.extend("    %s," % c_literal(v) for _, v in items)
    lines.append("};")


def dictionary_files():
    files = [TSV]
    extra = os.path.join(HERE, "ru.d")
    if os.path.isdir(extra):
        files += [os.path.join(extra, f) for f in sorted(os.listdir(extra)) if f.endswith(".tsv")]
    return files


def load_all():
    merged = {"=": {}, "^": {}, "$": {}}
    errors, dup = [], 0
    for path in dictionary_files():
        t, e, d = load(path)
        errors += e
        dup += d
        for typ in merged:
            for k, v in t[typ].items():
                if k in merged[typ] and merged[typ][k] != v:
                    dup += 1
                merged[typ][k] = v
    return merged, errors, dup


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tables, errors, dup = load_all()
    if errors:
        for e in errors:
            print("ERROR", e)
        print("%d error(s)" % len(errors))
        return 1
    exact = sorted(tables["="].items())
    prefix = sorted(tables["^"].items())
    suffix = sorted(tables["$"].items())
    ci = sorted(range(len(exact)), key=lambda i: (lower_bytes(exact[i][0]), exact[i][0]))
    if len(exact) > 65535:
        print("too many entries")
        return 1

    lines = [
        "// Generated by tools/i18n/gen_i18n.py from tools/i18n/ru.tsv - DO NOT EDIT.",
        "// Russian text uses the firmware single-byte encoding (0x80..0x9F = upper, 0xA0..0xBF = lower case).",
        "#pragma once",
        "#include <stdint.h>",
        "",
    ]
    emit_table(lines, "RU_EXACT", exact)
    if exact:
        lines.append("static const uint16_t RU_CI_INDEX[] = {")
        for k in range(0, len(ci), 16):
            lines.append("    " + ", ".join(str(x) for x in ci[k:k + 16]) + ",")
        lines.append("};")
    else:
        lines.append("static const uint16_t RU_CI_INDEX[1] = {0};")
    emit_table(lines, "RU_PREFIX", prefix)
    emit_table(lines, "RU_SUFFIX", suffix)
    data = "\n".join(lines) + "\n"
    old = open(OUT, encoding="latin-1").read() if os.path.exists(OUT) else None
    if old != data:
        with open(OUT, "w", encoding="latin-1", newline="\n") as f:
            f.write(data)
    print("i18n: %d exact, %d prefix, %d suffix entries (%d duplicates overridden) -> %s"
          % (len(exact), len(prefix), len(suffix), dup, os.path.relpath(OUT, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
