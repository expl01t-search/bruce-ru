#!/usr/bin/env python3
"""Report translations that no longer fit where the English text did.

Menu rows use text size FM (12 px per char) on a 240 px wide screen: ~19 chars fit in a
submenu row / ~17 in a list row before scrolling or clipping kicks in.
Usage: check_lengths.py [limit]   (default limit 19)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_i18n  # noqa: E402


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    tables, errors, _ = gen_i18n.load_all()
    if errors:
        print("\n".join(errors))
        return 1
    rows = []
    for k, v in tables["="].items():
        if b"\n" in k:
            continue
        en, ru = len(k), len(v)
        if en <= limit < ru:
            rows.append((ru - en, k.decode("utf-8"), v))
    rows.sort(reverse=True)
    inv = {}
    for i, ch in enumerate(gen_i18n.UPPER):
        inv[0x80 + i] = ch
    for i, ch in enumerate(gen_i18n.LOWER):
        inv[0xA0 + i] = ch
    for d, en, v in rows:
        ru = "".join(inv.get(b, chr(b)) for b in v)
        print("%3d  %-24s -> %s (%d)" % (d, en, ru, len(v)))
    print("%d entries longer than %d chars while English fits" % (len(rows), limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
