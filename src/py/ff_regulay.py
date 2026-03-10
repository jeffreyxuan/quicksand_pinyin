#!/usr/bin/env python3
"""Generate a TTF from an SFD source using FontForge."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


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


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Raises:
        SystemExit: If required arguments are missing.

    Example:
        python ff_regulay.py -input src/ff/in.sfd -output _output/out.ttf
    """
    parser = argparse.ArgumentParser(
        description="Call FontForge to generate a TTF from an SFD source."
    )
    parser.add_argument("-input", required=True, help="Input SFD path")
    parser.add_argument("-output", required=True, help="Output TTF path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_sfd = Path(args.input).resolve()
    output_ttf = Path(args.output).resolve()

    if not input_sfd.exists():
        print(f"Input file not found: {input_sfd}", file=sys.stderr)
        return 2

    output_ttf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
        tmp.write(FF_SCRIPT)
        ff_script_path = Path(tmp.name)

    try:
        cmd = [
            str(FONTFORGE_BIN),
            "-lang=py",
            "-script",
            str(ff_script_path),
            str(input_sfd),
            str(output_ttf),
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
