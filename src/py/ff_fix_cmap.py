#!/usr/bin/env python3
"""Fix cmap entries for required pinyin combining marks and related letters."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


TARGET_TEXT = (
    "◌́◌̀◌̂◌̌◌̄◌̍◌̋◌̆◌͘ "
    "a̍a̋e̍e̋i̍i̋o̍u̍m̀m̂m̌m̄m̍m̋m̆n̂n̄n̍n̋n̆ "
    "A̍A̋E̍E̋I̍I̋O̍U̍M̀M̂M̌M̄M̍M̋M̆N̂N̄N̍N̋N̆"
)

# Explicit preferred glyph names for combining marks.
PREFERRED_GLYPH_NAMES = {
    0x0300: ["gravecomb", "uni0300"],
    0x0301: ["acutecomb", "uni0301"],
    0x0302: ["uni0302", "circumflexcomb", "uni0302.case"],
    0x0304: ["uni0304", "macroncomb", "uni0304.case"],
    0x0306: ["uni0306", "brevecomb", "uni0306.case"],
    0x030B: ["uni030B", "hungarumlautcomb", "uni030B.case"],
    0x030C: ["uni030C", "caroncomb", "uni030C.case"],
    0x030D: ["uni030D"],
    0x0358: ["uni0358"],
}

TARGET_O_GLYPHS = [
    "O",
    "Oacute",
    "Ograve",
    "Ocircumflex",
    "uni01D1",  # Ǒ
    "Omacron",  # Ō
    "Obreve",  # Ŏ
    "Ohungarumlaut",  # Ő
]


def parse_args() -> argparse.Namespace:
    """Summary: Parse CLI arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed arguments.

    Raises:
        SystemExit: When required args are missing.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Dump font to JSON, fix required cmap entries for pinyin-related "
            "combining marks/letters, then rebuild font with otfccbuild.exe."
        )
    )
    parser.add_argument("-input", required=True, help="Input font path")
    parser.add_argument("-output", required=True, help="Output font path")
    parser.add_argument("--otfccdump", default="otfccdump.exe", help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default="otfccbuild.exe", help="Path to otfccbuild executable")
    return parser.parse_args()


def collect_required_codepoints() -> list[int]:
    """Summary: Collect unique codepoints from TARGET_TEXT.

    Args:
        None

    Returns:
        list[int]: Sorted unique Unicode codepoints.
    """
    codepoints: set[int] = set()
    for ch in TARGET_TEXT:
        if ch.isspace() or ch == "◌":
            continue
        codepoints.add(ord(ch))
    return sorted(codepoints)


def pick_glyph_name(cp: int, glyph_set: set[str], cmap: dict[str, str]) -> str | None:
    """Summary: Pick a glyph name for a Unicode codepoint.

    Args:
        cp: Unicode codepoint.
        glyph_set: Existing glyph names in font.
        cmap: Current cmap mapping.

    Returns:
        str | None: Matching glyph name if found.
    """
    key = str(cp)
    if key in cmap and cmap[key] in glyph_set:
        return cmap[key]

    candidates: list[str] = []

    if cp in PREFERRED_GLYPH_NAMES:
        candidates.extend(PREFERRED_GLYPH_NAMES[cp])

    ch = chr(cp)
    if "A" <= ch <= "Z" or "a" <= ch <= "z":
        candidates.append(ch)

    candidates.append(f"uni{cp:04X}")
    candidates.append(f"u{cp:04X}")

    for name in candidates:
        if name in glyph_set:
            return name

    return None


def run_cmd(cmd: list[str]) -> None:
    """Summary: Run a command and fail on non-zero exit.

    Args:
        cmd: Command arguments.

    Returns:
        None

    Raises:
        RuntimeError: If command exits non-zero.
    """
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def _glyph_y_bounds(glyf_entry: dict) -> tuple[int, int] | None:
    """Summary: Calculate y-bounds from a glyf contour entry.

    Args:
        glyf_entry: One glyph object in ttf_json["glyf"].

    Returns:
        tuple[int, int] | None: (y_min, y_max) if contours exist, else None.
    """
    contours = glyf_entry.get("contours")
    if not isinstance(contours, list) or not contours:
        return None

    ys: list[int] = []
    for contour in contours:
        if not isinstance(contour, list):
            continue
        for point in contour:
            if isinstance(point, dict) and "y" in point:
                ys.append(int(point["y"]))

    if not ys:
        return None

    return min(ys), max(ys)


def _pick_o_anchor_class_and_y(subtable: dict) -> tuple[str, int] | None:
    """Summary: Pick the base anchor class/y for O-series attachment.

    Args:
        subtable: A gpos_mark_to_base subtable object.

    Returns:
        tuple[str, int] | None: (anchor class name, O base anchor y) if found.
    """
    bases = subtable.get("bases")
    if not isinstance(bases, dict):
        return None

    o_base = bases.get("O")
    if not isinstance(o_base, dict):
        return None

    # Prefer anchor4 because Oacute/Ograve/Ocircumflex may move anchor2 upward
    # with tone marks, while anchor4 stays near the O top edge.
    for cls in ("anchor4", "anchor2"):
        anchor = o_base.get(cls)
        if isinstance(anchor, dict) and "y" in anchor:
            return cls, int(anchor["y"])

    return None


def _pick_mark_x(marks: dict, preferred_class: str) -> int:
    """Summary: Pick a sensible x for uni0358 mark anchor.

    Args:
        marks: Subtable marks object.
        preferred_class: Anchor class chosen for uni0358.

    Returns:
        int: X coordinate to use for uni0358 mark anchor.
    """
    current = marks.get("uni0358")
    if isinstance(current, dict) and "x" in current:
        return int(current["x"])

    for item in marks.values():
        if isinstance(item, dict) and item.get("class") == preferred_class and "x" in item:
            return int(item["x"])

    for fallback_name in ("uni030D", "uni030C", "uni030B", "acutecomb"):
        fallback = marks.get(fallback_name)
        if isinstance(fallback, dict) and "x" in fallback:
            return int(fallback["x"])

    return 0


def fix_uni0358(ttf_json: dict) -> dict[str, int]:
    """Summary: Fix uni0358 mark class/position for uppercase O-series use.

    Args:
        ttf_json: Parsed otfcc JSON object.

    Returns:
        dict[str, int]: Counters of applied updates.
    """
    stats = {
        "class_updates": 0,
        "mark_entries_updated": 0,
        "subtables_touched": 0,
    }

    glyf = ttf_json.get("glyf", {})
    if not isinstance(glyf, dict):
        return stats

    o_bounds = _glyph_y_bounds(glyf.get("O", {}))
    uni0358_bounds = _glyph_y_bounds(glyf.get("uni0358", {}))
    if o_bounds is None or uni0358_bounds is None:
        return stats

    o_top_y = o_bounds[1]
    uni0358_bottom_y = uni0358_bounds[0]

    # Ensure uni0358 is a Mark in GDEF.
    gdef = ttf_json.setdefault("GDEF", {})
    glyph_class_def = gdef.setdefault("glyphClassDef", {})
    old_class = glyph_class_def.get("uni0358")
    if old_class != 3:
        glyph_class_def["uni0358"] = 3
        stats["class_updates"] += 1

    gpos = ttf_json.get("GPOS", {})
    lookups = gpos.get("lookups", {})
    if not isinstance(lookups, dict):
        return stats

    for lookup in lookups.values():
        if not isinstance(lookup, dict):
            continue
        if lookup.get("type") != "gpos_mark_to_base":
            continue

        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue

        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue

            picked = _pick_o_anchor_class_and_y(subtable)
            if picked is None:
                continue
            anchor_class, o_anchor_y = picked

            marks = subtable.get("marks")
            bases = subtable.get("bases")
            if not isinstance(marks, dict) or not isinstance(bases, dict):
                continue

            if not any(isinstance(bases.get(g), dict) for g in TARGET_O_GLYPHS):
                continue

            # final_bottom = base_y - mark_y + mark_bottom
            # target: final_bottom == O_top_y
            mark_y = o_anchor_y + uni0358_bottom_y - o_top_y
            mark_x = _pick_mark_x(marks, anchor_class)

            marks["uni0358"] = {
                "class": anchor_class,
                "x": int(mark_x),
                "y": int(mark_y),
            }
            stats["mark_entries_updated"] += 1
            stats["subtables_touched"] += 1

    return stats


def load_json_with_fallback(json_path: Path) -> dict:
    """Summary: Load JSON with encoding fallback for otfccdump outputs.

    Args:
        json_path: Path to JSON file.

    Returns:
        dict: Parsed JSON data.

    Raises:
        UnicodeDecodeError: If all encoding attempts fail.
        json.JSONDecodeError: If decoded text is not valid JSON.
    """
    encodings = ["utf-8", "utf-8-sig", "cp950", "cp936", "mbcs", "latin-1"]
    last_exc: Exception | None = None

    for enc in encodings:
        try:
            with json_path.open("r", encoding=enc) as f:
                return json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_exc = exc
            continue

    if last_exc is not None:
        raise last_exc
    raise UnicodeDecodeError("utf-8", b"", 0, 1, "Failed to decode JSON with fallback encodings")


def main() -> int:
    """Summary: Script entry point.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        python ff_fix_cmap.py -input in.ttf -output out.ttf
    """
    args = parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "font.json"

        run_cmd([args.otfccdump, "--pretty", str(input_path), "-o", str(json_path)])

        data = load_json_with_fallback(json_path)

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

        with json_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        run_cmd([args.otfccbuild, str(json_path), "-o", str(output_path)])

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
        f"subtables_touched={uni0358_stats['subtables_touched']}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
