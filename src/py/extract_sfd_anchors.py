#!/usr/bin/env python3
"""Extract base anchors from a FontForge SFD into JSON rules."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

FONTFORGE_BIN = Path(r"C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe")

FONTFORGE_EXTRACT_SCRIPT = r'''
import json
import sys
import fontforge

input_sfd = sys.argv[1]
output_json = sys.argv[2]

font = fontforge.open(input_sfd)
result = {"glyph_anchors": {}}

for glyph in font.glyphs():
    anchors = {}
    for item in glyph.anchorPoints:
        if len(item) < 4:
            continue
        name, anchor_type, x, y = item[:4]
        if anchor_type != "base":
            continue
        anchor_name = str(name).replace("Anchor-", "anchor").replace("-", "")
        anchors[anchor_name] = {"x": int(round(float(x))), "y": int(round(float(y)))}
    if anchors:
        result["glyph_anchors"][glyph.glyphname] = anchors

with open(output_json, "w", encoding="utf-8") as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

font.close()
print(f"Done: {output_json}")
'''


def parse_args() -> argparse.Namespace:
    """Summary: Parse CLI arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed arguments.

    Example:
        python extract_sfd_anchors.py -input in.sfd -output out.json
    """

    parser = argparse.ArgumentParser(description="Extract base anchors from a FontForge SFD file.")
    parser.add_argument("-input", required=True, help="Input SFD path")
    parser.add_argument("-output", required=True, help="Output JSON path")
    return parser.parse_args()


def indent_stderr(stderr_text: str) -> str:
    """Summary: Indent stderr text for easier visual grouping.

    Args:
        stderr_text: Raw stderr text.

    Returns:
        str: Stderr text with each non-empty line prefixed by eight spaces.

    Example:
        indent_stderr("line1\nline2\n")
    """

    indented_lines: list[str] = []
    for line in stderr_text.splitlines(keepends=True):
        if line.strip():
            indented_lines.append(f"        {line}")
        else:
            indented_lines.append(line)
    return "".join(indented_lines)


def extract_sfd_anchors(input_sfd: Path, output_json: Path) -> None:
    """Summary: Extract base anchors from an SFD file into JSON.

    Args:
        input_sfd: Source SFD path.
        output_json: Destination JSON path.

    Returns:
        None

    Raises:
        FileNotFoundError: If required input or FontForge executable is missing.
        ValueError: If input/output extensions are invalid.
        RuntimeError: If FontForge execution fails.

    Example:
        extract_sfd_anchors(Path("src/ufo/anchor/ToneOZ-Quicksnow_anchor.sfd"), Path("src/json/fonttool_fix_anchor_rules.json"))
    """

    if not input_sfd.exists():
        raise FileNotFoundError(f"Input SFD not found: {input_sfd}")
    if input_sfd.suffix.lower() != ".sfd":
        raise ValueError(f"Input must be .sfd: {input_sfd}")
    if output_json.suffix.lower() != ".json":
        raise ValueError(f"Output must be .json: {output_json}")
    if not FONTFORGE_BIN.exists():
        raise FileNotFoundError(f"FontForge not found: {FONTFORGE_BIN}")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "extract_sfd_anchors_ff.py"
        script_path.write_text(FONTFORGE_EXTRACT_SCRIPT, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [str(FONTFORGE_BIN), "-script", str(script_path), str(input_sfd), str(output_json)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(indent_stderr(result.stderr), end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"FontForge failed while extracting anchors: exit code {result.returncode}")


def main() -> int:
    """Summary: Run the SFD anchor extraction CLI.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()
    try:
        extract_sfd_anchors(Path(args.input).resolve(), Path(args.output).resolve())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
