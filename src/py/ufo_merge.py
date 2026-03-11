#!/usr/bin/env python3
"""Merge modified glyphs from SFD-derived UFOs back into a variable TTF."""

from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List


FONTFORGE_BIN = Path(r"C:\Program Files (x86)\FontForgeBuilds\bin\fontforge.exe")
REPO_ROOT = Path(__file__).resolve().parents[2]
VARWIDEUFO_PY = REPO_ROOT / "src" / "py" / "varwideufo" / "varwideufo.py"
TMP_UFO_INPUT = REPO_ROOT / "_tmp" / "ufo_input"
TMP_UFO_OUTPUT = REPO_ROOT / "_tmp" / "ufo_output"

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
    """Summary: Print a message to stderr.

    Args:
        *args: Message parts to print.
        **kwargs: Extra print keyword arguments.

    Returns:
        None

    Example:
        eprint("Something went wrong")
    """

    print(*args, file=sys.stderr, **kwargs)


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
    parser.add_argument("-input", required=True, help="Folder containing *.sfd and glyf_list_*.txt")
    parser.add_argument("-with", dest="with_font", required=True, help="Base variable TTF file")
    parser.add_argument("-output", required=True, help="Output TTF path")
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
        input_dir: Folder containing source SFD files.

    Returns:
        List[Path]: Sorted list of matching SFD paths.

    Raises:
        ValueError: If no SFD files are found.

    Example:
        find_sfd_inputs(Path("src/ufo"))
    """

    sfd_paths = sorted(input_dir.glob("*.sfd"))
    if not sfd_paths:
        raise ValueError(f"No .sfd files found in {input_dir}")
    return sfd_paths


def resolve_modified_list_path(sfd_path: Path) -> Path:
    """Summary: Resolve the modified glyph list path for an SFD file.

    Args:
        sfd_path: Source SFD path.

    Returns:
        Path: Path to the corresponding glyf list file.

    Raises:
        ValueError: If the list file does not exist.

    Example:
        resolve_modified_list_path(Path("src/ufo/Font-W300.ufo.sfd"))
    """

    modified_list_path = sfd_path.parent / f"glyf_list_{sfd_path.stem}.txt"
    if not modified_list_path.exists():
        raise ValueError(f"Missing modified glyph list for {sfd_path.name}: {modified_list_path.name}")
    return modified_list_path


def read_modified_list(modified_list_path: Path) -> List[str]:
    """Summary: Read glyph names from a modified list file.

    Args:
        modified_list_path: Path to a glyf_list_*.txt file.

    Returns:
        List[str]: Glyph names in file order without blank lines.

    Example:
        read_modified_list(Path("src/ufo/glyf_list_Font-W300.ufo.txt"))
    """

    lines = modified_list_path.read_text(encoding="utf-8-sig").splitlines()
    return [line.strip() for line in lines if line.strip()]


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
        build_ufo_from_sfd(Path("src/ufo/font.ufo.sfd"), Path("_tmp/ufo_input/font.ufo"))
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

    for glyph_name in glyph_names:
        input_file_name = input_contents.get(glyph_name)
        if not input_file_name:
            raise ValueError(f"Glyph {glyph_name!r} not found in source UFO: {input_ufo}")

        output_file_name = output_contents.get(glyph_name)
        if not output_file_name:
            raise ValueError(f"Glyph {glyph_name!r} not found in target UFO: {output_ufo}")

        input_file = input_glyph_dir / input_file_name
        output_file = output_glyph_dir / output_file_name
        if not input_file.exists():
            raise ValueError(f"Source GLIF file not found for glyph {glyph_name!r}: {input_file}")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_file, output_file)


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


def validate_args(input_dir: Path, with_font: Path, output_ttf: Path) -> None:
    """Summary: Validate CLI input paths and file types.

    Args:
        input_dir: SFD input directory.
        with_font: Base variable TTF path.
        output_ttf: Output TTF path.

    Returns:
        None

    Raises:
        ValueError: If any CLI path is invalid.

    Example:
        validate_args(Path("src/ufo"), Path("res/font.ttf"), Path("_output/out.ttf"))
    """

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(f"-input must be an existing folder: {input_dir}")
    if not with_font.exists() or not with_font.is_file() or with_font.suffix.lower() != ".ttf":
        raise ValueError(f"-with must be an existing .ttf file: {with_font}")
    if output_ttf.suffix.lower() != ".ttf":
        raise ValueError(f"-output must be a .ttf file path: {output_ttf}")
    if not VARWIDEUFO_PY.exists():
        raise ValueError(f"varwideufo.py not found: {VARWIDEUFO_PY}")


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

    try:
        validate_args(input_dir, with_font, output_ttf)
        sfd_paths = find_sfd_inputs(input_dir)

        ensure_clean_dir(TMP_UFO_INPUT)
        ensure_clean_dir(TMP_UFO_OUTPUT)
        print(f"Building base UFO project from TTF: {with_font.name}")
        build_ufo_from_ttf(with_font, TMP_UFO_OUTPUT)

        for sfd_path in sfd_paths:
            modified_list_path = resolve_modified_list_path(sfd_path)
            modified_glyphs = read_modified_list(modified_list_path)
            if not modified_glyphs:
                eprint(f"Warning: modified glyph list is empty: {modified_list_path}")

            output_ufo_name = sfd_path.stem
            input_ufo = TMP_UFO_INPUT / output_ufo_name
            output_ufo = TMP_UFO_OUTPUT / output_ufo_name

            print(f"Exporting UFO from SFD: {sfd_path.name}")
            build_ufo_from_sfd(sfd_path, input_ufo)

            if not output_ufo.exists():
                raise ValueError(f"Matching output UFO not found for {sfd_path.name}: {output_ufo}")

            print(f"Copying {len(modified_glyphs)} glyph(s) from {input_ufo.name} to {output_ufo.name}")
            copy_modified_glyphs(input_ufo, output_ufo, modified_glyphs)

        print(f"Building merged TTF: {output_ttf}")
        build_ttf_from_ufo(TMP_UFO_OUTPUT, output_ttf)
        print(f"Done: {output_ttf}")
        return 0
    except Exception as exc:  # noqa: BLE001
        eprint(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
