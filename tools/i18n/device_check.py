#!/usr/bin/env python3
"""On-device check of the Russian UI over USB serial (needs the localized firmware).

Sends `nav` commands and, after each one, `i18n screen`, which prints the last strings
the firmware drew on the display (already translated, converted to UTF-8).

Usage: device_check.py COM5 [step ...]
  steps: next | prev | sel | esc | status | lang-ru | lang-en | screen | wait<seconds>
         tr:<english text>
Example: device_check.py COM5 status screen next screen sel screen esc
"""
import sys
import time

import serial  # pyserial


def talk(port, cmd, seconds=1.5):
    port.reset_input_buffer()
    port.write((cmd + "\n").encode())
    port.flush()
    data = b""
    t0 = time.time()
    while time.time() - t0 < seconds:
        data += port.read(port.in_waiting or 1)
    return data.decode("utf-8", errors="replace")


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    port = serial.Serial()
    port.port = argv[0]
    port.baudrate = 115200
    port.timeout = 0.2
    port.dtr = False  # opening the port must not reset the ESP32
    port.rts = False
    port.open()
    time.sleep(0.3)
    for step in argv[1:] or ["status", "screen"]:
        if step.startswith("wait"):
            time.sleep(float(step[4:] or 1))
            continue
        if step == "status":
            cmd = "i18n"
        elif step == "screen":
            cmd = "i18n screen"
        elif step.startswith("lang-"):
            cmd = "i18n lang " + step[5:]
        elif step.startswith("tr:"):
            cmd = 'i18n tr "%s"' % step[3:]
        else:
            cmd = "nav " + step
        out = talk(port, cmd, 2.0 if cmd.startswith("nav") else 1.5)
        print("==> " + cmd)
        for line in out.splitlines():
            line = line.rstrip()
            if line and not line.startswith(("COMMAND:", "and Released")):
                print("    " + line)
    port.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
