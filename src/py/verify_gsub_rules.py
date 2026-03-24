#!/usr/bin/env python3
"""Verify GSUB rule integrity and variable-font tables."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from fontTools.ttLib import TTFont


DEFAULT_FONT = Path("_output") / "ToneOZ-Quicksnow.ttf"
DEFAULT_RULES_JSON = Path(__file__).resolve().parents[1] / "json" / "fonttool_fix_cmap_rules.json"
SHAPING_CASES: List[Tuple[Tuple[int, ...], str]] = [
    ((0x00EA, 0x030C), "ecircumflex_uni030C"),
    ((0x00CA, 0x030C), "Ecircumflex_uni030C"),
]


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Example:
        python verify_gsub_rules.py -font _output/ToneOZ-Quicksnow.ttf
    """

    parser = argparse.ArgumentParser(description="Verify GSUB rules and variable-font tables.")
    parser.add_argument("-font", default=str(DEFAULT_FONT), help="Path to target TTF file")
    parser.add_argument("-rules-json", default=str(DEFAULT_RULES_JSON), help="Path to rules JSON")
    parser.add_argument("--otfccdump", default="otfccdump.exe", help="Path to otfccdump executable")
    return parser.parse_args()


def load_rules(path: Path) -> List[Dict[str, Any]]:
    """Summary: Load enabled ligature rules from JSON.

    Args:
        path: Rules JSON path.

    Returns:
        List[Dict[str, Any]]: Enabled rule objects.

    Example:
        load_rules(Path("src/json/fonttool_fix_cmap_rules.json"))
    """

    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        rules = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("gsub_ligature_rules"), list):
            rules = raw["gsub_ligature_rules"]
        elif isinstance(raw.get("rules"), list):
            rules = raw["rules"]
        else:
            return []
    else:
        return []

    enabled: List[Dict[str, Any]] = []
    for item in rules:
        if isinstance(item, dict) and item.get("enabled", True):
            enabled.append(item)
    return enabled


def dump_otfcc_json(font_path: Path, otfccdump: str) -> Dict[str, Any]:
    """Summary: Dump TTF to JSON through otfccdump.

    Args:
        font_path: Font file path.
        otfccdump: otfccdump executable.

    Returns:
        Dict[str, Any]: Parsed JSON object.

    Raises:
        RuntimeError: If otfccdump fails.

    Example:
        dump_otfcc_json(Path("_output/out.ttf"), "otfccdump.exe")
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "font.json"
        result = subprocess.run(
            [otfccdump, "--pretty", str(font_path), "-o", str(json_path)],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"otfccdump failed with exit code {result.returncode}")
        return json.loads(json_path.read_text(encoding="utf-8", errors="replace"))


def collect_ligature_substitutions(gsub: Dict[str, Any], feature_names: Iterable[str]) -> List[Dict[str, Any]]:
    """Summary: Collect ligature substitutions from specific GSUB features.

    Args:
        gsub: GSUB JSON object.
        feature_names: Feature names to traverse.

    Returns:
        List[Dict[str, Any]]: Flattened ligature substitutions.

    Example:
        collect_ligature_substitutions({"features": {}, "lookups": {}}, ["ccmp_00002"])
    """

    features = gsub.get("features", {}) if isinstance(gsub, dict) else {}
    lookups = gsub.get("lookups", {}) if isinstance(gsub, dict) else {}
    substitutions: List[Dict[str, Any]] = []

    for feature_name in feature_names:
        lookup_names = features.get(feature_name, [])
        if not isinstance(lookup_names, list):
            continue
        for lookup_name in lookup_names:
            lookup = lookups.get(lookup_name, {})
            if not isinstance(lookup, dict):
                continue
            if lookup.get("type") != "gsub_ligature":
                continue
            for subtable in lookup.get("subtables", []):
                if not isinstance(subtable, dict):
                    continue
                raw_subs = subtable.get("substitutions", [])
                if not isinstance(raw_subs, list):
                    continue
                substitutions.extend([item for item in raw_subs if isinstance(item, dict)])

    return substitutions


def build_case_variants(source: Sequence[str], glyph_order_set: set[str]) -> List[List[str]]:
    """Summary: Build candidate source sequences, including `.case` mark variants.

    Args:
        source: Original source glyph sequence.
        glyph_order_set: Glyph set in font.

    Returns:
        List[List[str]]: Candidate sequences including optional `.case` marks.

    Example:
        build_case_variants(["Ecircumflex", "uni030C"], {"uni030C.case"})
    """

    variants: List[List[str]] = [list(source)]
    for idx, glyph_name in enumerate(source):
        case_name = f"{glyph_name}.case"
        if case_name not in glyph_order_set:
            continue
        new_variants: List[List[str]] = []
        for item in variants:
            new_variants.append(item)
            replaced = list(item)
            replaced[idx] = case_name
            new_variants.append(replaced)
        variants = new_variants

    dedup: List[List[str]] = []
    seen: set[Tuple[str, ...]] = set()
    for item in variants:
        key = tuple(item)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(item)
    return dedup


def verify_shaping_cases(
    cmap: Dict[int, str], glyph_order_set: set[str], substitutions: List[Dict[str, Any]]
) -> List[str]:
    """Summary: Verify key input sequences can resolve to expected ligature targets.

    Args:
        cmap: Best cmap table (codepoint -> glyph name).
        glyph_order_set: Font glyph set.
        substitutions: Ligature substitution entries.

    Returns:
        List[str]: Failure messages, empty means pass.

    Example:
        verify_shaping_cases({0x00EA: "ecircumflex"}, set(), [])
    """

    failures: List[str] = []
    sub_map: Dict[Tuple[str, ...], str] = {}
    for item in substitutions:
        src = item.get("from")
        dst = item.get("to")
        if isinstance(src, list) and src and isinstance(dst, str):
            key = tuple(x for x in src if isinstance(x, str))
            if len(key) == len(src):
                sub_map[key] = dst

    for cps, expected_target in SHAPING_CASES:
        source = [cmap.get(cp) for cp in cps]
        if any(not x for x in source):
            failures.append(
                f"Shaping input missing in cmap: {[f'U+{cp:04X}' for cp in cps]} -> {source}"
            )
            continue

        candidate_sources = build_case_variants(source, glyph_order_set)
        hit = False
        for candidate in candidate_sources:
            if sub_map.get(tuple(candidate)) == expected_target:
                hit = True
                break

        if not hit:
            failures.append(
                "Shaping verification failed: "
                f"{[f'U+{cp:04X}' for cp in cps]} ({source}) "
                f"cannot resolve to {expected_target}"
            )

    return failures


def main() -> int:
    """Summary: Verify output font against GSUB and variable-font constraints.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()
    font_path = Path(args.font).resolve()
    rules_json_path = Path(args.rules_json).resolve()

    if not font_path.exists():
        print(f"Font not found: {font_path}", file=sys.stderr)
        return 2

    failures: List[str] = []

    # 1) Variable table verification
    with TTFont(str(font_path)) as tt:
        for tag in ("fvar", "gvar", "HVAR", "STAT"):
            if tag not in tt:
                failures.append(f"Missing variable table: {tag}")
        cmap = tt["cmap"].getBestCmap()
        glyph_order_set = set(tt.getGlyphOrder())

    # 2) GSUB structure verification using otfcc JSON (feature/lookup names)
    data = dump_otfcc_json(font_path, args.otfccdump)
    cmap_json = data.get("cmap", {}) if isinstance(data, dict) else {}
    gdef_json = data.get("GDEF", {}) if isinstance(data.get("GDEF", {}), dict) else {}
    gdef_classes = gdef_json.get("glyphClassDef", {}) if isinstance(gdef_json.get("glyphClassDef", {}), dict) else {}
    gpos_json = data.get("GPOS", {}) if isinstance(data.get("GPOS", {}), dict) else {}
    gpos_lookups = gpos_json.get("lookups", {}) if isinstance(gpos_json.get("lookups", {}), dict) else {}
    gsub = data.get("GSUB", {})
    features = gsub.get("features", {}) if isinstance(gsub, dict) else {}
    lookup_order = gsub.get("lookupOrder", []) if isinstance(gsub, dict) else []
    languages = gsub.get("languages", {}) if isinstance(gsub, dict) else {}
    lookups = gsub.get("lookups", {}) if isinstance(gsub, dict) else {}

    if "ccmp_00002" not in features:
        failures.append("Missing GSUB feature: ccmp_00002")
    if "ccmp_00003" not in features:
        failures.append("Missing GSUB feature: ccmp_00003")
    if "ccmp_00000" in features:
        failures.append("Unexpected GSUB feature: ccmp_00000")
    if "lookup_ccmp_6" not in lookups:
        failures.append("Missing GSUB lookup: lookup_ccmp_6")
    if isinstance(lookup_order, list) and "lookup_ccmp_6" not in lookup_order:
        failures.append("GSUB lookupOrder missing lookup_ccmp_6")

    for lang_key in ("DFLT_DFLT", "latn_DFLT"):
        lang_obj = languages.get(lang_key)
        if not isinstance(lang_obj, dict):
            failures.append(f"Missing GSUB language: {lang_key}")
            continue
        feats = lang_obj.get("features")
        if not isinstance(feats, list):
            failures.append(f"Invalid GSUB language features list: {lang_key}")
            continue
        if "ccmp_00002" not in feats and "ccmp_00003" not in feats:
            failures.append(f"Language {lang_key} not hooked to ccmp_00002/ccmp_00003")

    # 2.5) dotted-circle anchor chain verification
    if cmap_json.get(str(0x25CC)) != "uni25CC":
        failures.append("U+25CC cmap is missing or not mapped to uni25CC")
    if gdef_classes.get("uni25CC") != 1:
        failures.append("GDEF glyphClassDef for uni25CC must be 1 (base)")
    dotted_base_found = False
    for lookup in gpos_lookups.values():
        if not isinstance(lookup, dict) or lookup.get("type") != "gpos_mark_to_base":
            continue
        for subtable in lookup.get("subtables", []):
            if not isinstance(subtable, dict):
                continue
            bases = subtable.get("bases", {})
            if not isinstance(bases, dict):
                continue
            uni25cc_base = bases.get("uni25CC")
            if isinstance(uni25cc_base, dict) and any(
                isinstance(v, dict) and "x" in v and "y" in v for v in uni25cc_base.values()
            ):
                dotted_base_found = True
                break
        if dotted_base_found:
            break
    if not dotted_base_found:
        failures.append("GPOS mark-to-base is missing bases.uni25CC anchors")

    # 3) Rule presence verification
    rules = load_rules(rules_json_path)
    substitutions = collect_ligature_substitutions(gsub, ("ccmp_00002", "ccmp_00003"))

    for rule in rules:
        from_list = rule.get("from")
        to_glyph = rule.get("to")
        exists = False
        for sub in substitutions:
            if sub.get("from") == from_list and sub.get("to") == to_glyph:
                exists = True
                break
        if not exists:
            failures.append(f"Missing substitution rule: {from_list} -> {to_glyph}")

    # 4) Shaping-hit verification (including .case path)
    failures.extend(verify_shaping_cases(cmap, glyph_order_set, substitutions))

    if failures:
        print("Verification FAILED:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Verification PASSED.")
    print(f"Font: {font_path}")
    print(f"Rules JSON: {rules_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
