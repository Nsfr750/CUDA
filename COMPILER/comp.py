"""Compilazione di CUDA Core Monitor con Nuitka.

Produce una build standalone (cartella) oppure un eseguibile singolo.

Uso:
    python COMPILER/comp.py         # dist/CUDA-Monitor.exe (onefile)
    python COMPILER/comp.py --dir   # build standalone in dist/main.dist/

Richiede:  pip install nuitka
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import APP_NAME, __version__  # noqa: E402

COMPANY = "Tuxxle"
AUTHOR = "Nsfr750"
COPYRIGHT = "© Copyright 2024-2026 Nsfr750 - All rights reserved."
DESCRIPTION = "Monitor GUI per GPU NVIDIA/AMD/Intel"

EXE_NAME = "CUDA-Monitor.exe"
ONEFILE = "--dir" not in sys.argv  # default: eseguibile singolo in dist/

args = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--enable-plugin=pyside6",          # Qt DLL e plugin PySide6
    "--windows-console-mode=disable",   # app GUI senza console
    "--assume-yes-for-downloads",       # toolchain (MinGW) automatico
    "--remove-output",                  # pulisce build precedenti
    "--nofollow-import-to=torch",       # fallback opzionale: escluso
    "--include-data-files=assets/icon.png=assets/icon.png",
    f"--windows-icon-from-ico={ROOT / 'assets' / 'icon.ico'}",
    f"--output-dir={ROOT / 'dist'}",
    f"--output-filename={EXE_NAME}",
    f"--company-name={COMPANY}",
    f"--product-name={APP_NAME}",
    f"--product-version={__version__}",
    f"--file-version={__version__}",
    f"--file-description={DESCRIPTION}",
    f"--copyright={COPYRIGHT}",
]
if ONEFILE:
    args.append("--onefile")
args.append(str(ROOT / "main.py"))      # entry point: ultimo argomento

print("Compilazione di", APP_NAME, "v" + __version__)
print(" ".join(args), "\n")
raise SystemExit(subprocess.run(args, cwd=ROOT).returncode)
