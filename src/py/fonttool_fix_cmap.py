#!/usr/bin/env python3
"""Fix cmap and layout tables while preserving variable-font tables."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont

from ff_fix_cmap import (
    collect_required_codepoints,
    fix_i_ccmp,
    fix_uni0358,
    load_json_with_fallback,
    pick_glyph_name,
    run_cmd,
)


PATCHED_TABLE_TAGS = ("cmap", "GDEF", "GPOS", "GSUB")


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Raises:
        SystemExit: If required arguments are missing.

    Example:
        python fonttool_fix_cmap.py -input in.ttf -output out.ttf
    """

    parser = argparse.ArgumentParser(
        description=(
            "Fix cmap entries, uni0358 anchors, and ccmp substitutions while "
            "preserving variable-font tables."
        )
    )
    parser.add_argument("-input", required=True, help="Input font path")
    parser.add_argument("-output", required=True, help="Output font path")
    parser.add_argument("--otfccdump", default="otfccdump.exe", help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default="otfccbuild.exe", help="Path to otfccbuild executable")
    return parser.parse_args()


def apply_json_fixes(data: dict) -> tuple[list[tuple[int, str]], list[int], dict[str, int], dict[str, int]]:
    """Summary: Apply cmap, GDEF, GPOS, and GSUB fixes to otfcc JSON.

    Args:
        data: Parsed otfcc JSON.

    Returns:
        tuple[list[tuple[int, str]], list[int], dict[str, int], dict[str, int]]:
            Added cmap entries, missing codepoints, uni0358 stats, and ccmp stats.

    Example:
        apply_json_fixes({"cmap": {}, "glyph_order": []})
    """

    cmap = data.setdefault("cmap", {})
    glyph_order = data.get("glyph_order", [])
    glyph_set = set(glyph_order)

    required_cps = collect_required_codepoints()
    added: list[tuple[int, str]] = []
    missing: list[int] = []

    for cp in required_cps:
        key = str(cp)
        if key in cmap:
            continue

        glyph_name = pick_glyph_name(cp, glyph_set, cmap)
        if glyph_name is None:
            missing.append(cp)
            continue

        cmap[key] = glyph_name
        added.append((cp, glyph_name))

    uni0358_stats = fix_uni0358(data)
    ccmp_stats = fix_i_ccmp(data)
    return added, missing, uni0358_stats, ccmp_stats


def copy_patched_tables(original_font_path: Path, patched_font_path: Path, output_path: Path) -> None:
    """Summary: Copy patched tables onto the original font and save output.

    Args:
        original_font_path: Original input font path.
        patched_font_path: Temporary rebuilt font path containing patched tables.
        output_path: Final output font path.

    Returns:
        None

    Example:
        copy_patched_tables(Path("in.ttf"), Path("patched.ttf"), Path("out.ttf"))
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with TTFont(str(original_font_path)) as original_font, TTFont(str(patched_font_path)) as patched_font:
        for tag in PATCHED_TABLE_TAGS:
            if tag in patched_font:
                original_font[tag] = copy.deepcopy(patched_font[tag])
        original_font.save(str(output_path))


def main() -> int:
    """Summary: Run fonttool_fix_cmap.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        json_path = tmp_path / "font.json"
        patched_font_path = tmp_path / "patched_tables.ttf"

        run_cmd([args.otfccdump, "--pretty", str(input_path), "-o", str(json_path)])

        data = load_json_with_fallback(json_path)
        added, missing, uni0358_stats, ccmp_stats = apply_json_fixes(data)

        with json_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        run_cmd([args.otfccbuild, str(json_path), "-o", str(patched_font_path)])
        copy_patched_tables(input_path, patched_font_path, output_path)

    if added:
        print("Added cmap entries:")
        for cp, glyph in added:
            print(f"  U+{cp:04X} -> {glyph}")
    else:
        print("No new cmap entries were added.")

    if missing:
        print("Missing glyphs for these codepoints (could not add to cmap):")
        for cp in missing:
            print(f"  U+{cp:04X}")

    print(
        "uni0358 fix stats: "
        f"class_updates={uni0358_stats['class_updates']}, "
        f"mark_entries_updated={uni0358_stats['mark_entries_updated']}, "
        f"subtables_touched={uni0358_stats['subtables_touched']}, "
        f"base_anchor_updates={uni0358_stats['base_anchor_updates']}"
    )

    print(
        "ccmp fix stats: "
        f"feature_created={ccmp_stats['feature_created']}, "
        f"lookup_created={ccmp_stats['lookup_created']}, "
        f"rules_added_or_updated={ccmp_stats['rules_added_or_updated']}, "
        f"languages_updated={ccmp_stats['languages_updated']}"
    )

    print(f"Done: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
