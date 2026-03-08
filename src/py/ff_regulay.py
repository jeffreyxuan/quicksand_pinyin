#!/usr/bin/env python3
"""Generate Quicksand-Regular_pinyin.ttf from the SFD source using FontForge."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_SFD = REPO_ROOT / "src" / "ff" / "Quicksand-Regular_pinyin.sfd"
OUTPUT_TTF = REPO_ROOT / "_output" / "Quicksand-Regular_pinyin.ttf"
FONTFORGE_BIN = Path(r"C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe")

FF_SCRIPT = r'''
import sys
import fontforge

if len(sys.argv) < 3:
    raise SystemExit("Usage: ff_script.py <input_sfd> <output_ttf>")

input_sfd = sys.argv[1]
output_ttf = sys.argv[2]

font = fontforge.open(input_sfd)
font.generate(output_ttf)
font.close()
print(f"Done: {output_ttf}")
'''


def main() -> int:
    if not INPUT_SFD.exists():
        print(f"Input file not found: {INPUT_SFD}", file=sys.stderr)
        return 2

    OUTPUT_TTF.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
        tmp.write(FF_SCRIPT)
        ff_script_path = Path(tmp.name)

    try:
        cmd = [
            str(FONTFORGE_BIN),
            "-lang=py",
            "-script",
            str(ff_script_path),
            str(INPUT_SFD),
            str(OUTPUT_TTF),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        ff_script_path.unlink(missing_ok=True)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0:
        return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
