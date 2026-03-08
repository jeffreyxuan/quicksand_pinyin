#!/usr/bin/env python3
"""Fix cmap entries, uni0358 anchors, and ccmp substitutions."""

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

UPPER_O_GLYPHS = [
    "O",
    "Oacute",
    "Ograve",
    "Ocircumflex",
    "uni01D1",
    "Omacron",
    "Obreve",
    "Ohungarumlaut",
]

LOWER_O_GLYPHS = [
    "o",
    "oacute",
    "ograve",
    "ocircumflex",
    "uni01D2",
    "omacron",
    "obreve",
    "ohungarumlaut",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dump font to JSON, fix required cmap entries, apply uni0358 anchor "
            "rules, and rebuild font with otfccbuild.exe."
        )
    )
    parser.add_argument("-input", required=True, help="Input font path")
    parser.add_argument("-output", required=True, help="Output font path")
    parser.add_argument("--otfccdump", default="otfccdump.exe", help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default="otfccbuild.exe", help="Path to otfccbuild executable")
    return parser.parse_args()


def collect_required_codepoints() -> list[int]:
    codepoints: set[int] = set()
    for ch in TARGET_TEXT:
        if ch.isspace() or ch == "◌":
            continue
        codepoints.add(ord(ch))
    return sorted(codepoints)


def pick_glyph_name(cp: int, glyph_set: set[str], cmap: dict[str, str]) -> str | None:
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def _glyph_bounds(glyf_entry: dict) -> tuple[int, int, int, int] | None:
    contours = glyf_entry.get("contours")
    if not isinstance(contours, list) or not contours:
        return None

    xs: list[int] = []
    ys: list[int] = []
    for contour in contours:
        if not isinstance(contour, list):
            continue
        for point in contour:
            if not isinstance(point, dict):
                continue
            if "x" in point:
                xs.append(int(point["x"]))
            if "y" in point:
                ys.append(int(point["y"]))

    if not xs or not ys:
        return None

    return min(xs), max(xs), min(ys), max(ys)


def _pick_o_anchor_class_and_point(subtable: dict) -> tuple[str, int, int] | None:
    bases = subtable.get("bases")
    if not isinstance(bases, dict):
        return None

    o_base = bases.get("O")
    if not isinstance(o_base, dict):
        return None

    for cls in ("anchor4", "anchor2"):
        anchor = o_base.get(cls)
        if isinstance(anchor, dict) and "x" in anchor and "y" in anchor:
            return cls, int(anchor["x"]), int(anchor["y"])

    return None


def _set_base_anchor(base: dict, anchor_name: str, x: int, y: int) -> bool:
    new = {"x": int(x), "y": int(y)}
    if base.get(anchor_name) == new:
        return False
    base[anchor_name] = new
    return True


def fix_uni0358(ttf_json: dict) -> dict[str, int]:
    stats = {
        "class_updates": 0,
        "mark_entries_updated": 0,
        "subtables_touched": 0,
        "base_anchor_updates": 0,
    }

    glyf = ttf_json.get("glyf", {})
    if not isinstance(glyf, dict):
        return stats

    o_bounds = _glyph_bounds(glyf.get("O", {}))
    lower_o_bounds = _glyph_bounds(glyf.get("o", {}))
    uni0358_bounds = _glyph_bounds(glyf.get("uni0358", {}))
    if o_bounds is None or lower_o_bounds is None or uni0358_bounds is None:
        return stats

    _, o_right_x, _, o_top_y = o_bounds
    _, lower_o_right_x, _, _ = lower_o_bounds
    uni0358_left_x, _, uni0358_bottom_y, _ = uni0358_bounds

    gdef = ttf_json.setdefault("GDEF", {})
    glyph_class_def = gdef.setdefault("glyphClassDef", {})
    if glyph_class_def.get("uni0358") != 3:
        glyph_class_def["uni0358"] = 3
        stats["class_updates"] += 1

    gpos = ttf_json.get("GPOS", {})
    lookups = gpos.get("lookups", {})
    if not isinstance(lookups, dict):
        return stats

    for lookup in lookups.values():
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_mark_to_base":
            continue

        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue

        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue

            picked = _pick_o_anchor_class_and_point(subtable)
            if picked is None:
                continue
            source_class, o_anchor_x, o_anchor_y = picked

            marks = subtable.get("marks")
            bases = subtable.get("bases")
            if not isinstance(marks, dict) or not isinstance(bases, dict):
                continue

            has_upper = any(isinstance(bases.get(g), dict) for g in UPPER_O_GLYPHS)
            has_lower = any(isinstance(bases.get(g), dict) for g in LOWER_O_GLYPHS)
            if not has_upper and not has_lower:
                continue

            target_class = "anchor5"

            mark_x = o_anchor_x + uni0358_left_x - o_right_x
            mark_y = o_anchor_y + uni0358_bottom_y - o_top_y

            new_mark = {"class": target_class, "x": int(mark_x), "y": int(mark_y)}
            if marks.get("uni0358") != new_mark:
                marks["uni0358"] = new_mark
                stats["mark_entries_updated"] += 1

            upper_base_x = o_right_x + mark_x - uni0358_left_x
            upper_base_y = o_top_y + mark_y - uni0358_bottom_y
            for glyph_name in UPPER_O_GLYPHS:
                base = bases.get(glyph_name)
                if isinstance(base, dict) and _set_base_anchor(base, target_class, upper_base_x, upper_base_y):
                    stats["base_anchor_updates"] += 1

            lower_base_x = lower_o_right_x + mark_x - uni0358_left_x
            for glyph_name in LOWER_O_GLYPHS:
                base = bases.get(glyph_name)
                if not isinstance(base, dict):
                    continue
                src_anchor = base.get(source_class)
                if isinstance(src_anchor, dict) and "y" in src_anchor:
                    lower_base_y = int(src_anchor["y"])
                else:
                    lower_base_y = upper_base_y
                if _set_base_anchor(base, target_class, lower_base_x, lower_base_y):
                    stats["base_anchor_updates"] += 1

            stats["subtables_touched"] += 1

    return stats


def fix_i_ccmp(ttf_json: dict) -> dict[str, int]:
    stats = {
        "feature_created": 0,
        "lookup_created": 0,
        "rules_added_or_updated": 0,
        "languages_updated": 0,
    }

    glyph_order = ttf_json.get("glyph_order", [])
    if "i_hungarumlautcomb" not in glyph_order or "i_verticallineabovecomb" not in glyph_order:
        return stats

    gsub = ttf_json.setdefault("GSUB", {})
    lookups = gsub.setdefault("lookups", {})
    features = gsub.setdefault("features", {})
    languages = gsub.setdefault("languages", {})
    lookup_order = gsub.setdefault("lookupOrder", [])

    ccmp_key = None
    for k in features.keys():
        if k == "ccmp" or str(k).startswith("ccmp"):
            ccmp_key = k
            break

    if ccmp_key is None:
        ccmp_key = "ccmp_auto"
        features[ccmp_key] = []
        stats["feature_created"] += 1

    ccmp_lookups = features.get(ccmp_key)
    if not isinstance(ccmp_lookups, list):
        ccmp_lookups = []
        features[ccmp_key] = ccmp_lookups

    lookup_name = None
    for lname in ccmp_lookups:
        lk = lookups.get(lname)
        if isinstance(lk, dict) and lk.get("type") == "gsub_ligature":
            lookup_name = lname
            break

    if lookup_name is None:
        lookup_name = "lookup_ccmp_i_marks"
        idx = 0
        while lookup_name in lookups:
            idx += 1
            lookup_name = f"lookup_ccmp_i_marks_{idx}"
        lookups[lookup_name] = {
            "type": "gsub_ligature",
            "flags": {},
            "subtables": [{"substitutions": []}],
        }
        ccmp_lookups.append(lookup_name)
        lookup_order.append(lookup_name)
        stats["lookup_created"] += 1

    lookup = lookups[lookup_name]
    if lookup.get("type") != "gsub_ligature":
        lookup["type"] = "gsub_ligature"

    subtables = lookup.setdefault("subtables", [])
    if not isinstance(subtables, list) or len(subtables) == 0:
        subtables = [{"substitutions": []}]
        lookup["subtables"] = subtables

    if "substitutions" not in subtables[0] or not isinstance(subtables[0]["substitutions"], list):
        subtables[0]["substitutions"] = []
    substitutions = subtables[0]["substitutions"]

    wanted = [
        {"from": ["i", "uni030B"], "to": "i_hungarumlautcomb"},
        {"from": ["i", "uni030D"], "to": "i_verticallineabovecomb"},
    ]

    for rule in wanted:
        found = False
        for item in substitutions:
            if not isinstance(item, dict):
                continue
            if item.get("from") == rule["from"]:
                found = True
                if item.get("to") != rule["to"]:
                    item["to"] = rule["to"]
                    stats["rules_added_or_updated"] += 1
                break
        if not found:
            substitutions.append(rule)
            stats["rules_added_or_updated"] += 1

    for lang_obj in languages.values():
        if not isinstance(lang_obj, dict):
            continue
        feats = lang_obj.get("features")
        if not isinstance(feats, list):
            continue
        if ccmp_key not in feats:
            feats.append(ccmp_key)
            stats["languages_updated"] += 1

    return stats


def load_json_with_fallback(json_path: Path) -> dict:
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
        ccmp_stats = fix_i_ccmp(data)

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
