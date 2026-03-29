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
    load_json_with_fallback,
    pick_glyph_name,
)
from font_name_utils import (
    apply_rename_rules,
    compute_version,
    normalize_name_records,
    replace_version_placeholders,
)


PATCHED_TABLE_TAGS = ("cmap", "GDEF", "GPOS", "GSUB", "name", "head", "OS/2")
DEFAULT_RULES_JSON = Path(__file__).resolve().parents[1] / "json" / "fonttool_fix_cmap_rules.json"
DEFAULT_NAME_JSON = Path(__file__).resolve().parents[1] / "json" / "name_Quicksand-VariableFont_wght.json"
DEFAULT_ANCHOR_RULES_JSON = Path(__file__).resolve().parents[1] / "json" / "fonttool_fix_anchor_rules.json"
UNI030D_ON_UNI0358_X_SHIFT = -12
UNI030D_ON_UNI0358_Y_SHIFT = 30


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


def eprint(*args: object, **kwargs: object) -> None:
    """Summary: Print stderr text with 8-space indentation.

    Args:
        *args: Message parts to print.
        **kwargs: Extra print keyword arguments.

    Returns:
        None

    Example:
        eprint("Something went wrong")
    """

    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    text = sep.join(str(arg) for arg in args) + end
    print(indent_stderr(text), end="", file=sys.stderr, **kwargs)


def run_cmd(cmd: list[str]) -> None:
    """Summary: Run a subprocess command with indented stderr output.

    Args:
        cmd: Command and arguments.

    Returns:
        None

    Raises:
        RuntimeError: If the command fails.

    Example:
        run_cmd(["otfccdump.exe", "--version"])
    """

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


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
    parser.add_argument(
        "--name-json",
        default=str(DEFAULT_NAME_JSON),
        help="Path to name table JSON used to rename output font metadata",
    )
    parser.add_argument(
        "--anchor-rules-json",
        default=str(DEFAULT_ANCHOR_RULES_JSON),
        help="Path to JSON rules file for patching GPOS mark_to_base anchors",
    )
    parser.add_argument(
        "--merge-source-kern-from",
        default="",
        help="Optional source variable font path used to merge original kern into rebuilt variable mark/mkmk GPOS",
    )
    parser.add_argument(
        "--copy-kern-x-to-i",
        action="store_true",
        help="Copy all X-left/X-right kerning rules to I in kern PairPos lookups",
    )
    parser.add_argument(
        "--copy-kern-t-left-to-j",
        "--copy_kern_T_left_only_to_J",
        dest="copy_kern_t_left_to_j",
        action="store_true",
        help="Copy T-left kerning rules to J-left only (keep J-right kerning unchanged)",
    )
    parser.add_argument(
        "-fix_stat_linked_bold",
        action="store_true",
        help="Patch STAT linked bold entries: 300->700, 500->700, 600->700",
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


def sort_ligature_substitutions(substitutions: List[Dict[str, Any]]) -> None:
    """Summary: Sort ligature substitutions by longest source sequence first.

    Args:
        substitutions: Mutable substitutions list.

    Returns:
        None

    Example:
        sort_ligature_substitutions([{"from": ["a", "b"], "to": "ab"}])
    """

    def _key(item: Dict[str, Any]) -> Tuple[int, str]:
        src = item.get("from")
        if isinstance(src, list):
            src_list = [str(x) for x in src]
            return (-len(src_list), "|".join(src_list))
        return (0, "")

    substitutions.sort(key=_key)


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

        # Keep longer ligature patterns first, so 3-glyph rules are not shadowed
        # by earlier 2-glyph rules in the same lookup.
        sort_ligature_substitutions(substitutions)

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


def apply_name_json_rename(ttf_json: Dict[str, Any], name_json_path: Path) -> Dict[str, int]:
    """Summary: Apply name JSON and version placeholders to font metadata.

    Args:
        ttf_json: Parsed otfcc JSON.
        name_json_path: Name table JSON path.

    Returns:
        Dict[str, int]: Rename stats.

    Example:
        apply_name_json_rename({}, Path("src/json/name_Quicksand-VariableFont_wght.json"))
    """

    stats = {
        "enabled": 0,
        "name_records_applied": 0,
        "version_replaced_count": 0,
    }
    if not name_json_path.exists():
        return stats

    name_json = load_json_with_fallback(name_json_path)
    name_records = normalize_name_records(name_json)
    version = compute_version()
    replaced = replace_version_placeholders(name_records, version)
    apply_rename_rules(ttf_json, name_records, version)

    stats["enabled"] = 1
    stats["name_records_applied"] = len(name_records)
    stats["version_replaced_count"] = replaced
    return stats


def _is_nonzero_pair_value(value: Any) -> bool:
    """Summary: Check whether a kerning matrix value is non-zero.

    Args:
        value: Pair adjustment value from otfcc JSON matrix.

    Returns:
        bool: True when value has a non-zero adjustment.

    Example:
        _is_nonzero_pair_value(-20)
    """

    if isinstance(value, (int, float)):
        return int(value) != 0
    if isinstance(value, dict):
        for sub_value in value.values():
            if _is_nonzero_pair_value(sub_value):
                return True
        return False
    if isinstance(value, list):
        return any(_is_nonzero_pair_value(item) for item in value)
    return False


def _count_nonzero_in_row(matrix: List[Any], row_index: int) -> int:
    """Summary: Count non-zero values in one kerning matrix row."""

    if row_index < 0 or row_index >= len(matrix):
        return 0
    row = matrix[row_index]
    if not isinstance(row, list):
        return 0
    return sum(1 for value in row if _is_nonzero_pair_value(value))


def _count_nonzero_in_col(matrix: List[Any], col_index: int) -> int:
    """Summary: Count non-zero values in one kerning matrix column."""

    if col_index < 0:
        return 0
    total = 0
    for row in matrix:
        if not isinstance(row, list):
            continue
        if col_index >= len(row):
            continue
        if _is_nonzero_pair_value(row[col_index]):
            total += 1
    return total


def copy_kern_x_to_i(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Copy kern rules from X to I for both left and right sides.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Copy statistics.

    Example:
        copy_kern_x_to_i({"GPOS": {}})
    """

    stats = {
        "x_left_rules_found": 0,
        "x_right_rules_found": 0,
        "i_left_rules_added_or_updated": 0,
        "i_right_rules_added_or_updated": 0,
        "skipped_conflicts": 0,
    }

    gpos = ttf_json.get("GPOS", {})
    if not isinstance(gpos, dict):
        return stats

    lookups = gpos.get("lookups", {})
    features = gpos.get("features", {})
    if not isinstance(lookups, dict) or not isinstance(features, dict):
        return stats

    kern_lookup_names = features.get("kern")
    if not isinstance(kern_lookup_names, list):
        kern_lookup_names = [name for name, lookup in lookups.items() if isinstance(lookup, dict) and lookup.get("type") == "gpos_pair"]

    for lookup_name in kern_lookup_names:
        lookup = lookups.get(lookup_name)
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_pair":
            continue
        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue

        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue
            first = subtable.get("first")
            second = subtable.get("second")
            matrix = subtable.get("matrix")
            if not isinstance(first, dict) or not isinstance(second, dict) or not isinstance(matrix, list):
                continue

            x_first_class = first.get("X")
            if isinstance(x_first_class, int):
                left_rules = _count_nonzero_in_row(matrix, x_first_class)
                stats["x_left_rules_found"] += left_rules
                if first.get("I") != x_first_class:
                    first["I"] = x_first_class
                    stats["i_left_rules_added_or_updated"] += left_rules

            x_second_class = second.get("X")
            if isinstance(x_second_class, int):
                right_rules = _count_nonzero_in_col(matrix, x_second_class)
                stats["x_right_rules_found"] += right_rules
                if second.get("I") != x_second_class:
                    second["I"] = x_second_class
                    stats["i_right_rules_added_or_updated"] += right_rules

    return stats


def copy_kern_t_left_only_to_j(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Copy kern rules from T-left to J-left only.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Copy statistics.

    Example:
        copy_kern_t_left_only_to_j({"GPOS": {}})
    """

    stats = {
        "t_left_rules_found": 0,
        "j_left_rules_added_or_updated": 0,
        "j_right_rules_preserved": 0,
        "skipped_conflicts": 0,
    }

    gpos = ttf_json.get("GPOS", {})
    if not isinstance(gpos, dict):
        return stats

    lookups = gpos.get("lookups", {})
    features = gpos.get("features", {})
    if not isinstance(lookups, dict) or not isinstance(features, dict):
        return stats

    kern_lookup_names = features.get("kern")
    if not isinstance(kern_lookup_names, list):
        kern_lookup_names = [name for name, lookup in lookups.items() if isinstance(lookup, dict) and lookup.get("type") == "gpos_pair"]

    for lookup_name in kern_lookup_names:
        lookup = lookups.get(lookup_name)
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_pair":
            continue
        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue

        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue
            first = subtable.get("first")
            second = subtable.get("second")
            matrix = subtable.get("matrix")
            if not isinstance(first, dict) or not isinstance(second, dict) or not isinstance(matrix, list):
                continue

            # Keep existing J-right kerning intact.
            j_second_class = second.get("J")
            if isinstance(j_second_class, int):
                stats["j_right_rules_preserved"] += _count_nonzero_in_col(matrix, j_second_class)

            t_first_class = first.get("T")
            if not isinstance(t_first_class, int):
                continue

            left_rules = _count_nonzero_in_row(matrix, t_first_class)
            stats["t_left_rules_found"] += left_rules
            if first.get("J") != t_first_class:
                first["J"] = t_first_class
                stats["j_left_rules_added_or_updated"] += left_rules

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
            elif isinstance(x, list) and x:
                head = x[0]
                if isinstance(head, (int, float)):
                    xs.append(int(head))
            if isinstance(y, (int, float)):
                ys.append(int(y))
            elif isinstance(y, list) and y:
                head = y[0]
                if isinstance(head, (int, float)):
                    ys.append(int(head))
    if not xs or not ys:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def _set_base_anchor(base: Dict[str, Any], anchor_name: str, x: int, y: int) -> bool:
    """Summary: Set base anchor value and report whether it changed."""

    new = {"x": int(x), "y": int(y)}
    if base.get(anchor_name) == new:
        return False
    base[anchor_name] = new
    return True


def fix_uni0358(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Fix uni0358 mark/base anchors with lowercase-priority baseline.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Fix stats.

    Example:
        fix_uni0358({"GDEF": {}, "GPOS": {}, "glyf": {}})
    """

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
    _, lower_o_right_x, _, lower_o_top_y = lower_o_bounds
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

    upper_o_glyphs = [
        "O",
        "Oacute",
        "Ograve",
        "Ocircumflex",
        "uni01D1",
        "Omacron",
        "Obreve",
        "Ohungarumlaut",
    ]
    lower_o_glyphs = [
        "o",
        "oacute",
        "ograve",
        "ocircumflex",
        "uni01D2",
        "omacron",
        "obreve",
        "ohungarumlaut",
    ]

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

            o_base = bases.get("O")
            if not isinstance(o_base, dict):
                continue

            source_class = None
            o_anchor = None
            for cls in ("anchor4", "anchor2"):
                anchor = o_base.get(cls)
                if _valid_anchor(anchor):
                    source_class = cls
                    o_anchor = anchor
                    break
            if source_class is None or o_anchor is None:
                continue

            has_upper = any(isinstance(bases.get(g), dict) for g in upper_o_glyphs)
            has_lower = any(isinstance(bases.get(g), dict) for g in lower_o_glyphs)
            if not has_upper and not has_lower:
                continue

            # Lowercase priority: for o͘ we derive mark anchor from lowercase geometry first.
            # This keeps o + uni0358 from floating too high when O/o heights differ.
            lower_o_base = bases.get("o")
            if has_lower and isinstance(lower_o_base, dict):
                lower_src = lower_o_base.get(source_class)
                if _valid_anchor(lower_src):
                    ref_anchor_x = int(lower_src["x"])
                    ref_anchor_y = int(lower_src["y"])
                    ref_right_x = lower_o_right_x
                    ref_top_y = lower_o_top_y
                else:
                    ref_anchor_x = int(o_anchor["x"])
                    ref_anchor_y = int(o_anchor["y"])
                    ref_right_x = o_right_x
                    ref_top_y = o_top_y
            else:
                ref_anchor_x = int(o_anchor["x"])
                ref_anchor_y = int(o_anchor["y"])
                ref_right_x = o_right_x
                ref_top_y = o_top_y

            target_class = "anchor5"
            mark_x = ref_anchor_x + uni0358_left_x - ref_right_x
            mark_y = ref_anchor_y + uni0358_bottom_y - ref_top_y
            new_mark = {"class": target_class, "x": int(mark_x), "y": int(mark_y)}
            if marks.get("uni0358") != new_mark:
                marks["uni0358"] = new_mark
                stats["mark_entries_updated"] += 1

            upper_base_x = o_right_x + mark_x - uni0358_left_x
            upper_base_y = o_top_y + mark_y - uni0358_bottom_y
            for glyph_name in upper_o_glyphs:
                base = bases.get(glyph_name)
                if isinstance(base, dict) and _set_base_anchor(base, target_class, upper_base_x, upper_base_y):
                    stats["base_anchor_updates"] += 1

            lower_base_x = lower_o_right_x + mark_x - uni0358_left_x
            lower_base_y = lower_o_top_y + mark_y - uni0358_bottom_y
            for glyph_name in lower_o_glyphs:
                base = bases.get(glyph_name)
                if isinstance(base, dict) and _set_base_anchor(base, target_class, lower_base_x, lower_base_y):
                    stats["base_anchor_updates"] += 1

            stats["subtables_touched"] += 1

    return stats


def fix_uni030d(ttf_json: Dict[str, Any]) -> Dict[str, int]:
    """Summary: Ensure uni030D is a valid mark with GPOS mark entries.

    Args:
        ttf_json: Parsed otfcc JSON.

    Returns:
        Dict[str, int]: Stats for class/mark updates.
    """

    stats = {
        "class_updates": 0,
        "mark_entries_updated": 0,
        "subtables_touched": 0,
        "base_anchor_updates": 0,
    }

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
    uni0358_bounds = _glyph_bounds(glyf.get("uni0358", {}))
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

            if lookup.get("type") != "gpos_mark_to_mark" or uni0358_bounds is None:
                continue

            bases = subtable.get("bases")
            if not isinstance(bases, dict):
                continue

            uni0358_base = bases.get("uni0358")
            if not isinstance(uni0358_base, dict):
                uni0358_base = {}
                bases["uni0358"] = uni0358_base

            target_x = (uni0358_bounds[0] + uni0358_bounds[1]) // 2
            target_y = uni0358_bounds[3]

            src_base_entry = bases.get(src_mark)
            if isinstance(src_base_entry, dict):
                src_anchor = src_base_entry.get(cls)
                if _valid_anchor(src_anchor) and src_bounds is not None:
                    src_cx = (src_bounds[0] + src_bounds[1]) // 2
                    src_top = src_bounds[3]
                    target_x += int(src_anchor["x"]) - src_cx
                    target_y += int(src_anchor["y"]) - src_top

            # Optical tweak for o̍͘ / O̍͘:
            # move the stacked uni030D slightly left and higher on uni0358.
            target_x += UNI030D_ON_UNI0358_X_SHIFT
            target_y += UNI030D_ON_UNI0358_Y_SHIFT

            new_base_anchor = {"x": int(target_x), "y": int(target_y)}
            if uni0358_base.get(cls) != new_base_anchor:
                uni0358_base[cls] = new_base_anchor
                stats["base_anchor_updates"] += 1
                stats["subtables_touched"] += 1

    return stats


def apply_anchor_rules_from_json(ttf_json: Dict[str, Any], anchor_rules_json: Path) -> Dict[str, int]:
    """Summary: Patch mark-to-base anchors from a JSON rules file.

    Args:
        ttf_json: Parsed otfcc JSON.
        anchor_rules_json: Anchor JSON path.

    Returns:
        Dict[str, int]: Stats for patched glyphs/anchors/lookups.

    Example:
        apply_anchor_rules_from_json({}, Path("src/json/fonttool_fix_anchor_rules.json"))
    """

    stats = {
        "enabled": 0,
        "glyphs_updated": 0,
        "anchors_updated": 0,
        "lookups_touched": 0,
    }
    if not anchor_rules_json.exists():
        return stats

    raw = json.loads(anchor_rules_json.read_text(encoding="utf-8"))
    glyph_anchors = raw.get("glyph_anchors") if isinstance(raw, dict) else None
    if not isinstance(glyph_anchors, dict) or not glyph_anchors:
        return stats

    gpos = ttf_json.get("GPOS", {})
    lookups = gpos.get("lookups", {}) if isinstance(gpos, dict) else {}
    if not isinstance(lookups, dict):
        return stats

    touched_glyphs: set[str] = set()
    touched_lookups: set[str] = set()
    for lookup_name, lookup in lookups.items():
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_mark_to_base":
            continue
        subtables = lookup.get("subtables")
        if not isinstance(subtables, list):
            continue
        lookup_touched = False
        for subtable in subtables:
            if not isinstance(subtable, dict):
                continue
            bases = subtable.get("bases")
            if not isinstance(bases, dict):
                continue
            subtable_touched = False
            for glyph_name, anchors in glyph_anchors.items():
                if glyph_name not in bases or not isinstance(anchors, dict):
                    continue
                base_obj = bases.get(glyph_name)
                if not isinstance(base_obj, dict):
                    continue
                glyph_touched = False
                for anchor_name, anchor_value in anchors.items():
                    if not isinstance(anchor_name, str) or not isinstance(anchor_value, dict):
                        continue
                    x = anchor_value.get("x")
                    y = anchor_value.get("y")
                    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                        continue
                    new_anchor = {"x": int(x), "y": int(y)}
                    if base_obj.get(anchor_name) != new_anchor:
                        base_obj[anchor_name] = new_anchor
                        stats["anchors_updated"] += 1
                        glyph_touched = True
                        subtable_touched = True
                if glyph_touched:
                    touched_glyphs.add(glyph_name)
            if subtable_touched:
                lookup_touched = True
        if lookup_touched:
            touched_lookups.add(lookup_name)

    if stats["anchors_updated"] > 0:
        stats["enabled"] = 1
    stats["glyphs_updated"] = len(touched_glyphs)
    stats["lookups_touched"] = len(touched_lookups)
    return stats


def apply_json_fixes(
    data: Dict[str, Any],
    rules_json_path: Path,
    name_json_path: Path,
    anchor_rules_json_path: Path,
    enable_copy_kern_x_to_i: bool,
    enable_copy_kern_t_left_to_j: bool,
) -> Tuple[
    List[Tuple[int, str]],
    List[int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
    Dict[str, int],
]:
    """Summary: Apply cmap, GDEF, GPOS, and GSUB fixes to otfcc JSON.

    Args:
        data: Parsed otfcc JSON.
        rules_json_path: Path to additional GSUB rules JSON.
        name_json_path: Path to name table JSON.
        anchor_rules_json_path: Path to anchor rules JSON.
        enable_copy_kern_x_to_i: Whether to apply X->I kerning copy.
        enable_copy_kern_t_left_to_j: Whether to apply T-left->J-left kerning copy.

    Returns:
        tuple[
            list[tuple[int, str]],
            list[int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
            dict[str, int],
        ]:
            Added cmap entries, missing codepoints, uni0358 stats, ccmp stats,
            dotted-circle stats, uni030D stats, rename stats, X->I kern stats,
            T->J kern stats, and anchor patch stats.

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
    rename_stats = apply_name_json_rename(data, name_json_path)
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
    kern_copy_stats = {
        "x_left_rules_found": 0,
        "x_right_rules_found": 0,
        "i_left_rules_added_or_updated": 0,
        "i_right_rules_added_or_updated": 0,
        "skipped_conflicts": 0,
    }
    if enable_copy_kern_x_to_i:
        kern_copy_stats = copy_kern_x_to_i(data)
    kern_t_to_j_stats = {
        "t_left_rules_found": 0,
        "j_left_rules_added_or_updated": 0,
        "j_right_rules_preserved": 0,
        "skipped_conflicts": 0,
    }
    if enable_copy_kern_t_left_to_j:
        kern_t_to_j_stats = copy_kern_t_left_only_to_j(data)
    anchor_patch_stats = apply_anchor_rules_from_json(data, anchor_rules_json_path)
    return (
        added,
        missing,
        uni0358_stats,
        ccmp_stats,
        dotted_circle_stats,
        uni030d_stats,
        rename_stats,
        kern_copy_stats,
        kern_t_to_j_stats,
        anchor_patch_stats,
    )


def fix_stat_linked_bold(font: TTFont) -> Dict[str, int]:
    """Summary: Patch selected STAT axis values to linked-bold entries.

    Args:
        font: Mutable TTFont object.

    Returns:
        Dict[str, int]: Stats for found/updated/already-ok entries.

    Example:
        fix_stat_linked_bold(TTFont("out.ttf"))
    """

    stats = {
        "targets_found": 0,
        "entries_updated": 0,
        "entries_already_ok": 0,
        "stat_missing": 0,
    }
    if "STAT" not in font:
        stats["stat_missing"] = 1
        return stats

    stat_table = font["STAT"].table
    axis_value_array = getattr(stat_table, "AxisValueArray", None)
    axis_values = getattr(axis_value_array, "AxisValue", None)
    if not isinstance(axis_values, list):
        stats["stat_missing"] = 1
        return stats

    target_map = {300.0: 700.0, 500.0: 700.0, 600.0: 700.0}
    for axis_value in axis_values:
        value = getattr(axis_value, "Value", None)
        if value is None:
            continue
        value_float = float(value)
        if value_float not in target_map:
            continue
        stats["targets_found"] += 1
        linked_value = target_map[value_float]
        current_format = getattr(axis_value, "Format", None)
        current_linked = getattr(axis_value, "LinkedValue", None)
        if current_format == 3 and current_linked is not None and float(current_linked) == linked_value:
            stats["entries_already_ok"] += 1
            continue
        axis_value.Format = 3
        axis_value.LinkedValue = linked_value
        stats["entries_updated"] += 1

    return stats


def _get_feature_records(font: TTFont) -> List[Any]:
    """Summary: Get GPOS feature records from a font."""

    if "GPOS" not in font:
        return []
    gpos_table = font["GPOS"].table
    feature_list = getattr(gpos_table, "FeatureList", None)
    records = getattr(feature_list, "FeatureRecord", None)
    return list(records) if isinstance(records, list) else []


def _get_lookup_records(font: TTFont) -> List[Any]:
    """Summary: Get GPOS lookups from a font."""

    if "GPOS" not in font:
        return []
    gpos_table = font["GPOS"].table
    lookup_list = getattr(gpos_table, "LookupList", None)
    lookups = getattr(lookup_list, "Lookup", None)
    return list(lookups) if isinstance(lookups, list) else []


def _feature_tag_map(records: List[Any]) -> Dict[str, Tuple[int, Any]]:
    """Summary: Map feature tag to first matching feature record."""

    mapping: Dict[str, Tuple[int, Any]] = {}
    for index, record in enumerate(records):
        tag = getattr(record, "FeatureTag", None)
        if isinstance(tag, str) and tag not in mapping:
            mapping[tag] = (index, record)
    return mapping


def _langsys_feature_tags(langsys: Any, feature_records: List[Any]) -> List[str]:
    """Summary: Read feature tags referenced by one LangSys object."""

    indices = getattr(langsys, "FeatureIndex", None)
    if not isinstance(indices, list):
        return []
    tags: List[str] = []
    for index in indices:
        if isinstance(index, int) and 0 <= index < len(feature_records):
            tag = getattr(feature_records[index], "FeatureTag", None)
            if isinstance(tag, str):
                tags.append(tag)
    return tags


def _langsys_req_feature_tag(langsys: Any, feature_records: List[Any]) -> str | None:
    """Summary: Read required feature tag for one LangSys object."""

    req_index = getattr(langsys, "ReqFeatureIndex", None)
    if not isinstance(req_index, int) or req_index in (-1, 0xFFFF):
        return None
    if 0 <= req_index < len(feature_records):
        tag = getattr(feature_records[req_index], "FeatureTag", None)
        if isinstance(tag, str):
            return tag
    return None


def merge_source_kern_into_patched_gpos(source_font: TTFont, target_font: TTFont) -> Dict[str, int]:
    """Summary: Merge source kern PairPos with rebuilt variable mark/mkmk GPOS.

    Args:
        source_font: Original source variable font containing legacy kern.
        target_font: Mutable output font already containing rebuilt GPOS.

    Returns:
        Dict[str, int]: Merge statistics.

    Example:
        merge_source_kern_into_patched_gpos(TTFont("src.ttf"), TTFont("out.ttf"))
    """

    stats = {
        "enabled": 0,
        "source_kern_lookups_found": 0,
        "kern_lookups_merged": 0,
        "features_updated": 0,
        "preserved_variable_gpos": 1,
    }
    if "GPOS" not in source_font or "GPOS" not in target_font:
        return stats

    source_gpos_table = source_font["GPOS"].table
    target_gpos_table = target_font["GPOS"].table
    source_feature_records = _get_feature_records(source_font)
    target_feature_records = _get_feature_records(target_font)
    source_lookup_records = _get_lookup_records(source_font)
    target_lookup_records = _get_lookup_records(target_font)
    if not source_feature_records or not target_feature_records:
        return stats

    source_feature_map = _feature_tag_map(source_feature_records)
    target_feature_map = _feature_tag_map(target_feature_records)
    replace_tags = {"abvm", "blwm", "mark", "mkmk"}
    replace_available = {tag for tag in replace_tags if tag in target_feature_map}

    selected_specs: List[Tuple[str, int, str, Any]] = []
    for source_index, source_record in enumerate(source_feature_records):
        feature_tag = getattr(source_record, "FeatureTag", None)
        if not isinstance(feature_tag, str):
            continue
        if feature_tag in replace_available:
            continue
        selected_specs.append(("source", source_index, feature_tag, source_record))

    for target_index, target_record in enumerate(target_feature_records):
        feature_tag = getattr(target_record, "FeatureTag", None)
        if not isinstance(feature_tag, str) or feature_tag not in replace_tags:
            continue
        selected_specs.append(("target", target_index, feature_tag, target_record))

    merged_gpos = copy.deepcopy(source_font["GPOS"])
    merged_table = merged_gpos.table
    new_lookups: List[Any] = []
    new_feature_records: List[Any] = []
    lookup_index_map: Dict[Tuple[str, int], int] = {}
    new_feature_index_by_tag: Dict[str, int] = {}

    for origin, _feature_index, feature_tag, feature_record in selected_specs:
        lookup_source = source_lookup_records if origin == "source" else target_lookup_records
        cloned_feature_record = copy.deepcopy(feature_record)
        new_lookup_indices: List[int] = []
        lookup_indices = getattr(feature_record.Feature, "LookupListIndex", [])
        for lookup_index in lookup_indices:
            if not isinstance(lookup_index, int):
                continue
            key = (origin, lookup_index)
            if key not in lookup_index_map:
                if lookup_index < 0 or lookup_index >= len(lookup_source):
                    continue
                lookup_index_map[key] = len(new_lookups)
                new_lookups.append(copy.deepcopy(lookup_source[lookup_index]))
            new_lookup_indices.append(lookup_index_map[key])
        cloned_feature_record.Feature.LookupListIndex = new_lookup_indices
        cloned_feature_record.Feature.LookupCount = len(new_lookup_indices)
        if feature_tag == "kern":
            stats["source_kern_lookups_found"] += len(new_lookup_indices)
            stats["kern_lookups_merged"] = len(new_lookup_indices)
        new_feature_index_by_tag[feature_tag] = len(new_feature_records)
        new_feature_records.append(cloned_feature_record)

    merged_table.LookupList.Lookup = new_lookups
    merged_table.LookupList.LookupCount = len(new_lookups)
    merged_table.FeatureList.FeatureRecord = new_feature_records
    merged_table.FeatureList.FeatureCount = len(new_feature_records)
    stats["features_updated"] = len(new_feature_records)

    source_script_list = getattr(source_gpos_table, "ScriptList", None)
    target_script_list = getattr(target_gpos_table, "ScriptList", None)
    source_script_records = list(getattr(source_script_list, "ScriptRecord", []) or [])
    target_script_records = list(getattr(target_script_list, "ScriptRecord", []) or [])
    target_script_map = {getattr(record, "ScriptTag", ""): record for record in target_script_records}

    merged_script_records: List[Any] = []
    seen_script_tags: set[str] = set()

    def merge_langsys(base_langsys: Any, other_langsys: Any | None, base_features: List[Any], other_features: List[Any]) -> Any:
        if base_langsys is None and other_langsys is None:
            return None
        langsys = copy.deepcopy(base_langsys if base_langsys is not None else other_langsys)
        source_tags = _langsys_feature_tags(base_langsys, base_features) if base_langsys is not None else []
        other_tags = _langsys_feature_tags(other_langsys, other_features) if other_langsys is not None else []
        merged_tags = source_tags + [tag for tag in other_tags if tag not in source_tags]
        mapped_indices = [new_feature_index_by_tag[tag] for tag in merged_tags if tag in new_feature_index_by_tag]
        langsys.FeatureIndex = mapped_indices
        langsys.FeatureCount = len(mapped_indices)
        req_tag = _langsys_req_feature_tag(base_langsys, base_features) if base_langsys is not None else None
        if req_tag is None and other_langsys is not None:
            req_tag = _langsys_req_feature_tag(other_langsys, other_features)
        langsys.ReqFeatureIndex = new_feature_index_by_tag.get(req_tag, 0xFFFF) if req_tag else 0xFFFF
        return langsys

    for source_script_record in source_script_records:
        script_tag = getattr(source_script_record, "ScriptTag", "")
        if not isinstance(script_tag, str):
            continue
        seen_script_tags.add(script_tag)
        merged_script_record = copy.deepcopy(source_script_record)
        target_script_record = target_script_map.get(script_tag)
        target_script = getattr(target_script_record, "Script", None) if target_script_record is not None else None
        source_script = source_script_record.Script
        merged_script_record.Script.DefaultLangSys = merge_langsys(
            getattr(source_script, "DefaultLangSys", None),
            getattr(target_script, "DefaultLangSys", None),
            source_feature_records,
            target_feature_records,
        )
        source_lang_map = {getattr(record, "LangSysTag", ""): record for record in getattr(source_script, "LangSysRecord", []) or []}
        target_lang_map = {getattr(record, "LangSysTag", ""): record for record in getattr(target_script, "LangSysRecord", []) or []} if target_script is not None else {}
        merged_langsys_records: List[Any] = []
        seen_lang_tags: set[str] = set()
        for lang_tag, source_lang_record in source_lang_map.items():
            if not isinstance(lang_tag, str):
                continue
            seen_lang_tags.add(lang_tag)
            merged_lang_record = copy.deepcopy(source_lang_record)
            target_lang_record = target_lang_map.get(lang_tag)
            merged_lang_record.LangSys = merge_langsys(
                source_lang_record.LangSys,
                target_lang_record.LangSys if target_lang_record is not None else None,
                source_feature_records,
                target_feature_records,
            )
            merged_langsys_records.append(merged_lang_record)
        for lang_tag, target_lang_record in target_lang_map.items():
            if not isinstance(lang_tag, str) or lang_tag in seen_lang_tags:
                continue
            merged_lang_record = copy.deepcopy(target_lang_record)
            merged_lang_record.LangSys = merge_langsys(
                None,
                target_lang_record.LangSys,
                source_feature_records,
                target_feature_records,
            )
            merged_langsys_records.append(merged_lang_record)
        merged_script_record.Script.LangSysRecord = merged_langsys_records
        merged_script_record.Script.LangSysCount = len(merged_langsys_records)
        merged_script_records.append(merged_script_record)

    for target_script_record in target_script_records:
        script_tag = getattr(target_script_record, "ScriptTag", "")
        if not isinstance(script_tag, str) or script_tag in seen_script_tags:
            continue
        merged_script_record = copy.deepcopy(target_script_record)
        target_script = target_script_record.Script
        merged_script_record.Script.DefaultLangSys = merge_langsys(
            None,
            getattr(target_script, "DefaultLangSys", None),
            source_feature_records,
            target_feature_records,
        )
        merged_langsys_records = []
        for target_lang_record in getattr(target_script, "LangSysRecord", []) or []:
            merged_lang_record = copy.deepcopy(target_lang_record)
            merged_lang_record.LangSys = merge_langsys(
                None,
                target_lang_record.LangSys,
                source_feature_records,
                target_feature_records,
            )
            merged_langsys_records.append(merged_lang_record)
        merged_script_record.Script.LangSysRecord = merged_langsys_records
        merged_script_record.Script.LangSysCount = len(merged_langsys_records)
        merged_script_records.append(merged_script_record)

    merged_table.ScriptList.ScriptRecord = merged_script_records
    merged_table.ScriptList.ScriptCount = len(merged_script_records)
    target_font["GPOS"] = merged_gpos
    stats["enabled"] = 1
    return stats


def copy_patched_tables(
    original_font_path: Path,
    patched_font_path: Path,
    output_path: Path,
    enable_fix_stat_linked_bold: bool,
    merge_source_kern_from: Path | None,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Summary: Copy patched tables onto the original font and save output.

    Args:
        original_font_path: Original input font path.
        patched_font_path: Temporary rebuilt font path containing patched tables.
        output_path: Final output font path.
        enable_fix_stat_linked_bold: Whether to patch STAT linked bold entries.

    Returns:
        tuple[Dict[str, int], Dict[str, int]]: STAT linked bold stats and GPOS merge stats.

    Example:
        copy_patched_tables(Path("in.ttf"), Path("patched.ttf"), Path("out.ttf"), False, None)
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stat_fix_stats = {
        "targets_found": 0,
        "entries_updated": 0,
        "entries_already_ok": 0,
        "stat_missing": 0,
    }
    gpos_merge_stats = {
        "enabled": 0,
        "source_kern_lookups_found": 0,
        "kern_lookups_merged": 0,
        "features_updated": 0,
        "preserved_variable_gpos": 0,
    }
    with TTFont(str(original_font_path)) as original_font, TTFont(str(patched_font_path)) as patched_font:
        patched_table_tags = PATCHED_TABLE_TAGS
        if merge_source_kern_from is not None and merge_source_kern_from.exists():
            patched_table_tags = tuple(tag for tag in PATCHED_TABLE_TAGS if tag not in {"GDEF", "GPOS"})
            gpos_merge_stats["preserved_variable_gpos"] = 1
        for tag in patched_table_tags:
            if tag in patched_font:
                original_font[tag] = copy.deepcopy(patched_font[tag])
        if merge_source_kern_from is not None and merge_source_kern_from.exists():
            with TTFont(str(merge_source_kern_from)) as source_font:
                gpos_merge_stats = merge_source_kern_into_patched_gpos(source_font, original_font)
        if enable_fix_stat_linked_bold:
            stat_fix_stats = fix_stat_linked_bold(original_font)
        original_font.save(str(output_path))
    return stat_fix_stats, gpos_merge_stats


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
    name_json_path = Path(args.name_json).resolve()
    anchor_rules_json_path = Path(args.anchor_rules_json).resolve()
    merge_source_kern_from = Path(args.merge_source_kern_from).resolve() if args.merge_source_kern_from else None

    if not input_path.exists():
        eprint(f"Input file not found: {input_path}")
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        json_path = tmp_path / "font.json"
        patched_font_path = tmp_path / "patched_tables.ttf"

        run_cmd([args.otfccdump, "--pretty", str(input_path), "-o", str(json_path)])

        data = load_json_with_fallback(json_path)
        (
            added,
            missing,
            uni0358_stats,
            ccmp_stats,
            dotted_circle_stats,
            uni030d_stats,
            rename_stats,
            kern_copy_stats,
            kern_t_to_j_stats,
            anchor_patch_stats,
        ) = apply_json_fixes(
            data,
            rules_json_path,
            name_json_path,
            anchor_rules_json_path,
            args.copy_kern_x_to_i,
            args.copy_kern_t_left_to_j,
        )

        with json_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

        run_cmd([args.otfccbuild, str(json_path), "-o", str(patched_font_path)])
        stat_fix_stats, gpos_merge_stats = copy_patched_tables(
            input_path,
            patched_font_path,
            output_path,
            args.fix_stat_linked_bold,
            merge_source_kern_from,
        )

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
        f"subtables_touched={uni030d_stats['subtables_touched']}, "
        f"base_anchor_updates={uni030d_stats['base_anchor_updates']}"
    )
    print(
        "rename fix stats: "
        f"enabled={rename_stats['enabled']}, "
        f"name_records_applied={rename_stats['name_records_applied']}, "
        f"version_replaced_count={rename_stats['version_replaced_count']}"
    )
    print(
        "copy_kern_X_to_I stats: "
        f"enabled={1 if args.copy_kern_x_to_i else 0}, "
        f"x_left_rules_found={kern_copy_stats['x_left_rules_found']}, "
        f"x_right_rules_found={kern_copy_stats['x_right_rules_found']}, "
        f"i_left_rules_added_or_updated={kern_copy_stats['i_left_rules_added_or_updated']}, "
        f"i_right_rules_added_or_updated={kern_copy_stats['i_right_rules_added_or_updated']}, "
        f"skipped_conflicts={kern_copy_stats['skipped_conflicts']}"
    )
    print(
        "copy_kern_T_left_only_to_J stats: "
        f"enabled={1 if args.copy_kern_t_left_to_j else 0}, "
        f"t_left_rules_found={kern_t_to_j_stats['t_left_rules_found']}, "
        f"j_left_rules_added_or_updated={kern_t_to_j_stats['j_left_rules_added_or_updated']}, "
        f"j_right_rules_preserved={kern_t_to_j_stats['j_right_rules_preserved']}, "
        f"skipped_conflicts={kern_t_to_j_stats['skipped_conflicts']}"
    )
    print(
        "anchor patch stats: "
        f"enabled={anchor_patch_stats['enabled']}, "
        f"glyphs_updated={anchor_patch_stats['glyphs_updated']}, "
        f"anchors_updated={anchor_patch_stats['anchors_updated']}, "
        f"lookups_touched={anchor_patch_stats['lookups_touched']}"
    )
    print(
        "fix_stat_linked_bold stats: "
        f"enabled={1 if args.fix_stat_linked_bold else 0}, "
        f"targets_found={stat_fix_stats['targets_found']}, "
        f"entries_updated={stat_fix_stats['entries_updated']}, "
        f"entries_already_ok={stat_fix_stats['entries_already_ok']}, "
        f"stat_missing={stat_fix_stats['stat_missing']}"
    )
    print(
        "merge_source_kern stats: "
        f"enabled={gpos_merge_stats['enabled']}, "
        f"source_kern_lookups_found={gpos_merge_stats['source_kern_lookups_found']}, "
        f"kern_lookups_merged={gpos_merge_stats['kern_lookups_merged']}, "
        f"features_updated={gpos_merge_stats['features_updated']}, "
        f"preserved_variable_gpos={gpos_merge_stats['preserved_variable_gpos']}"
    )

    print(f"Done: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
