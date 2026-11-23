#!/usr/bin/env python3
"""Extract string literals from Bruce sources together with their call context.

Usage:
  extract.py stats                 -> frequency of the functions literals are passed to
  extract.py dump <out.tsv>        -> every UI-candidate literal: kind, func, file:line, text
  extract.py ui <out.txt>          -> unique UI strings (decoded), one per line, escaped

A literal is a UI candidate when it is passed (directly or through a concatenation /
ternary) to one of the known display functions, or used as a menu Option label.
"""
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC_DIRS = [os.path.join(ROOT, "src"), os.path.join(ROOT, "boards", "m5stack-cplus2")]

# Functions whose string arguments end up on the screen
UI_FUNCS = {
    # tft object methods
    "print", "println", "printf", "drawString", "drawCentreString", "drawRightString",
    # display.h helpers
    "displayError", "displayWarning", "displayInfo", "displaySuccess", "displayTextLine",
    "displayRedStripe", "displayMessage", "padprint", "padprintln", "padprintf",
    "printTitle", "printSubtitle", "printFootnote", "printCenterFootnote",
    "drawMainBorderWithTitle", "progressHandler", "drawSubmenu", "loopOptions",
    "displayScrollingText", "drawButton", "drawOptions",
    # keyboard / misc prompts
    "keyboard", "num_keyboard", "hex_keyboard", "generalKeyboard", "pwdKeyboard",
    "drawPopup", "showMessage", "displayStatus", "addOptionToMainMenu", "MenuItemInterface",
    "loopSD", "Option", "push_back", "emplace_back", "options_push",
}
# Never UI (serial/log/fs/json/net)
NON_UI_OBJECTS = ("Serial", "USBSerial", "log_", "file", "File", "f.", "client", "server",
                  "request", "response", "doc", "json", "JSON", "http", "udp", "ble", "wifi",
                  "out", "dbg", "Debug", "webSocket", "ws", "fp", "logFile", "outFile",
                  "streamFile", "serialDevice", "Keyboard", "hid", "Mouse")

LIT_RE = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def strip_comments(code):
    """Replace comments with spaces (keeping line numbers), leave strings intact."""
    out = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c == '"' or c == "'":
            q = c
            j = i + 1
            while j < n and code[j] != q:
                if code[j] == "\\":
                    j += 1
                if code[j] == "\n" and q == "'":
                    break
                j += 1
            out.append(code[i:j + 1])
            i = j + 1
            continue
        if code.startswith("//", i):
            j = code.find("\n", i)
            if j < 0:
                j = n
            out.append(" " * (j - i))
            i = j
            continue
        if code.startswith("/*", i):
            j = code.find("*/", i + 2)
            if j < 0:
                j = n
            seg = code[i:j + 2]
            out.append(re.sub(r"[^\n]", " ", seg))
            i = j + 2
            continue
        if code.startswith('R"', i) and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == "_")):
            # raw string: R"delim( ... )delim" -> blank it out, never UI in this code base
            m = re.match(r'R"([^(\s]*)\(', code[i:])
            if m:
                end = code.find(")" + m.group(1) + '"', i)
                if end > 0:
                    seg = code[i:end + len(m.group(1)) + 2]
                    out.append(re.sub(r"[^\n]", " ", seg))
                    i = end + len(m.group(1)) + 2
                    continue
        out.append(c)
        i += 1
    return "".join(out)


def decode_c(s):
    """Decode C escape sequences of a literal body into a Python str (bytes as latin-1)."""
    res = []
    i = 0
    while i < len(s):
        c = s[i]
        if c != "\\":
            res.append(c)
            i += 1
            continue
        i += 1
        e = s[i]
        simple = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'",
                  "a": "\a", "b": "\b", "f": "\f", "v": "\v", "?": "?"}
        if e == "x":
            m = re.match(r"[0-9A-Fa-f]{1,2}", s[i + 1:])
            res.append(chr(int(m.group(0), 16)))
            i += 1 + len(m.group(0))
            continue
        if e in "01234567" and re.match(r"[0-7]{1,3}", s[i:]):
            m = re.match(r"[0-7]{1,3}", s[i:])
            res.append(chr(int(m.group(0), 8)))
            i += len(m.group(0))
            continue
        res.append(simple.get(e, e))
        i += 1
    return "".join(res)


def escape(s):
    return (s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
            .replace("\r", "\\r"))


WRAPPERS = {"String", "F", "PSTR", "c_str", "", "const_char", "toUpperCase", "substring", "concat",
             "std::string", "string", "FPSTR"}


def enclosing_call(code, pos):
    """Innermost call/brace enclosing pos, skipping transparent wrappers such as String(...)."""
    res = _enclosing_call(code, pos)
    guard = 0
    while res[0] == "call" and res[1] in WRAPPERS and guard < 6:
        res = _enclosing_call(code, res[3])
        guard += 1
    return res


def _enclosing_call(code, pos):
    """Return (func_name, receiver, depth_info) of the innermost '(' or '{' enclosing pos."""
    depth_paren = 0
    depth_brace = 0
    i = pos - 1
    while i >= 0:
        c = code[i]
        if c == '"':
            # skip over a string literal backwards
            j = i - 1
            while j >= 0:
                if code[j] == '"' and code[j - 1] != "\\":
                    break
                j -= 1
            i = j - 1
            continue
        if c == ")":
            depth_paren += 1
        elif c == "(":
            if depth_paren == 0:
                m = re.search(r"([A-Za-z_][\w]*)\s*(<[^<>()]*>)?\s*$", code[max(0, i - 120):i])
                name = m.group(1) if m else ""
                rm = re.search(r"([A-Za-z_][\w\.\->\[\]]*?)\s*(\.|->)\s*" + re.escape(name) + r"\s*(<[^<>()]*>)?\s*$",
                               code[max(0, i - 160):i]) if name else None
                recv = rm.group(1) if rm else ""
                return ("call", name, recv, i)
            depth_paren -= 1
        elif c == "}":
            depth_brace += 1
        elif c == "{":
            if depth_brace == 0 and depth_paren == 0:
                before = code[max(0, i - 200):i]
                return ("brace", before.rstrip()[-60:], "", i)
            if depth_brace > 0:
                depth_brace -= 1
        elif c == ";" and depth_paren == 0 and depth_brace == 0:
            return ("stmt", "", "", i)
        i -= 1
    return ("none", "", "", 0)


def iter_sources():
    for base in SRC_DIRS:
        for dp, _, files in os.walk(base):
            for fn in files:
                if fn.endswith((".cpp", ".h", ".c", ".hpp", ".ino")):
                    yield os.path.join(dp, fn)


def classify(code, m):
    """Return (kind, func, recv) for literal match m."""
    start = m.start()
    # literal used as Option label: `{"Label", ...` or `Option("Label"`
    kind, name, recv, _ = enclosing_call(code, start)
    return kind, name, recv


def literals():
    for path in iter_sources():
        raw = open(path, encoding="utf-8", errors="replace").read()
        code = strip_comments(raw)
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        for m in LIT_RE.finditer(code):
            # skip #include "..." and other preprocessor lines
            line_start = code.rfind("\n", 0, m.start()) + 1
            line_txt = code[line_start:code.find("\n", m.start())]
            if line_txt.lstrip().startswith(("#include", "#pragma", "#error", "#warning")):
                continue
            # skip char-adjacent junk like '"' handled by regex already
            body = m.group(1)
            line = code.count("\n", 0, m.start()) + 1
            kind, name, recv = classify(code, m)
            prev = code[max(0, m.start() - 3):m.start()].strip()
            nxt = code[m.end():m.end() + 3].strip()
            yield {
                "file": rel, "line": line, "raw": body, "text": decode_c(body),
                "kind": kind, "func": name, "recv": recv,
                "concat_before": prev.endswith("+"), "concat_after": nxt.startswith("+"),
                "line_txt": line_txt.strip(),
            }


MODULE_UI_FUNCS = {
    "addLine", "showAttackProgress", "showAttackResult", "confirmAttack", "rf_info_line", "jammer_status",
    "printStatusBadUSBBLE", "showDeviceInfoScreen", "setMood", "choose", "showSubMenu", "view", "status",
    "printTextAtPosition", "fromString", "ScrollableTextArea", "drawPopup", "showMessage", "addOptionSetMode",
    "displayStatus", "printCenter", "printLine", "drawTitle", "drawHeader", "drawFooter", "drawLabel",
    "drawStatus", "showStatus", "showError", "showInfo", "showResult", "showProgress", "message", "msg",
    "displayScreen", "header", "footer", "title", "drawCentered", "printAt", "printXY", "addItem",
}
NON_UI_FUNCS = {
    "if", "while", "for", "switch", "strcmp", "strncmp", "strcasecmp", "startsWith", "endsWith", "indexOf",
    "lastIndexOf", "replace", "exists", "open", "mkdir", "remove", "rmdir", "rename", "find", "strstr",
    "equals", "equalsIgnoreCase", "compareTo", "getArgument", "arg", "hasArg", "hasParam", "getParam",
    "addCommand", "addPosArg", "addFlagArg", "addArg", "addCompositeCmd", "addHeader", "send", "sendHeader",
    "on", "serveWebUIFile", "streamFile", "xTaskCreate", "xTaskCreatePinnedToCore", "fromJson", "parse",
    "sscanf", "strtoul", "strtol", "atoi", "cborAppendText", "begin", "write", "createNewFile", "_Static_assert",
    "JS_SetPropertyStr", "JS_GetPropertyStr", "JS_NewString", "JS_ThrowTypeError", "JS_ThrowInternalError",
    "JS_ThrowRangeError", "JS_ThrowSyntaxError", "JS_ThrowReferenceError", "JS_CFUNC_DEF", "JS_CFUNC_MAGIC_DEF",
    "JS_PROP_CLASS_DEF", "JS_OBJECT_DEF", "JS_PROP_DOUBLE_DEF", "JS_CFUNC_SPECIAL_DEF", "JS_CLASS_DEF",
    "JS_PROP_INT32_DEF", "JS_PROP_STRING_DEF", "JS_NewAtom", "JS_Eval", "JS_DefinePropertyValueStr",
    "rf_record_write_uint32", "rf_record_read_uint32", "rf_record_read_hex", "rf_record_write_hex",
    "rf_stream_definition", "initRfModule", "markSessionClosed", "logYmodem", "getString", "putString",
    "getInt", "putInt", "getBool", "putBool", "getUInt", "putUInt", "getFloat", "putFloat", "containsKey",
    "setHostname", "MDNS", "addService", "softAP", "connect", "readStringUntil", "httpGET", "POST", "GET",
    "setUserAgent", "addParameter", "printToSerial", "settimeofday", "strptime", "strftime", "fopen",
    "setenv", "tzset", "esp_vfs_spiffs_register", "preferences", "isKey", "match", "key", "get", "set",
    "getValue", "readFile", "writeFile", "appendFile", "deleteFile", "hasPrefix", "startswith",
}
LOGGISH = re.compile(r"(^log_|_LOG|LOG_|_DBG|^DBG|DEBUG|^ESP_LOG|Serial|^dbg)", re.I)


def looks_human(t):
    """Heuristic: does this text look like natural-language UI text?"""
    s = t.strip()
    if len(re.findall(r"[A-Za-z]", s)) < 2:
        return False
    if s.startswith(("/", "http", "AT+", "<", "{", "[", "%", "0x", "#!", "$")) and " " not in s[:12]:
        return False
    if "://" in s or s.endswith((".txt", ".json", ".conf", ".js", ".html", ".css", ".ir", ".sub", ".bin",
                                 ".png", ".jpg", ".bmp", ".gif", ".csv", ".pcap", ".log", ".nfc", ".rfid")):
        return False
    if re.search(r"[<>{};=]{2,}|</|/>|\\\\", s):
        return False
    # identifiers: lower_snake / camelCase / dotted.keys without spaces
    if " " not in s:
        if re.fullmatch(r"[a-z][a-z0-9_\.\-]*", s):
            return False
        if re.fullmatch(r"[a-z]+[A-Z][A-Za-z0-9_]*", s):
            return False
        if re.fullmatch(r"[A-Z0-9_]{1,}_[A-Z0-9_]+", s):
            return False
        if re.fullmatch(r"[0-9A-Fa-f:\-\.]+", s):
            return False
    return True


def category(rec):
    """'ui' = certainly shown on screen, 'maybe' = human-looking text in another context, 'no'."""
    kind, func, recv = rec["kind"], rec["func"], rec["recv"]
    lt = rec["line_txt"].lstrip()
    t = rec["text"]
    if LOGGISH.search(lt.split("(")[0]) or lt.startswith(("Serial", "USBSerial", "log_", "ESP_LOG")):
        return "no"
    if kind == "call":
        if LOGGISH.search(func) or func in NON_UI_FUNCS or func.startswith(("JS_", "rf_record", "RF_")):
            return "no"
        if func in ("print", "println", "printf", "drawString", "drawCentreString", "drawRightString"):
            r = recv.lower()
            if r.endswith("tft") or "sprite" in r or "canvas" in r or r in ("display", "spr", "s", "d", "gfx"):
                return "ui"
            if "serial" in r or r in ("file", "f", "client", "out", "fp", "stream", "dbg"):
                return "no"
            return "maybe" if looks_human(t) else "no"
        if func in UI_FUNCS or func in MODULE_UI_FUNCS:
            return "ui" if re.search(r"[A-Za-z]{2}", t) else "no"
        return "maybe" if looks_human(t) else "no"
    if kind == "brace":
        return "maybe" if looks_human(t) else "no"
    if kind in ("stmt", "none"):
        return "maybe" if looks_human(t) else "no"
    return "no"


def is_ui(rec):
    return category(rec) == "ui"


def main(argv):
    cmd = argv[0] if argv else "stats"
    recs = list(literals())
    if cmd == "stats":
        cnt = Counter()
        for r in recs:
            cnt[(r["kind"], r["func"] if r["kind"] == "call" else "")] += 1
        print("total literals:", len(recs))
        for (k, f), n in cnt.most_common(120):
            print("%6d  %-6s %s" % (n, k, f))
    elif cmd == "dump":
        with open(argv[1], "w", encoding="utf-8") as out:
            for r in recs:
                ui = is_ui(r)
                out.write("%s\t%s\t%s\t%s:%d\t%s\t%s\n" % (
                    "UI" if ui else "--", r["kind"], r["func"] if r["kind"] == "call" else r["func"][-30:].replace("\t", " "),
                    r["file"], r["line"],
                    ("+" if r["concat_before"] else "") + "|" + ("+" if r["concat_after"] else ""),
                    escape(r["text"])))
        print("wrote", argv[1])
    elif cmd == "ui":
        # unique strings with their best category ('ui' wins over 'maybe')
        best = {}
        where = defaultdict(list)
        flags = defaultdict(set)
        for r in recs:
            c = category(r)
            if c == "no":
                continue
            t = r["text"]
            if best.get(t) != "ui":
                best[t] = c
            where[t].append("%s:%d" % (r["file"], r["line"]))
            if r["concat_after"]:
                flags[t].add("^")
            if r["concat_before"]:
                flags[t].add("$")
        with open(argv[1], "w", encoding="utf-8") as out:
            for t in sorted(best, key=lambda x: (best[x] != "ui", x.lower())):
                out.write("%s\t%s\t%s\t%s\n" % (best[t], "".join(sorted(flags[t])) or "-", escape(t),
                                                 ",".join(where[t][:3])))
        n_ui = sum(1 for v in best.values() if v == "ui")
        print("unique strings: ui=%d maybe=%d" % (n_ui, len(best) - n_ui))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
