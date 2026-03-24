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
from typing import Any, Dict, Iterable, List, Tuple

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
DEFAULT_RULES_JSON = Path(__file__).resolve().parents[1] / "json" / "fonttool_fix_cmap_rules.json"


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
    parser.add_argument(
        "--rules-json",
        default=str(DEFAULT_RULES_JSON),
        help="Path to JSON rules file for extra GSUB ligature substitutions",
    )
    parser.add_argument("--otfccdump", default="otfccdump.exe", help="Path to otfccdump executable")
    parser.add_argument("--otfccbuild", default="otfccbuild.exe", help="Path to otfccbuild executable")
    return parser.parse_args()


def ensure_lookup_has_substitutions(lookup: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Summary: Ensure lookup has a writable substitutions list.

    Args:
        lookup: GSUB lookup object.

    Returns:
        List[Dict[str, Any]]: Substitutions list.

    Example:
        ensure_lookup_has_substitutions({"subtables": []})
    """

    subtables = lookup.setdefault("subtables", [])
    if not isinstance(subtables, list) or len(subtables) == 0:
        subtables = [{"substitutions": []}]
        lookup["subtables"] = subtables

    if not isinstance(subtables[0], dict):
        subtables[0] = {"substitutions": []}

    first_subtable = subtables[0]
    substitutions = first_subtable.get("substitutions")
    if not isinstance(substitutions, list):
        substitutions = []
        first_subtable["substitutions"] = substitutions
    return substitutions


def load_rules(rules_json_path: Path) -> List[Dict[str, Any]]:
    """Summary: Load ligature rules from JSON.

    Args:
        rules_json_path: Path to rules JSON file.

    Returns:
        List[Dict[str, Any]]: Parsed rule list.

    Raises:
        ValueError: If JSON shape is invalid.

    Example:
        load_rules(Path("src/json/fonttool_fix_cmap_rules.json"))
    """

    if not rules_json_path.exists():
        return []

    raw = json.loads(rules_json_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        rules = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("gsub_ligature_rules"), list):
            rules = raw["gsub_ligature_rules"]
        elif isinstance(raw.get("rules"), list):
            rules = raw["rules"]
        else:
            raise ValueError("Rules JSON must contain 'gsub_ligature_rules' or 'rules' list.")
    else:
        raise ValueError("Rules JSON root must be an object or a list.")

    valid_rules: List[Dict[str, Any]] = []
    for idx, item in enumerate(rules):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid rule at index {idx}: must be an object.")
        if item.get("enabled", True) is False:
            continue
        frm = item.get("from")
        to = item.get("to")
        if not isinstance(frm, list) or not frm or not all(isinstance(x, str) and x for x in frm):
            raise ValueError(f"Invalid rule at index {idx}: 'from' must be a non-empty string list.")
        if not isinstance(to, str) or not to:
            raise ValueError(f"Invalid rule at index {idx}: 'to' must be a non-empty string.")
        valid_rules.append(item)
    return valid_rules


def apply_ligature_rules(ttf_json: Dict[str, Any], rules: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Summary: Apply ligature substitutions from JSON rules to GSUB.

    Args:
        ttf_json: Parsed otfcc JSON.
        rules: Iterable of ligature rule objects.

    Returns:
        Dict[str, int]: Stats of feature/language/rule updates.

    Raises:
        ValueError: If required GSUB structures are missing.

    Example:
        apply_ligature_rules({"GSUB": {}}, [{"from":["a","b"],"to":"ab"}])
    """

    stats = {
        "feature_updates": 0,
        "lookup_updates": 0,
        "rules_added_or_updated": 0,
        "languages_updated": 0,
    }
    rules_list = list(rules)
    if not rules_list:
        return stats

    gsub = ttf_json.setdefault("GSUB", {})
    if not isinstance(gsub, dict):
        raise ValueError("Invalid GSUB table structure.")
    lookups = gsub.setdefault("lookups", {})
    features = gsub.setdefault("features", {})
    languages = gsub.setdefault("languages", {})
    lookup_order = gsub.setdefault("lookupOrder", [])
    if not isinstance(lookups, dict) or not isinstance(features, dict):
        raise ValueError("Invalid GSUB lookups/features structure.")

    for rule in rules_list:
        feature_name = str(rule.get("feature", "ccmp_00002"))
        lookup_name = str(rule.get("lookup", "lookup_ccmp_6"))
        from_list = [str(x) for x in rule["from"]]
        to_glyph = str(rule["to"])
        language_list = rule.get("languages")

        if feature_name == "ccmp_00000":
            raise ValueError("Rule feature must not be ccmp_00000; use existing ccmp_00002/ccmp_00003.")

        if feature_name not in features:
            raise ValueError(f"Feature not found: {feature_name}")
        feature_lookups = features.get(feature_name)
        if not isinstance(feature_lookups, list):
            raise ValueError(f"Feature lookup list is invalid: {feature_name}")
        if lookup_name not in feature_lookups:
            feature_lookups.append(lookup_name)
            stats["feature_updates"] += 1

        lookup = lookups.get(lookup_name)
        if lookup is None:
            lookup = {"type": "gsub_ligature", "flags": {}, "subtables": [{"substitutions": []}]}
            lookups[lookup_name] = lookup
            stats["lookup_updates"] += 1
        if lookup.get("type") != "gsub_ligature":
            raise ValueError(f"Lookup {lookup_name} is not gsub_ligature.")
        substitutions = ensure_lookup_has_substitutions(lookup)

        found = False
        for item in substitutions:
            if not isinstance(item, dict):
                continue
            if item.get("from") == from_list:
                found = True
                if item.get("to") != to_glyph:
                    item["to"] = to_glyph
                    stats["rules_added_or_updated"] += 1
                break
        if not found:
            substitutions.append({"from": from_list, "to": to_glyph})
            stats["rules_added_or_updated"] += 1

        if lookup_name not in lookup_order and isinstance(lookup_order, list):
            lookup_order.append(lookup_name)

        if language_list is not None:
            if not isinstance(language_list, list) or not all(isinstance(x, str) and x for x in language_list):
                raise ValueError("Rule 'languages' must be a string list when provided.")
            for lang_key in language_list:
                lang_obj = languages.get(lang_key)
                if not isinstance(lang_obj, dict):
                    languages[lang_key] = {"features": [feature_name]}
                    stats["languages_updated"] += 1
                    continue
                feats = lang_obj.get("features")
                if not isinstance(feats, list):
                    lang_obj["features"] = [feature_name]
                    stats["languages_updated"] += 1
                    continue
                if feature_name not in feats:
                    feats.append(feature_name)
                    stats["languages_updated"] += 1

    return stats


def _valid_anchor(anchor: Any) -> bool:
    """Summary: Check whether an anchor object has numeric x/y."""

    return isinstance(anchor, dict) and "x" in anchor and "y" in anchor


def _clone_anchor(anchor: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Clone anchor coordinates as ints."""

    return {"x": int(anchor["x"]), "y": int(anchor["y"])}


def fix_dotted_circle_mark_base(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Ensure U+25CC dotted circle works with combining marks.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Stats for cmap/GDEF/GPOS updates.

    Example:
        fix_dotted_circle_mark_base({"cmap": {}, "GPOS": {}})
    """

    stats = {
        "cmap_updates": 0,
        "class_updates": 0,
        "subtables_touched": 0,
        "base_anchor_updates": 0,
    }

    glyph_order = ttf_json.get("glyph_order", [])
    if not isinstance(glyph_order, list):
        return stats
    glyph_set = set(glyph_order)

    dotted_glyph_name = "uni25CC" if "uni25CC" in glyph_set else None
    if dotted_glyph_name is None:
        return stats

    cmap = ttf_json.setdefault("cmap", {})
    dotted_key = str(0x25CC)
    if cmap.get(dotted_key) != dotted_glyph_name:
        cmap[dotted_key] = dotted_glyph_name
        stats["cmap_updates"] += 1

    gdef = ttf_json.setdefault("GDEF", {})
    glyph_class_def = gdef.setdefault("glyphClassDef", {})
    if glyph_class_def.get(dotted_glyph_name) != 1:
        glyph_class_def[dotted_glyph_name] = 1
        stats["class_updates"] += 1

    gpos = ttf_json.get("GPOS", {})
    lookups = gpos.get("lookups", {}) if isinstance(gpos, dict) else {}
    if not isinstance(lookups, dict):
        return stats

    template_candidates = ("a", "o", "A", "O")

    for lookup in lookups.values():
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_mark_to_base":
            continue
        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue

        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue
            marks = subtable.get("marks")
            bases = subtable.get("bases")
            if not isinstance(marks, dict) or not isinstance(bases, dict):
                continue

            required_classes: set[str] = set()
            for mark_entry in marks.values():
                if isinstance(mark_entry, dict):
                    cls = mark_entry.get("class")
                    if isinstance(cls, str) and cls:
                        required_classes.add(cls)
            if not required_classes:
                continue

            template_bases: Dict[str, Dict[str, Any]] = {}
            for candidate in template_candidates:
                base_entry = bases.get(candidate)
                if isinstance(base_entry, dict) and any(_valid_anchor(v) for v in base_entry.values()):
                    template_bases[candidate] = base_entry
            if not template_bases:
                continue

            fallback_anchor: Dict[str, Any] | None = None
            for candidate in template_candidates:
                base_entry = template_bases.get(candidate)
                if not base_entry:
                    continue
                for anchor in base_entry.values():
                    if _valid_anchor(anchor):
                        fallback_anchor = anchor
                        break
                if fallback_anchor is not None:
                    break
            if fallback_anchor is None:
                continue

            dotted_base = bases.get(dotted_glyph_name)
            if not isinstance(dotted_base, dict):
                dotted_base = {}
                bases[dotted_glyph_name] = dotted_base

            updated = False
            for cls in sorted(required_classes):
                existing = dotted_base.get(cls)
                if _valid_anchor(existing):
                    continue
                src: Dict[str, Any] | None = None
                for candidate in template_candidates:
                    base_entry = template_bases.get(candidate)
                    if not base_entry:
                        continue
                    anchor = base_entry.get(cls)
                    if _valid_anchor(anchor):
                        src = anchor
                        break
                if not _valid_anchor(src):
                    src = fallback_anchor
                dotted_base[cls] = _clone_anchor(src)
                stats["base_anchor_updates"] += 1
                updated = True

            if updated:
                stats["subtables_touched"] += 1

    return stats


def _glyph_bounds(glyf_entry: Dict[str, Any]) -> Tuple[int, int, int, int] | None:
    """Summary: Get glyph contour bounds from otfcc glyf entry."""

    contours = glyf_entry.get("contours")
    if not isinstance(contours, list) or not contours:
        return None
    xs: List[int] = []
    ys: List[int] = []
    for contour in contours:
        if not isinstance(contour, list):
            continue
        for point in contour:
            if not isinstance(point, dict):
                continue
            x = point.get("x")
            y = point.get("y")
            if isinstance(x, (int, float)):
                xs.append(int(x))
            if isinstance(y, (int, float)):
                ys.append(int(y))
    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def fix_uni030d(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Ensure uni030D is a valid mark with GPOS mark entries.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Stats for class/mark updates.
    """

    stats = {"class_updates": 0, "mark_entries_updated": 0, "subtables_touched": 0}

    glyph_order = ttf_json.get("glyph_order", [])
    if not isinstance(glyph_order, list):
        return stats
    glyph_set = set(glyph_order)
    if "uni030D" not in glyph_set:
        return stats

    gdef = ttf_json.setdefault("GDEF", {})
    glyph_class_def = gdef.setdefault("glyphClassDef", {})
    if glyph_class_def.get("uni030D") != 3:
        glyph_class_def["uni030D"] = 3
        stats["class_updates"] += 1

    glyf = ttf_json.get("glyf", {})
    if not isinstance(glyf, dict):
        return stats

    src_mark = "uni030C" if "uni030C" in glyph_set else ("acutecomb" if "acutecomb" in glyph_set else None)
    if src_mark is None:
        return stats

    dst_bounds = _glyph_bounds(glyf.get("uni030D", {}))
    src_bounds = _glyph_bounds(glyf.get(src_mark, {}))
    dx = 0
    dy = 0
    if dst_bounds is not None and src_bounds is not None:
        src_cx = (src_bounds[0] + src_bounds[1]) // 2
        src_cy = (src_bounds[2] + src_bounds[3]) // 2
        dst_cx = (dst_bounds[0] + dst_bounds[1]) // 2
        dst_cy = (dst_bounds[2] + dst_bounds[3]) // 2
        dx = dst_cx - src_cx
        dy = dst_cy - src_cy

    gpos = ttf_json.get("GPOS", {})
    lookups = gpos.get("lookups", {}) if isinstance(gpos, dict) else {}
    if not isinstance(lookups, dict):
        return stats

    for lookup in lookups.values():
        if not isinstance(lookup, dict) or lookup.get("type") not in ("gpos_mark_to_base", "gpos_mark_to_mark"):
            continue
        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue
        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue
            marks = subtable.get("marks")
            if not isinstance(marks, dict):
                continue

            src_entry = marks.get(src_mark)
            if not isinstance(src_entry, dict):
                continue
            cls = src_entry.get("class")
            x = src_entry.get("x")
            y = src_entry.get("y")
            if not isinstance(cls, str) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue

            new_entry = {"class": cls, "x": int(x) + dx, "y": int(y) + dy}
            if marks.get("uni030D") != new_entry:
                marks["uni030D"] = new_entry
                stats["mark_entries_updated"] += 1
                stats["subtables_touched"] += 1

    return stats


def apply_json_fixes(
    data: Dict[str, Any], rules_json_path: Path
) -> Tuple[List[Tuple[int, str]], List[int], Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int]]:
    """Summary: Apply cmap, GDEF, GPOS, and GSUB fixes to otfcc JSON.

    Args:
        data: Parsed otfcc JSON.
        rules_json_path: Path to additional GSUB rules JSON.

    Returns:
        tuple[list[tuple[int, str]], list[int], dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
            Added cmap entries, missing codepoints, uni0358 stats, ccmp stats,
            dotted-circle stats, and uni030D stats.

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
    dotted_circle_stats = fix_dotted_circle_mark_base(data)
    uni030d_stats = fix_uni030d(data)
    ccmp_stats = {"feature_updates": 0, "lookup_updates": 0, "rules_added_or_updated": 0, "languages_updated": 0}
    ccmp_stats["rules_added_or_updated"] += 0
    # Keep legacy i-based ccmp updates.
    legacy_stats = fix_i_ccmp(data)
    ccmp_stats["rules_added_or_updated"] += int(legacy_stats.get("rules_added_or_updated", 0))
    ccmp_stats["languages_updated"] += int(legacy_stats.get("languages_updated", 0))

    extra_rules = load_rules(rules_json_path)
    rule_stats = apply_ligature_rules(data, extra_rules)
    ccmp_stats["feature_updates"] += int(rule_stats.get("feature_updates", 0))
    ccmp_stats["lookup_updates"] += int(rule_stats.get("lookup_updates", 0))
    ccmp_stats["rules_added_or_updated"] += int(rule_stats.get("rules_added_or_updated", 0))
    ccmp_stats["languages_updated"] += int(rule_stats.get("languages_updated", 0))
    return added, missing, uni0358_stats, ccmp_stats, dotted_circle_stats, uni030d_stats


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
    rules_json_path = Path(args.rules_json).resolve()

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
        added, missing, uni0358_stats, ccmp_stats, dotted_circle_stats, uni030d_stats = apply_json_fixes(
            data, rules_json_path
        )

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
        f"feature_updates={ccmp_stats['feature_updates']}, "
        f"lookup_updates={ccmp_stats['lookup_updates']}, "
        f"rules_added_or_updated={ccmp_stats['rules_added_or_updated']}, "
        f"languages_updated={ccmp_stats['languages_updated']}"
    )
    print(
        "dotted-circle fix stats: "
        f"cmap_updates={dotted_circle_stats['cmap_updates']}, "
        f"class_updates={dotted_circle_stats['class_updates']}, "
        f"subtables_touched={dotted_circle_stats['subtables_touched']}, "
        f"base_anchor_updates={dotted_circle_stats['base_anchor_updates']}"
    )
    print(
        "uni030D fix stats: "
        f"class_updates={uni030d_stats['class_updates']}, "
        f"mark_entries_updated={uni030d_stats['mark_entries_updated']}, "
        f"subtables_touched={uni030d_stats['subtables_touched']}"
    )

    print(f"Done: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
