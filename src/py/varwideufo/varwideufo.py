#!/usr/bin/env python3
"""
varwideufo.py

Convert a variable-weight TrueType font (.ttf/.otf with a wght axis) into a
minimal editable UFO project (masters + designspace), or build a variable
TrueType font back from an existing UFO/designspace project.

Direction is auto-detected from -input:
- input .ttf/.otf  -> output directory containing *.ufo and *.designspace
- input .designspace, .ufo, or a directory containing one .designspace
  -> output variable .ttf via fontmake

Notes:
- TTF -> UFO currently supports glyf-based TrueType outlines.
- TTF -> UFO reconstructs min/default/max weight masters by instancing the VF.
- UFO -> TTF requires the external `fontmake` command to be installed.
"""
from __future__ import annotations

import argparse
import copy
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import xml.etree.ElementTree as ET

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.pens.recordingPen import RecordingPointPen
from fontTools.pens.pointPen import ReverseContourPointPen
from fontTools.ttLib import TTFont
from fontTools.ufoLib.glifLib import readGlyphFromString, writeGlyphToString
from fontTools.varLib.instancer import instantiateVariableFont

PROJECT_METADATA_FILENAME = 'varwideufo_source.plist'
PRESERVED_TABLE_TAGS = ('fvar', 'STAT', 'OS/2', 'GDEF', 'GPOS', 'GSUB', 'prep', 'gasp', 'name')


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_style_token(value: float) -> str:
    if int(value) == value:
        return str(int(value))
    return str(value).replace('.', '_')


def write_plist(path: Path, data: object) -> None:
    with path.open('wb') as f:
        plistlib.dump(data, f, sort_keys=False)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8', newline='\n')


def write_project_metadata(output_dir: Path, input_font: Path) -> None:
    metadata_path = output_dir / PROJECT_METADATA_FILENAME
    metadata = {
        'sourceFontPath': os.path.relpath(str(input_font.resolve()), str(output_dir.resolve())),
    }
    write_plist(metadata_path, metadata)


def read_project_metadata(project_dir: Path) -> Optional[Dict[str, str]]:
    metadata_path = project_dir / PROJECT_METADATA_FILENAME
    if not metadata_path.exists():
        return None
    with metadata_path.open('rb') as f:
        data = plistlib.load(f)
    if not isinstance(data, dict):
        return None
    return data


def glyph_file_name(glyph_name: str, used_names: set[str]) -> str:
    base_name = glyph_name.replace('/', '_')
    candidate = f'{base_name}.glif'
    if candidate.lower() not in used_names:
        used_names.add(candidate.lower())
        return candidate

    suffix = 1
    while True:
        candidate = f'{base_name}__{suffix}.glif'
        if candidate.lower() not in used_names:
            used_names.add(candidate.lower())
            return candidate
        suffix += 1


def indent_xml(elem: ET.Element, level: int = 0) -> None:
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


def get_weight_axis(tt: TTFont):
    if 'fvar' not in tt:
        raise ValueError('Input font is not a variable font: missing fvar table.')
    axes = {axis.axisTag: axis for axis in tt['fvar'].axes}
    if 'wght' not in axes:
        raise ValueError('Input variable font has no wght axis.')
    return axes['wght']


def instantiate_to_temp(tt: TTFont, weight: float) -> TTFont:
    instance = instantiateVariableFont(tt, {'wght': weight}, inplace=False)
    return instance


def glyph_unicodes_from_cmap(tt: TTFont) -> Dict[str, List[int]]:
    cmap = tt.getBestCmap() or {}
    out: Dict[str, List[int]] = {}
    for codepoint, glyph_name in cmap.items():
        out.setdefault(glyph_name, []).append(codepoint)
    return out


def build_fontinfo(tt: TTFont, family_name: str, style_name: str) -> Dict[str, object]:
    head = tt['head']
    hhea = tt['hhea']
    os2 = tt['OS/2'] if 'OS/2' in tt else None
    post = tt['post'] if 'post' in tt else None
    info: Dict[str, object] = {
        'familyName': family_name,
        'styleName': style_name,
        'unitsPerEm': int(head.unitsPerEm),
        'ascender': int(hhea.ascent),
        'descender': int(hhea.descent),
        'openTypeHeadCreated': '1970/01/01 00:00:00',
    }
    if os2 is not None:
        info['openTypeOS2WeightClass'] = int(getattr(os2, 'usWeightClass', 400))
        info['xHeight'] = int(getattr(os2, 'sxHeight', 0) or 0)
        info['capHeight'] = int(getattr(os2, 'sCapHeight', 0) or 0)
    if post is not None:
        info['italicAngle'] = float(getattr(post, 'italicAngle', 0.0))
        info['underlinePosition'] = int(getattr(post, 'underlinePosition', 0))
        info['underlineThickness'] = int(getattr(post, 'underlineThickness', 0))
    return info


def write_glif(path: Path, glyph_name: str, width: int, ops: List[Tuple], unicodes: Iterable[int]) -> None:
    root = ET.Element('glyph', {'name': glyph_name, 'format': '2'})
    for codepoint in sorted(unicodes):
        ET.SubElement(root, 'unicode', {'hex': f'{codepoint:04X}'})
    ET.SubElement(root, 'advance', {'width': str(int(width))})

    if ops:
        outline = ET.SubElement(root, 'outline')
        current_contour: Optional[ET.Element] = None
        for op_name, args, _kwargs in ops:
            if op_name == 'beginPath':
                current_contour = ET.SubElement(outline, 'contour')
            elif op_name == 'endPath':
                current_contour = None
            elif op_name == 'addPoint':
                if current_contour is None:
                    raise ValueError(f'Point emitted outside contour for glyph {glyph_name}')
                (xy, segment_type, smooth, point_name) = args
                attrib = {'x': str(int(xy[0])), 'y': str(int(xy[1]))}
                if segment_type is not None:
                    attrib['type'] = segment_type
                if smooth:
                    attrib['smooth'] = 'yes'
                if point_name:
                    attrib['name'] = str(point_name)
                ET.SubElement(current_contour, 'point', attrib)
            elif op_name == 'addComponent':
                base_glyph, transform = args
                xx, xy, yx, yy, dx, dy = transform
                attrib = {
                    'base': base_glyph,
                    'xScale': str(xx),
                    'xyScale': str(xy),
                    'yxScale': str(yx),
                    'yScale': str(yy),
                    'xOffset': str(dx),
                    'yOffset': str(dy),
                }
                ET.SubElement(outline, 'component', attrib)
            else:
                raise ValueError(f'Unsupported point-pen op {op_name!r} for glyph {glyph_name}')

    indent_xml(root)
    tree = ET.ElementTree(root)
    tree.write(path, encoding='UTF-8', xml_declaration=True)


class GlifGlyph:
    """Minimal glyph object for GLIF round-trip through glifLib."""

    def __init__(self) -> None:
        self.name = ''
        self.width = 0
        self.height = 0
        self.unicodes: List[int] = []


def reverse_glif_contours(glif_path: Path) -> None:
    """Reverse contour winding in one GLIF file while preserving metadata."""

    original_root = ET.fromstring(glif_path.read_text(encoding='utf-8'))
    preserved_anchors = [copy.deepcopy(child) for child in list(original_root) if child.tag == 'anchor']

    glyph = GlifGlyph()
    pen = RecordingPointPen()
    text = ET.tostring(original_root, encoding='unicode')
    readGlyphFromString(text, glyphObject=glyph, pointPen=pen)

    reversed_pen = RecordingPointPen()
    pen.replay(ReverseContourPointPen(reversed_pen))
    out = writeGlyphToString(glyph.name, glyphObject=glyph, drawPointsFunc=reversed_pen.replay)
    rebuilt_root = ET.fromstring(out)
    rebuilt_anchor_names = [child.get('name') for child in list(rebuilt_root) if child.tag == 'anchor']
    if preserved_anchors and not rebuilt_anchor_names:
        insert_index = 0
        for index, child in enumerate(list(rebuilt_root)):
            if child.tag in {'unicode', 'advance'}:
                insert_index = index + 1
        for anchor_elem in preserved_anchors:
            rebuilt_root.insert(insert_index, anchor_elem)
            insert_index += 1
    indent_xml(rebuilt_root)
    ET.ElementTree(rebuilt_root).write(glif_path, encoding='UTF-8', xml_declaration=True)


def prepare_build_project(original_designspace: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    """Create a temporary UFO project copy with contours pre-reversed for fontmake."""

    tmp_dir = tempfile.TemporaryDirectory(prefix='varwideufo_build_')
    tmp_root = Path(tmp_dir.name)
    project_copy = tmp_root / 'project'
    shutil.copytree(original_designspace.parent, project_copy)

    for glif_path in project_copy.glob('*.ufo/glyphs/*.glif'):
        reverse_glif_contours(glif_path)

    return tmp_dir, project_copy / original_designspace.name


def ttfont_to_ufo(tt: TTFont, out_ufo: Path, family_name: str, style_name: str) -> None:
    if 'glyf' not in tt:
        raise ValueError('TTF -> UFO currently supports glyf-based TrueType fonts only.')

    glyph_order = tt.getGlyphOrder()
    glyf = tt['glyf']
    hmtx = tt['hmtx'].metrics
    unicodes_map = glyph_unicodes_from_cmap(tt)

    glyph_dir = out_ufo / 'glyphs'
    ensure_dir(glyph_dir)
    ensure_dir(out_ufo)

    contents: Dict[str, str] = {}
    used_file_names: set[str] = set()
    for glyph_name in glyph_order:
        file_name = glyph_file_name(glyph_name, used_file_names)
        contents[glyph_name] = file_name
        pen = RecordingPointPen()
        glyf[glyph_name].drawPoints(pen, glyf)
        width = int(hmtx.get(glyph_name, (0, 0))[0])
        write_glif(glyph_dir / file_name, glyph_name, width, pen.value, unicodes_map.get(glyph_name, []))

    write_plist(out_ufo / 'metainfo.plist', {'creator': 'varwideufo.py', 'formatVersion': 3})
    write_plist(out_ufo / 'fontinfo.plist', build_fontinfo(tt, family_name, style_name))
    write_plist(out_ufo / 'layercontents.plist', [['public.default', 'glyphs']])
    write_plist(out_ufo / 'glyphs' / 'contents.plist', contents)
    write_plist(out_ufo / 'lib.plist', {'public.glyphOrder': glyph_order})
    write_plist(out_ufo / 'groups.plist', {})
    write_plist(out_ufo / 'kerning.plist', {})
    write_text(out_ufo / 'features.fea', '')


def original_glyph_order_is_preserved(source_order: List[str], built_order: List[str]) -> bool:
    if len(built_order) < len(source_order):
        return False
    return built_order[:len(source_order)] == source_order


def original_cmap_is_preserved(source_cmap: Dict[int, str], built_cmap: Dict[int, str]) -> bool:
    for codepoint, glyph_name in source_cmap.items():
        if built_cmap.get(codepoint) != glyph_name:
            return False
    return True


def can_preserve_tables(source_font: TTFont, built_font: TTFont) -> bool:
    source_order = source_font.getGlyphOrder()
    built_order = built_font.getGlyphOrder()
    source_cmap = source_font.getBestCmap() or {}
    built_cmap = built_font.getBestCmap() or {}
    return (
        original_glyph_order_is_preserved(source_order, built_order)
        and original_cmap_is_preserved(source_cmap, built_cmap)
    )


def get_preservation_failure_reason(source_font: TTFont, built_font: TTFont) -> str:
    source_order = source_font.getGlyphOrder()
    built_order = built_font.getGlyphOrder()
    source_cmap = source_font.getBestCmap() or {}
    built_cmap = built_font.getBestCmap() or {}

    if len(built_order) < len(source_order):
        return 'rebuilt font is missing original glyphs'
    if built_order[:len(source_order)] != source_order:
        return 'original glyph order changed in rebuilt font'
    for codepoint, glyph_name in source_cmap.items():
        if built_cmap.get(codepoint) != glyph_name:
            return f'original cmap mapping changed for U+{codepoint:04X}'
    return 'rebuilt font is not source-compatible'


def preserve_source_tables(project_dir: Path, output_font: Path) -> None:
    metadata = read_project_metadata(project_dir)
    if not metadata:
        return

    relative_source_path = metadata.get('sourceFontPath')
    if not relative_source_path:
        return
    skip_preserve_tags = {
        str(tag) for tag in metadata.get('skipPreserveTags', [])
        if isinstance(tag, str)
    }

    source_font_path = (project_dir / relative_source_path).resolve()
    if not source_font_path.exists():
        eprint(f'Warning: source font metadata points to missing file: {source_font_path}')
        return

    with TTFont(str(source_font_path)) as source_font, TTFont(str(output_font)) as built_font:
        if not can_preserve_tables(source_font, built_font):
            reason = get_preservation_failure_reason(source_font, built_font)
            eprint(f'Warning: skipped source table preservation because {reason}.')
            return

        for tag in PRESERVED_TABLE_TAGS:
            if tag in skip_preserve_tags:
                continue
            if tag in source_font:
                built_font[tag] = copy.deepcopy(source_font[tag])
        built_font.save(str(output_font))


def variable_font_to_ufo_project(input_font: Path, output_dir: Path) -> None:
    ensure_dir(output_dir)
    tt = TTFont(str(input_font))
    axis = get_weight_axis(tt)
    write_project_metadata(output_dir, input_font)

    family_name = input_font.stem
    min_w = float(axis.minValue)
    def_w = float(axis.defaultValue)
    max_w = float(axis.maxValue)
    weights: List[float] = []
    for value in (min_w, def_w, max_w):
        if value not in weights:
            weights.append(value)

    ds = DesignSpaceDocument()
    ds_path = output_dir / f'{family_name}.designspace'
    ds.path = str(ds_path.resolve())
    axis_desc = AxisDescriptor()
    axis_desc.name = 'Weight'
    axis_desc.tag = 'wght'
    axis_desc.minimum = min_w
    axis_desc.default = def_w
    axis_desc.maximum = max_w
    ds.addAxis(axis_desc)

    for weight in weights:
        style_name = f'W{safe_style_token(weight)}'
        ufo_name = f'{family_name}-{style_name}.ufo'
        ufo_path = output_dir / ufo_name
        instance_tt = instantiate_to_temp(tt, weight)
        ttfont_to_ufo(instance_tt, ufo_path, family_name, style_name)

        src = SourceDescriptor()
        src.path = str(ufo_path.resolve())
        src.name = style_name
        src.familyName = family_name
        src.styleName = style_name
        src.location = {'Weight': weight}
        if weight == def_w:
            src.copyLib = True
            src.copyFeatures = True
            src.copyGroups = True
            src.copyInfo = True
        ds.addSource(src)

    ds.write(str(ds_path))


def find_designspace_for_input(input_path: Path) -> Path:
    if input_path.is_file() and input_path.suffix.lower() == '.designspace':
        return input_path

    if input_path.is_file() and input_path.suffix.lower() == '.ufo':
        parent = input_path.parent
    elif input_path.is_dir():
        parent = input_path
    else:
        raise ValueError('For UFO -> TTF, input must be a .designspace, a .ufo, or a directory containing one .designspace.')

    matches = sorted(parent.glob('*.designspace'))
    if not matches:
        raise ValueError(f'No .designspace file found in {parent}')
    if len(matches) > 1:
        raise ValueError(f'Multiple .designspace files found in {parent}; pass the exact one via -input.')
    return matches[0]


def build_variable_font_from_ufo(input_path: Path, output_font: Path) -> None:
    designspace = find_designspace_for_input(input_path)
    fontmake = shutil.which('fontmake')
    if not fontmake:
        raise RuntimeError('fontmake is required for UFO -> variable TTF. Install it with: pip install fontmake')

    ensure_dir(output_font.parent)
    tmp_dir, build_designspace = prepare_build_project(designspace)
    try:
        cmd = [
            fontmake,
            '-m', str(build_designspace),
            '-o', 'variable',
            '--output-path', str(output_font),
        ]
        subprocess.run(cmd, check=True, cwd=str(build_designspace.parent))
    finally:
        tmp_dir.cleanup()
    preserve_source_tables(designspace.parent, output_font)


def detect_direction(input_path: Path) -> str:
    suffix = input_path.suffix.lower()
    if suffix in {'.ttf', '.otf'}:
        return 'ttf-to-ufo'
    if suffix in {'.ufo', '.designspace'} or input_path.is_dir():
        return 'ufo-to-ttf'
    raise ValueError('Unsupported input type. Use .ttf/.otf for VF -> UFO, or .ufo/.designspace/directory for UFO -> VF.')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Convert variable weight TTF <-> UFO project.')
    parser.add_argument('-input', required=True, help='Input path (.ttf/.otf, .ufo, .designspace, or project directory)')
    parser.add_argument('-output', required=True, help='Output directory for TTF->UFO, or output .ttf for UFO->TTF')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        eprint(f'Input not found: {input_path}')
        return 2

    try:
        direction = detect_direction(input_path)
        if direction == 'ttf-to-ufo':
            if output_path.exists() and output_path.is_file():
                raise ValueError('For TTF -> UFO, -output must be a directory path.')
            variable_font_to_ufo_project(input_path, output_path)
            print(f'Wrote UFO project to {output_path}')
        else:
            if output_path.suffix.lower() != '.ttf':
                raise ValueError('For UFO -> TTF, -output must be a .ttf file path.')
            build_variable_font_from_ufo(input_path, output_path)
            print(f'Wrote variable font to {output_path}')
        return 0
    except subprocess.CalledProcessError as exc:
        eprint(f'Build failed with exit code {exc.returncode}: {exc}')
        return exc.returncode or 1
    except Exception as exc:  # noqa: BLE001
        eprint(f'Error: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
