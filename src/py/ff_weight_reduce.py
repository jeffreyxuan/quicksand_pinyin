#!/usr/bin/env python3
"""Reduce glyph stroke weight with FontForge while preserving advance widths."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


FF_SCRIPT = r'''
import os
import sys
import fontforge


def save_font(font, output_path):
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".sfd":
        font.save(output_path)
    else:
        font.generate(output_path)


if len(sys.argv) < 3:
    raise SystemExit("Usage: ff_script.py <input> <output>")

input_path = sys.argv[1]
output_path = sys.argv[2]

font = fontforge.open(input_path)
old_widths = {g.glyphname: g.width for g in font.glyphs()}

for g in font.glyphs():
    if not g.isWorthOutputting():
        continue
    if g.foreground.isEmpty():
        continue

    g.changeWeight(-16)
    g.width = old_widths[g.glyphname]

for g in font.glyphs():
    if g.glyphname in old_widths:
        g.width = old_widths[g.glyphname]

save_font(font, output_path)
font.close()
print(f"Done: {output_path}")
'''


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI args.

    Raises:
        SystemExit: If required arguments are missing.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Call FontForge Python to reduce all glyph stroke weights by 16 "
            "while keeping each glyph advance width unchanged."
        )
    )
    parser.add_argument("-input", required=True, help="Input font path (.sfd/.ttf/.otf)")
    parser.add_argument("-output", required=True, help="Output font path")
    parser.add_argument(
        "--fontforge-bin",
        default="fontforge",
        help="FontForge executable path (default: fontforge)",
    )
    return parser.parse_args()


def run_fontforge(fontforge_bin: str, input_path: Path, output_path: Path) -> None:
    """Summary: Run FontForge with an internal Python script.

    Args:
        fontforge_bin: FontForge executable.
        input_path: Source font file.
        output_path: Destination font file.

    Returns:
        None

    Raises:
        RuntimeError: If FontForge command fails.
        FileNotFoundError: If FontForge executable is missing.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
        tmp.write(FF_SCRIPT)
        script_path = Path(tmp.name)

    try:
        cmd = [
            fontforge_bin,
            "-lang=py",
            "-script",
            str(script_path),
            str(input_path),
            str(output_path),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)

    if completed.returncode != 0:
        raise RuntimeError(f"FontForge failed (exit {completed.returncode}).")


def main() -> int:
    """Summary: CLI entry point.

    Args:
        None

    Returns:
        int: Process exit code.

    Raises:
        Exception: Any unexpected runtime error.

    Example:
        python ff_weight_reduce.py -input in.sfd -output out.sfd
    """
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        run_fontforge(args.fontforge_bin, input_path, output_path)
    except FileNotFoundError:
        print(
            f"FontForge executable not found: {args.fontforge_bin}",
            file=sys.stderr,
        )
        return 3
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
