# PlatformIO pre-build hook: regenerate src/core/i18n_ru_data.h from tools/i18n/ru.tsv
import os
import subprocess
import sys

Import("env")  # noqa: F821  (provided by PlatformIO/SCons)

PROJECT_DIR = env.subst("$PROJECT_DIR")  # noqa: F821
script = os.path.join(PROJECT_DIR, "tools", "i18n", "gen_i18n.py")
res = subprocess.run([sys.executable, "-I", script], cwd=PROJECT_DIR)
if res.returncode != 0:
    sys.stderr.write("i18n: dictionary generation failed (see errors above)\n")
    env.Exit(1)  # noqa: F821
