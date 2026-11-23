#!/usr/bin/env python3
"""Drive Bruce over USB serial and print the text it draws on its screen.

`display start` makes the firmware stream every draw call as a binary packet
(0xAA, size, fn, x16, y16, size16, fg16, bg16, text...) over the serial port.
We send `nav <next|prev|sel|esc>` and decode the text packets that follow, using the
Russian single-byte mapping, so the output is what the user sees on the display.
(`display dump` / `display stop` are not used: both crash upstream Bruce 1.17.)

Usage: device_screen.py COM5 [step ...]
  steps: next | prev | sel | esc | wait<seconds> | listen<seconds>
Example: device_screen.py COM5 listen2 next sel wait2 esc
"""
import sys
import time

import serial  # pyserial (installed with esptool / platformio)

TEXT_FUNCS = {14: "centre", 15: "right", 16: "string", 17: "print"}
KNOWN_FUNCS = set(range(0, 22)) | {99}


def decode(b):
    out = []
    for c in b:
        if 0x80 <= c <= 0x9F:
            out.append(chr(0x410 + c - 0x80))
        elif 0xA0 <= c <= 0xBF:
            out.append(chr(0x430 + c - 0xA0))
        elif 32 <= c < 0x80 or c in (10, 13):
            out.append(chr(c))
        else:
            out.append("\\x%02X" % c)
    return "".join(out)


def parse(data):
    items = []
    i = 0
    while i + 3 <= len(data):
        if data[i] != 0xAA:
            i += 1
            continue
        size, fn = data[i + 1], data[i + 2]
        if fn not in KNOWN_FUNCS or size < 3 or i + size > len(data):
            i += 1
            continue
        entry = data[i:i + size]
        if fn in TEXT_FUNCS and size > 13:
            x = (entry[3] << 8) | entry[4]
            y = (entry[5] << 8) | entry[6]
            items.append((x, y, TEXT_FUNCS[fn], decode(entry[13:])))
        i += size
    return items


def collect(port, seconds):
    data = b""
    t0 = time.time()
    while time.time() - t0 < seconds:
        data += port.read(port.in_waiting or 1)
    return data


def show(title, items):
    print("---- %s ----" % title)
    seen = set()
    for x, y, kind, text in items:
        key = (x, y, text)
        if not text.strip() or key in seen:
            continue
        seen.add(key)
        print("y=%3d x=%3d %-6s %s" % (y, x, kind, text.rstrip("\r\n")))


def main(argv):
    port = serial.Serial()
    port.port = argv[0]
    port.baudrate = 115200
    port.timeout = 0.2
    port.dtr = False  # do not reset the ESP32 when opening the port
    port.rts = False
    port.open()
    time.sleep(0.3)
    port.reset_input_buffer()
    port.write(b"display start\n")
    port.flush()
    collect(port, 1.0)
    for step in argv[1:] or ["listen2"]:
        if step.startswith("wait"):
            time.sleep(float(step[4:] or 1))
            continue
        if step.startswith("listen"):
            show("listen", parse(collect(port, float(step[6:] or 2))))
            continue
        port.reset_input_buffer()
        port.write(("nav " + step + "\n").encode())
        port.flush()
        show("after nav " + step, parse(collect(port, 2.5)))
    port.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
