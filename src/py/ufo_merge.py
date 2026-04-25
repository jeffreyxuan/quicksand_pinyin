#!/usr/bin/env python3
"""Merge modified glyphs from SFD-derived UFOs back into a variable TTF."""

from __future__ import annotations

import argparse
from collections import deque
import json
import plistlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Set

from extract_sfd_anchors import extract_sfd_anchors


FONTFORGE_BIN = Path(r"C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe")
DEFAULT_TTFAUTOHINT = Path(r"C:\tool\ttfautohint\ttfautohint.exe")
REPO_ROOT = Path(__file__).resolve().parents[2]
VARWIDEUFO_PY = REPO_ROOT / "src" / "py" / "varwideufo" / "varwideufo.py"
FONTTOOL_FIX_CMAP_PY = REPO_ROOT / "src" / "py" / "fonttool_fix_cmap.py"
NAME_JSON_PATH = REPO_ROOT / "src" / "json" / "name_Quicksand-VariableFont_wght.json"
ANCHOR_RULES_JSON_PATH = REPO_ROOT / "src" / "json" / "fonttool_fix_anchor_rules.json"
KERN_RULES_JSON_PATH = REPO_ROOT / "src" / "json" / "fonttool_fix_kern_rules.json"
ANCHOR_DIR_NAME = "anchor"
GLYF_DIR_NAME = "glyf"
PROJECT_METADATA_FILENAME = "varwideufo_source.plist"
TMP_UFO_INPUT = REPO_ROOT / "_tmp" / "ufo_input"
TMP_UFO_OUTPUT = REPO_ROOT / "_tmp" / "ufo_output"
TMP_MERGED_TTF = REPO_ROOT / "_tmp" / "ufo_merge_intermediate.ttf"
DISABLED_ANCHOR_RULES_JSON_PATH = REPO_ROOT / "_tmp" / "__disabled_anchor_rules__.json"
AUTO_EXPAND_REFER_GLYPHS_DEFAULT = True

FONTFORGE_UFO_SCRIPT = r'''
import sys
import fontforge

if len(sys.argv) < 3:
    raise SystemExit("Usage: ff_ufo_export.py <input_sfd> <output_ufo>")

input_sfd = sys.argv[1]
output_ufo = sys.argv[2]

font = fontforge.open(input_sfd)
font.generate(output_ufo, "", ("round",))
font.close()
print(f"Done: {output_ufo}")
'''


def eprint(*args: object, **kwargs: object) -> None:
    """Summary: Print a message to stderr with 8-space indentation.

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
    indented_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.strip():
            indented_lines.append(f"        {line}")
        else:
            indented_lines.append(line)
    print("".join(indented_lines), end="", file=sys.stderr, **kwargs)


def parse_args() -> argparse.Namespace:
    """Summary: Parse command-line arguments for ufo_merge.py.

    Args:
        None

    Returns:
        argparse.Namespace: Parsed CLI arguments.

    Raises:
        SystemExit: If required CLI arguments are missing.

    Example:
        python ufo_merge.py -input src/ufo -with res/font.ttf -output _output/out.ttf
    """

    parser = argparse.ArgumentParser(
        description="Merge modified glyphs from SFD sources into a variable TTF."
    )
    parser.add_argument(
        "-input",
        required=True,
        help="Folder containing glyf_update.txt and a glyf subfolder with *.sfd files",
    )
    parser.add_argument("-with", dest="with_font", required=True, help="Base variable TTF file")
    parser.add_argument("-output", required=True, help="Output TTF path")
    parser.add_argument(
        "-fix_stat_linked_bold",
        action="store_true",
        help="Patch STAT linked bold entries: 300->700, 500->700, 600->700",
    )
    parser.add_argument("--autohint", action="store_true", help="Run ttfautohint on final output TTF")
    parser.add_argument(
        "--ttfautohint",
        default=str(DEFAULT_TTFAUTOHINT),
        help="Path to ttfautohint executable (used with --autohint)",
    )
    parser.set_defaults(auto_expand_refer_glyphs=AUTO_EXPAND_REFER_GLYPHS_DEFAULT)
    parser.add_argument(
        "--auto-expand-refer-glyphs",
        dest="auto_expand_refer_glyphs",
        action="store_true",
        help="Auto-include glyphs that reference listed glyphs via SFD Refer (recursive)",
    )
    parser.add_argument(
        "--no-auto-expand-refer-glyphs",
        dest="auto_expand_refer_glyphs",
        action="store_false",
        help="Disable auto-expanding SFD Refer dependencies and only use glyf_update.txt",
    )
    return parser.parse_args()


def ensure_clean_dir(path: Path) -> None:
    """Summary: Recreate a directory as an empty folder.

    Args:
        path: Directory path to recreate.

    Returns:
        None

    Example:
        ensure_clean_dir(Path("_tmp/ufo_input"))
    """

    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_sfd_inputs(input_dir: Path) -> List[Path]:
    """Summary: Find all SFD sources from the input folder.

    Args:
        input_dir: Root folder containing `glyf_update.txt` and `glyf/*.sfd`.

    Returns:
        List[Path]: Sorted list of matching SFD paths.

    Raises:
        ValueError: If no SFD files are found.

    Example:
        find_sfd_inputs(Path("src/ufo"))
    """

    sfd_dir = input_dir / GLYF_DIR_NAME
    if not sfd_dir.exists():
        sfd_dir = input_dir
    sfd_paths = sorted(path for path in sfd_dir.glob("*.sfd") if not path.stem.lower().endswith("_anchor"))
    if not sfd_paths:
        raise ValueError(f"No .sfd files found in {sfd_dir}")
    return sfd_paths


def resolve_glyph_update_path(input_dir: Path) -> Path:
    """Summary: Resolve the shared glyph update list path.

    Args:
        input_dir: Folder containing SFD inputs.

    Returns:
        Path: Path to glyf_update.txt.

    Raises:
        ValueError: If the list file does not exist.

    Example:
        resolve_glyph_update_path(Path("src/ufo"))
    """

    glyph_update_path = input_dir / "glyf_update.txt"
    if not glyph_update_path.exists():
        raise ValueError(f"Missing glyph update list: {glyph_update_path}")
    return glyph_update_path


def read_seed_modified_list(modified_list_path: Path) -> List[str]:
    """Summary: Read seed glyph names from glyf_update.txt.

    Args:
        modified_list_path: Path to glyf_update.txt.

    Returns:
        List[str]: Seed glyph names in file order without blank lines.

    Example:
        read_seed_modified_list(Path("src/ufo/glyf_update.txt"))
    """

    lines = modified_list_path.read_text(encoding="utf-8-sig").splitlines()
    glyph_names: List[str] = []
    seen: set[str] = set()
    for line in lines:
        glyph_name = line.strip()
        if not glyph_name or glyph_name in seen:
            continue
        seen.add(glyph_name)
        glyph_names.append(glyph_name)
    return glyph_names


def parse_sfd_refer_dependencies(sfd_path: Path) -> Dict[str, Set[str]]:
    """Summary: Parse one SFD and build reverse Refer dependency mapping.

    Args:
        sfd_path: Path to source SFD.

    Returns:
        Dict[str, Set[str]]: Mapping `base_glyph -> dependent glyphs`.

    Raises:
        ValueError: If a Refer line points to an encoding missing in the same SFD.

    Example:
        parse_sfd_refer_dependencies(Path("src/ufo/glyf/Quicksand-VariableFont_wght-W300.ufo.sfd"))
    """

    lines = sfd_path.read_text(encoding="utf-8").splitlines()
    glyph_by_encoding: Dict[int, str] = {}
    glyph_refer_encodings: Dict[str, Set[int]] = {}
    refer_reverse: Dict[str, Set[str]] = {}

    current_glyph: Optional[str] = None
    for line in lines:
        if line.startswith("StartChar: "):
            current_glyph = line.split(": ", 1)[1].strip()
            glyph_refer_encodings.setdefault(current_glyph, set())
            continue
        if line == "EndChar":
            current_glyph = None
            continue
        if current_glyph is None:
            continue
        if line.startswith("Encoding: "):
            parts = line.split(": ", 1)[1].split()
            if parts:
                encoding = int(parts[0])
                glyph_by_encoding[encoding] = current_glyph
            continue
        if line.startswith("Refer: "):
            parts = line.split()
            if len(parts) >= 2:
                refer_encoding = int(parts[1])
                glyph_refer_encodings[current_glyph].add(refer_encoding)

    for dependent_glyph, refer_encodings in glyph_refer_encodings.items():
        for refer_encoding in refer_encodings:
            base_glyph = glyph_by_encoding.get(refer_encoding)
            if base_glyph is None:
                raise ValueError(
                    f"Invalid Refer encoding {refer_encoding} in {sfd_path} for glyph {dependent_glyph}"
                )
            refer_reverse.setdefault(base_glyph, set()).add(dependent_glyph)
    return refer_reverse


def validate_refer_dependencies_consistency(
    sfd_paths: List[Path],
    seed_glyph_names: List[str],
) -> Dict[str, Set[str]]:
    """Summary: Validate Refer dependencies are identical across all SFD masters for reachable seed chains.

    Args:
        sfd_paths: Master SFD paths.
        seed_glyph_names: Root glyph names from glyf_update.txt used to scope validation.

    Returns:
        Dict[str, Set[str]]: Master-consistent reverse Refer mapping.

    Raises:
        ValueError: If any glyph Refer dependency set differs between masters.

    Example:
        validate_refer_dependencies_consistency([Path("W300.sfd"), Path("W700.sfd")], ["a"])
    """

    if not sfd_paths:
        return {}

    per_master_dependencies: Dict[Path, Dict[str, Set[str]]] = {
        sfd_path: parse_sfd_refer_dependencies(sfd_path) for sfd_path in sfd_paths
    }
    mismatch_lines: List[str] = []
    first_problem_glyph: Optional[str] = None
    first_problem_base: Optional[str] = None
    baseline_path = sfd_paths[0]
    baseline = per_master_dependencies[baseline_path]
    validated_reverse_dependencies: Dict[str, Set[str]] = {}
    pending: Deque[str] = deque(seed_glyph_names)
    visited: Set[str] = set()

    while pending:
        base_glyph = pending.popleft()
        if base_glyph in visited:
            continue
        visited.add(base_glyph)

        baseline_dependents = baseline.get(base_glyph, set())
        mismatch_found = False
        union_dependents: Set[str] = set(baseline_dependents)
        for sfd_path in sfd_paths[1:]:
            current_dependents = per_master_dependencies[sfd_path].get(base_glyph, set())
            union_dependents.update(current_dependents)
            if current_dependents != baseline_dependents:
                mismatch_found = True
                only_in_baseline = sorted(baseline_dependents - current_dependents)
                only_in_current = sorted(current_dependents - baseline_dependents)
                if first_problem_glyph is None:
                    first_candidates = only_in_baseline + only_in_current
                    if first_candidates:
                        first_problem_glyph = first_candidates[0]
                        first_problem_base = base_glyph
                mismatch_lines.append(
                    f"- base glyph {base_glyph!r} referenced_by mismatch: "
                    f"only_in_{baseline_path.name}({len(only_in_baseline)}): {only_in_baseline}; "
                    f"only_in_{sfd_path.name}({len(only_in_current)}): {only_in_current}"
                )

        for dependent in sorted(union_dependents):
            if dependent not in visited:
                pending.append(dependent)
        if not mismatch_found:
            validated_reverse_dependencies[base_glyph] = set(baseline_dependents)

    if mismatch_lines:
        first_problem_line = ""
        if first_problem_glyph is not None and first_problem_base is not None:
            first_problem_line = (
                f"First problematic glyph: {first_problem_glyph!r} "
                f"(in referenced_by of base glyph {first_problem_base!r}).\n"
            )
        raise ValueError(
            "Reverse Refer dependencies (which glyphs reference a base glyph) differ across masters.\n"
            f"Total mismatches: {len(mismatch_lines)}\n"
            + first_problem_line
            + "\n".join(mismatch_lines)
            + "\nNote: this does NOT mean the base glyph references those glyphs; it means those glyphs reference the base glyph."
        )

    return validated_reverse_dependencies


def expand_glyph_names_by_refer_dependencies(
    seed_glyph_names: List[str],
    refer_dependencies: Dict[str, Set[str]],
) -> List[str]:
    """Summary: Recursively expand glyph names by reverse Refer dependencies.

    Args:
        seed_glyph_names: Initial glyph names from glyf_update.txt.
        refer_dependencies: Mapping `base_glyph -> dependent glyphs`.

    Returns:
        List[str]: Expanded glyph list with deterministic order and no duplicates.

    Example:
        expand_glyph_names_by_refer_dependencies(["a"], {"a": {"amacron"}})
    """

    expanded: List[str] = list(seed_glyph_names)
    seen: Set[str] = set(seed_glyph_names)
    queue: Deque[str] = deque(seed_glyph_names)

    while queue:
        glyph_name = queue.popleft()
        for dependent in sorted(refer_dependencies.get(glyph_name, set())):
            if dependent in seen:
                continue
            seen.add(dependent)
            expanded.append(dependent)
            queue.append(dependent)

    return expanded


def read_modified_list(modified_list_path: Path, sfd_paths: List[Path], auto_expand_refer_glyphs: bool) -> List[str]:
    """Summary: Read glyph names from glyf_update.txt and optionally auto-expand Refer dependencies.

    Args:
        modified_list_path: Path to glyf_update.txt.
        sfd_paths: SFD master paths used for Refer dependency analysis.
        auto_expand_refer_glyphs: Whether to recursively include Refer dependents.

    Returns:
        List[str]: Glyph names in file order plus optional dependency expansion.

    Raises:
        ValueError: If Refer dependencies are inconsistent across masters.

    Example:
        read_modified_list(Path("src/ufo/glyf_update.txt"), [Path("W300.sfd"), Path("W700.sfd")], True)
    """

    seed_glyph_names = read_seed_modified_list(modified_list_path)
    if not auto_expand_refer_glyphs:
        return seed_glyph_names

    refer_dependencies = validate_refer_dependencies_consistency(sfd_paths, seed_glyph_names)
    return expand_glyph_names_by_refer_dependencies(seed_glyph_names, refer_dependencies)


def extract_weight_token(path: Path) -> Optional[str]:
    """Summary: Extract a W### token from a path stem.

    Args:
        path: Path whose stem may contain a weight token.

    Returns:
        Optional[str]: Weight token digits when found.

    Example:
        extract_weight_token(Path("ToneOZ-Quicksnow-W300_anchor.sfd"))
    """

    normalized_stem = path.stem.replace(".", "-").replace("_", "-")
    for part in normalized_stem.split("-"):
        upper_part = part.upper()
        if upper_part.startswith("W") and upper_part[1:].isdigit():
            return upper_part[1:]
    return None


def resolve_variable_anchor_master_paths(input_dir: Path) -> Dict[str, Path]:
    """Summary: Find variable anchor master SFDs for W300/W700.

    Args:
        input_dir: Root input directory.

    Returns:
        Dict[str, Path]: Mapping like {"300": path, "700": path} when present.

    Example:
        resolve_variable_anchor_master_paths(Path("src/ufo"))
    """

    anchor_dir = input_dir / ANCHOR_DIR_NAME
    if not anchor_dir.is_dir():
        return {}

    found: Dict[str, Path] = {}
    for path in sorted(anchor_dir.glob("*.sfd")):
        weight_token = extract_weight_token(path)
        if weight_token in {"300", "700"}:
            found[weight_token] = path
    return found


def find_matching_ufo_by_weight(project_dir: Path, weight_token: str) -> Path:
    """Summary: Find a master UFO directory whose name contains the target weight token.

    Args:
        project_dir: UFO project root directory.
        weight_token: Weight token such as "300" or "700".

    Returns:
        Path: Matching UFO directory.

    Raises:
        ValueError: If no matching UFO exists.

    Example:
        find_matching_ufo_by_weight(Path("_tmp/ufo_output"), "300")
    """

    matches = sorted(path for path in project_dir.glob("*.ufo") if f"W{weight_token}" in path.stem.upper())
    if not matches:
        raise ValueError(f"Matching UFO not found for W{weight_token} in {project_dir}")
    return matches[0]


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Summary: Pretty-print XML indentation in-place.

    Args:
        elem: XML element to indent.
        level: Current nesting depth.

    Returns:
        None

    Example:
        indent_xml(root)
    """

    indent = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent


def apply_anchor_rules_to_ufo(ufo_dir: Path, anchor_rules_json: Path) -> Dict[str, int]:
    """Summary: Apply anchor JSON to one UFO master by updating GLIF anchor elements.

    Args:
        ufo_dir: Target UFO directory.
        anchor_rules_json: JSON file exported from an anchor SFD.

    Returns:
        Dict[str, int]: Update stats.

    Raises:
        ValueError: If required UFO files are missing.

    Example:
        apply_anchor_rules_to_ufo(Path("_tmp/ufo_output/Font-W300.ufo"), Path("_tmp/W300_anchor.json"))
    """

    glyph_dir = ufo_dir / "glyphs"
    contents = load_contents_plist(glyph_dir)
    anchor_data = json.loads(anchor_rules_json.read_text(encoding="utf-8"))
    glyph_anchors = anchor_data.get("glyph_anchors", {})
    glyph_mark_anchors = anchor_data.get("glyph_mark_anchors", {})
    if not isinstance(glyph_anchors, dict) or not isinstance(glyph_mark_anchors, dict):
        raise ValueError(f"Invalid anchor rules json: {anchor_rules_json}")

    stats = {"glyphs_updated": 0, "anchors_updated": 0}
    all_glyph_names = sorted(set(glyph_anchors) | set(glyph_mark_anchors))
    for glyph_name in all_glyph_names:
        anchors = glyph_anchors.get(glyph_name, {})
        mark_anchors = glyph_mark_anchors.get(glyph_name, {})
        if glyph_name not in contents or (not isinstance(anchors, dict)) or (not isinstance(mark_anchors, dict)):
            continue
        glif_path = glyph_dir / contents[glyph_name]
        if not glif_path.exists():
            continue

        tree = ET.parse(glif_path)
        root = tree.getroot()
        old_anchor_elements = [child for child in list(root) if child.tag == "anchor"]
        for child in old_anchor_elements:
            root.remove(child)

        insert_index = 0
        for index, child in enumerate(list(root)):
            if child.tag in {"unicode", "advance"}:
                insert_index = index + 1

        combined_anchors = dict(anchors)
        combined_anchors.update(mark_anchors)
        for anchor_name in sorted(combined_anchors):
            anchor_value = combined_anchors[anchor_name]
            if not isinstance(anchor_value, dict):
                continue
            x = int(anchor_value["x"])
            y = int(anchor_value["y"])
            anchor_element = ET.Element("anchor", {"name": anchor_name, "x": str(x), "y": str(y)})
            root.insert(insert_index, anchor_element)
            insert_index += 1
            stats["anchors_updated"] += 1

        indent_xml(root)
        tree.write(glif_path, encoding="UTF-8", xml_declaration=True)
        stats["glyphs_updated"] += 1
    return stats


def update_project_metadata_skip_tags(project_dir: Path, skip_tags: List[str]) -> None:
    """Summary: Mark project metadata so varwideufo skips preserving selected source tables.

    Args:
        project_dir: UFO project root directory.
        skip_tags: Source table tags to skip preserving.

    Returns:
        None

    Example:
        update_project_metadata_skip_tags(Path("_tmp/ufo_output"), ["GDEF", "GPOS"])
    """

    metadata_path = project_dir / PROJECT_METADATA_FILENAME
    if not metadata_path.exists():
        return
    with metadata_path.open("rb") as handle:
        metadata = plistlib.load(handle)
    if not isinstance(metadata, dict):
        return
    metadata["skipPreserveTags"] = skip_tags
    with metadata_path.open("wb") as handle:
        plistlib.dump(metadata, handle, sort_keys=False)


def apply_variable_anchor_masters(input_dir: Path, project_dir: Path) -> bool:
    """Summary: Apply W300/W700 anchor masters to matching UFO masters before variable build.

    Args:
        input_dir: Root input directory.
        project_dir: UFO project root directory to patch.

    Returns:
        bool: True when variable anchor masters were applied.

    Example:
        apply_variable_anchor_masters(Path("src/ufo"), Path("_tmp/ufo_output"))
    """

    anchor_master_paths = resolve_variable_anchor_master_paths(input_dir)
    if not {"300", "700"}.issubset(anchor_master_paths):
        return False

    total_glyphs_updated = 0
    total_anchors_updated = 0
    with tempfile.TemporaryDirectory(prefix="ufo_anchor_masters_") as tmpdir:
        tmp_root = Path(tmpdir)
        for weight_token in ("300", "700"):
            anchor_sfd = anchor_master_paths[weight_token]
            anchor_json = tmp_root / f"W{weight_token}_anchors.json"
            extract_sfd_anchors(anchor_sfd, anchor_json)
            target_ufo = find_matching_ufo_by_weight(project_dir, weight_token)
            stats = apply_anchor_rules_to_ufo(target_ufo, anchor_json)
            total_glyphs_updated += stats["glyphs_updated"]
            total_anchors_updated += stats["anchors_updated"]

    update_project_metadata_skip_tags(project_dir, ["GDEF", "GPOS"])
    print(
        "variable anchor master stats: "
        f"enabled=1, glyphs_updated={total_glyphs_updated}, anchors_updated={total_anchors_updated}, "
        "skip_preserve_tags=GDEF,GPOS"
    )
    return True


def build_ufo_from_sfd(input_sfd: Path, output_ufo: Path) -> None:
    """Summary: Convert one SFD file to a UFO3 directory using FontForge.

    Args:
        input_sfd: Source SFD path.
        output_ufo: Target UFO directory path.

    Returns:
        None

    Raises:
        RuntimeError: If FontForge is missing or export fails.

    Example:
        build_ufo_from_sfd(Path("src/ufo/glyf/font.ufo.sfd"), Path("_tmp/ufo_input/font.ufo"))
    """

    if not FONTFORGE_BIN.exists():
        raise RuntimeError(f"FontForge not found: {FONTFORGE_BIN}")

    output_ufo.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as tmp:
        tmp.write(FONTFORGE_UFO_SCRIPT)
        ff_script_path = Path(tmp.name)

    try:
        cmd = [
            str(FONTFORGE_BIN),
            "-lang=py",
            "-script",
            str(ff_script_path),
            str(input_sfd),
            str(output_ufo),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        ff_script_path.unlink(missing_ok=True)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        raise RuntimeError(f"FontForge failed for {input_sfd} with exit code {result.returncode}")


def build_ufo_from_ttf(input_ttf: Path, output_dir: Path) -> None:
    """Summary: Convert a variable TTF to a UFO project via varwideufo.py.

    Args:
        input_ttf: Source variable TTF path.
        output_dir: Target UFO project directory.

    Returns:
        None

    Raises:
        RuntimeError: If varwideufo.py fails.

    Example:
        build_ufo_from_ttf(Path("res/font.ttf"), Path("_tmp/ufo_output"))
    """

    cmd = [sys.executable, str(VARWIDEUFO_PY), "-input", str(input_ttf), "-output", str(output_dir)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        raise RuntimeError(f"varwideufo.py failed while converting TTF to UFO: exit code {result.returncode}")


def load_contents_plist(glyph_dir: Path) -> Dict[str, str]:
    """Summary: Load glyph name to glif filename mapping from a UFO glyph folder.

    Args:
        glyph_dir: UFO glyph directory path.

    Returns:
        Dict[str, str]: Mapping from glyph name to GLIF file name.

    Raises:
        ValueError: If contents.plist is missing or invalid.

    Example:
        load_contents_plist(Path("_tmp/ufo_output/Font-W300.ufo/glyphs"))
    """

    contents_path = glyph_dir / "contents.plist"
    if not contents_path.exists():
        raise ValueError(f"Missing contents.plist in {glyph_dir}")
    with contents_path.open("rb") as handle:
        data = plistlib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid contents.plist in {glyph_dir}")
    return {str(key): str(value) for key, value in data.items()}


def write_contents_plist(glyph_dir: Path, contents: Dict[str, str]) -> None:
    """Summary: Write glyph name mapping back to contents.plist.

    Args:
        glyph_dir: UFO glyph directory path.
        contents: Glyph name to GLIF filename mapping.

    Returns:
        None

    Example:
        write_contents_plist(Path("_tmp/ufo_output/Font-W300.ufo/glyphs"), {"a": "a.glif"})
    """

    contents_path = glyph_dir / "contents.plist"
    with contents_path.open("wb") as handle:
        plistlib.dump(contents, handle, sort_keys=False)


def load_lib_plist(ufo_dir: Path) -> Dict[str, object]:
    """Summary: Load a UFO lib.plist file.

    Args:
        ufo_dir: UFO directory path.

    Returns:
        Dict[str, object]: Parsed lib data.

    Raises:
        ValueError: If lib.plist is missing or invalid.

    Example:
        load_lib_plist(Path("_tmp/ufo_output/Font-W300.ufo"))
    """

    lib_path = ufo_dir / "lib.plist"
    if not lib_path.exists():
        raise ValueError(f"Missing lib.plist in {ufo_dir}")
    with lib_path.open("rb") as handle:
        data = plistlib.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid lib.plist in {ufo_dir}")
    return data


def write_lib_plist(ufo_dir: Path, lib_data: Dict[str, object]) -> None:
    """Summary: Write data back to a UFO lib.plist file.

    Args:
        ufo_dir: UFO directory path.
        lib_data: Updated lib.plist data.

    Returns:
        None

    Example:
        write_lib_plist(Path("_tmp/ufo_output/Font-W300.ufo"), {"public.glyphOrder": ["a"]})
    """

    lib_path = ufo_dir / "lib.plist"
    with lib_path.open("wb") as handle:
        plistlib.dump(lib_data, handle, sort_keys=False)


def make_unique_glif_name(glyph_name: str, used_names: set[str]) -> str:
    """Summary: Generate a unique GLIF file name for a glyph.

    Args:
        glyph_name: Glyph name to convert into a file name.
        used_names: Existing lower-cased file names.

    Returns:
        str: Unique GLIF file name.

    Example:
        make_unique_glif_name("uni030D", {"a.glif"})
    """

    base_name = glyph_name.replace("/", "_")
    candidate = f"{base_name}.glif"
    if candidate.lower() not in used_names:
        used_names.add(candidate.lower())
        return candidate

    suffix = 1
    while True:
        candidate = f"{base_name}__{suffix}.glif"
        if candidate.lower() not in used_names:
            used_names.add(candidate.lower())
            return candidate
        suffix += 1


def add_glyph_to_lib_order(lib_data: Dict[str, object], glyph_name: str) -> None:
    """Summary: Ensure a glyph appears in public.glyphOrder.

    Args:
        lib_data: UFO lib.plist data.
        glyph_name: Glyph name to append when missing.

    Returns:
        None

    Example:
        add_glyph_to_lib_order({"public.glyphOrder": ["a"]}, "uni030D")
    """

    glyph_order = lib_data.get("public.glyphOrder")
    if isinstance(glyph_order, list):
        if glyph_name not in glyph_order:
            glyph_order.append(glyph_name)
    else:
        lib_data["public.glyphOrder"] = [glyph_name]


def copy_modified_glyphs(input_ufo: Path, output_ufo: Path, glyph_names: Iterable[str]) -> None:
    """Summary: Copy modified glyph GLIF files from one UFO to another.

    Args:
        input_ufo: UFO generated from the SFD source.
        output_ufo: UFO generated from the base variable TTF.
        glyph_names: Glyph names to copy.

    Returns:
        None

    Raises:
        ValueError: If glyph folders or glyph mappings are missing.

    Example:
        copy_modified_glyphs(Path("_tmp/ufo_input/A.ufo"), Path("_tmp/ufo_output/A.ufo"), ["a"])
    """

    input_glyph_dir = input_ufo / "glyphs"
    output_glyph_dir = output_ufo / "glyphs"
    if not input_glyph_dir.is_dir():
        raise ValueError(f"Missing input glyphs folder: {input_glyph_dir}")
    if not output_glyph_dir.is_dir():
        raise ValueError(f"Missing output glyphs folder: {output_glyph_dir}")

    input_contents = load_contents_plist(input_glyph_dir)
    output_contents = load_contents_plist(output_glyph_dir)
    output_lib = load_lib_plist(output_ufo)
    used_output_names = {file_name.lower() for file_name in output_contents.values()}
    contents_changed = False
    lib_changed = False

    for glyph_name in glyph_names:
        input_file_name = input_contents.get(glyph_name)
        if not input_file_name:
            raise ValueError(f"Glyph {glyph_name!r} not found in source UFO: {input_ufo}")

        output_file_name = output_contents.get(glyph_name)
        if not output_file_name:
            output_file_name = make_unique_glif_name(glyph_name, used_output_names)
            output_contents[glyph_name] = output_file_name
            add_glyph_to_lib_order(output_lib, glyph_name)
            contents_changed = True
            lib_changed = True

        input_file = input_glyph_dir / input_file_name
        output_file = output_glyph_dir / output_file_name
        if not input_file.exists():
            raise ValueError(f"Source GLIF file not found for glyph {glyph_name!r}: {input_file}")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_file, output_file)

    if contents_changed:
        write_contents_plist(output_glyph_dir, output_contents)
    if lib_changed:
        write_lib_plist(output_ufo, output_lib)


def build_ttf_from_ufo(input_dir: Path, output_ttf: Path) -> None:
    """Summary: Build a variable TTF from a UFO project via varwideufo.py.

    Args:
        input_dir: UFO project directory.
        output_ttf: Target TTF path.

    Returns:
        None

    Raises:
        RuntimeError: If varwideufo.py fails.

    Example:
        build_ttf_from_ufo(Path("_tmp/ufo_output"), Path("_output/out.ttf"))
    """

    output_ttf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(VARWIDEUFO_PY), "-input", str(input_dir), "-output", str(output_ttf)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        output_ttf.unlink(missing_ok=True)
        raise RuntimeError(f"varwideufo.py failed while converting UFO to TTF: exit code {result.returncode}")


def run_fonttool_fix_cmap(
    input_ttf: Path,
    output_ttf: Path,
    fix_stat_linked_bold: bool,
    anchor_rules_json_path: Optional[Path],
    merge_source_kern_from: Optional[Path],
) -> None:
    """Summary: Run fonttool_fix_cmap.py on an intermediate TTF.

    Args:
        input_ttf: Intermediate TTF path.
        output_ttf: Final TTF path.
        fix_stat_linked_bold: Whether to patch STAT linked bold entries.
        anchor_rules_json_path: Optional fixed anchor JSON path for final TTF patching.
        merge_source_kern_from: Optional source variable font path used to merge original kern.

    Returns:
        None

    Raises:
        RuntimeError: If fonttool_fix_cmap.py fails.

    Example:
        run_fonttool_fix_cmap(Path("_tmp/in.ttf"), Path("_output/out.ttf"), False, None, None)
    """

    output_ttf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(FONTTOOL_FIX_CMAP_PY),
        "-input",
        str(input_ttf),
        "-output",
        str(output_ttf),
        "--name-json",
        str(NAME_JSON_PATH),
        "--copy_kern_T_left_only_to_J",
        "--kern-rules-json",
        str(KERN_RULES_JSON_PATH),
    ]
    if anchor_rules_json_path is not None:
        cmd.extend(["--anchor-rules-json", str(anchor_rules_json_path)])
    if merge_source_kern_from is not None:
        cmd.extend(["--merge-source-kern-from", str(merge_source_kern_from)])
    if fix_stat_linked_bold:
        cmd.append("-fix_stat_linked_bold")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        output_ttf.unlink(missing_ok=True)
        raise RuntimeError(f"fonttool_fix_cmap.py failed with exit code {result.returncode}")


def run_ttfautohint(output_ttf: Path, ttfautohint_exe: Path) -> None:
    """Summary: Run ttfautohint on output TTF in-place.

    Args:
        output_ttf: Final output TTF path.
        ttfautohint_exe: ttfautohint executable path.

    Returns:
        None

    Raises:
        RuntimeError: If ttfautohint execution fails.

    Example:
        run_ttfautohint(Path("_output/out.ttf"), Path("C:/tool/ttfautohint/ttfautohint.exe"))
    """

    if not ttfautohint_exe.exists():
        raise RuntimeError(f"ttfautohint not found: {ttfautohint_exe}")

    hinted_ttf = output_ttf.with_suffix(".autohint.tmp.ttf")
    hinted_ttf.unlink(missing_ok=True)

    cmd = [str(ttfautohint_exe), str(output_ttf), str(hinted_ttf)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        eprint(result.stderr, end="")
    if result.returncode != 0:
        hinted_ttf.unlink(missing_ok=True)
        raise RuntimeError(f"ttfautohint failed with exit code {result.returncode}")

    shutil.move(str(hinted_ttf), str(output_ttf))


def validate_args(input_dir: Path, with_font: Path, output_ttf: Path, autohint: bool, ttfautohint_exe: Path) -> None:
    """Summary: Validate CLI input paths and file types.

    Args:
        input_dir: SFD input directory.
        with_font: Base variable TTF path.
        output_ttf: Output TTF path.
        autohint: Whether autohint is enabled.
        ttfautohint_exe: ttfautohint executable path.

    Returns:
        None

    Raises:
        ValueError: If any CLI path is invalid.

    Example:
        validate_args(Path("src/ufo"), Path("res/font.ttf"), Path("_output/out.ttf"), False, Path("ttfautohint.exe"))
    """

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"-input must be an existing folder: {input_dir}")
    if not with_font.exists() or not with_font.is_file() or with_font.suffix.lower() != ".ttf":
        raise ValueError(f"-with must be an existing .ttf file: {with_font}")
    if output_ttf.suffix.lower() != ".ttf":
        raise ValueError(f"-output must be a .ttf file path: {output_ttf}")
    if not VARWIDEUFO_PY.exists():
        raise ValueError(f"varwideufo.py not found: {VARWIDEUFO_PY}")
    if not FONTTOOL_FIX_CMAP_PY.exists():
        raise ValueError(f"fonttool_fix_cmap.py not found: {FONTTOOL_FIX_CMAP_PY}")
    if not NAME_JSON_PATH.exists():
        raise ValueError(f"name json not found: {NAME_JSON_PATH}")
    if autohint and not ttfautohint_exe.exists():
        raise ValueError(f"ttfautohint not found: {ttfautohint_exe}")


def main() -> int:
    """Summary: Execute the ufo_merge workflow from CLI arguments.

    Args:
        None

    Returns:
        int: Process exit code.

    Example:
        raise SystemExit(main())
    """

    args = parse_args()
    input_dir = Path(args.input).expanduser().resolve()
    with_font = Path(args.with_font).expanduser().resolve()
    output_ttf = Path(args.output).expanduser().resolve()
    ttfautohint_exe = Path(args.ttfautohint).expanduser().resolve()

    try:
        validate_args(input_dir, with_font, output_ttf, args.autohint, ttfautohint_exe)
        sfd_paths = find_sfd_inputs(input_dir)
        glyph_update_path = resolve_glyph_update_path(input_dir)
        modified_glyphs = read_modified_list(glyph_update_path, sfd_paths, args.auto_expand_refer_glyphs)
        if not modified_glyphs:
            eprint(f"Warning: glyph update list is empty: {glyph_update_path}")

        ensure_clean_dir(TMP_UFO_INPUT)
        ensure_clean_dir(TMP_UFO_OUTPUT)
        TMP_MERGED_TTF.unlink(missing_ok=True)
        output_ttf.unlink(missing_ok=True)
        print(f"Building base UFO project from TTF: {with_font.name}")
        build_ufo_from_ttf(with_font, TMP_UFO_OUTPUT)

        for sfd_path in sfd_paths:
            output_ufo_name = sfd_path.stem
            input_ufo = TMP_UFO_INPUT / output_ufo_name
            output_ufo = TMP_UFO_OUTPUT / output_ufo_name

            print(f"Exporting UFO from SFD: {sfd_path.name}")
            build_ufo_from_sfd(sfd_path, input_ufo)

            if not output_ufo.exists():
                raise ValueError(f"Matching output UFO not found for {sfd_path.name}: {output_ufo}")

            print(f"Copying {len(modified_glyphs)} glyph(s) from {input_ufo.name} to {output_ufo.name}")
            copy_modified_glyphs(input_ufo, output_ufo, modified_glyphs)

        print(f"Building intermediate TTF: {TMP_MERGED_TTF}")
        variable_anchor_masters_applied = apply_variable_anchor_masters(input_dir, TMP_UFO_OUTPUT)
        build_ttf_from_ufo(TMP_UFO_OUTPUT, TMP_MERGED_TTF)
        print(f"Running fonttool_fix_cmap.py for final output: {output_ttf}")
        final_anchor_rules_json = (
            DISABLED_ANCHOR_RULES_JSON_PATH if variable_anchor_masters_applied else ANCHOR_RULES_JSON_PATH
        )
        run_fonttool_fix_cmap(
            TMP_MERGED_TTF,
            output_ttf,
            args.fix_stat_linked_bold,
            final_anchor_rules_json,
            with_font if variable_anchor_masters_applied else None,
        )
        if args.autohint:
            print(f"Running ttfautohint on final output: {output_ttf}")
            run_ttfautohint(output_ttf, ttfautohint_exe)
        print(f"Done: {output_ttf}")
        print("input change list : glyf_update.txt")
        return 0
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
