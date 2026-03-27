#!/usr/bin/env python3
"""Shared helpers for font name-table and version metadata updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


MAC_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


def compute_version(now: datetime | None = None) -> str:
    """Summary: Build version string in 0.YYMMDD format.

    Args:
        now: Datetime to use; defaults to current local timezone.

    Returns:
        str: Version string such as 0.260310.

    Example:
        compute_version()
    """

    current = now or datetime.now().astimezone()
    return f"0.{current.strftime('%y%m%d')}"


def compute_head_created(now: datetime | None = None) -> int:
    """Summary: Compute head.created in Mac epoch seconds.

    Args:
        now: Datetime to use; defaults to current local timezone.

    Returns:
        int: Rounded seconds since 1904-01-01 UTC.

    Example:
        compute_head_created()
    """

    current = now or datetime.now().astimezone()
    return int(round((current - MAC_EPOCH).total_seconds()))


def normalize_name_records(name_json: Any) -> list[dict[str, Any]]:
    """Summary: Extract name records list from name JSON.

    Args:
        name_json: Parsed name JSON object.

    Returns:
        list[dict[str, Any]]: Name records list.

    Raises:
        ValueError: If JSON format is unsupported.

    Example:
        normalize_name_records({"name": []})
    """

    if isinstance(name_json, dict) and isinstance(name_json.get("name"), list):
        return name_json["name"]
    if isinstance(name_json, list):
        return name_json
    raise ValueError("-namejson must be a list or an object containing a 'name' list.")


def replace_version_placeholders(name_records: list[dict[str, Any]], version: str) -> int:
    """Summary: Replace version placeholders and version strings in name records.

    Args:
        name_records: Name records to update in-place.
        version: Computed version string.

    Returns:
        int: Number of modified nameString entries.

    Example:
        replace_version_placeholders(records, "0.260310")
    """

    changed = 0
    for record in name_records:
        if not isinstance(record, dict):
            continue
        value = record.get("nameString")
        if not isinstance(value, str):
            continue

        new_value = value.replace("{}", version)
        if value.startswith("Version "):
            new_value = f"Version {version}"

        if new_value != value:
            record["nameString"] = new_value
            changed += 1
    return changed


def set_fe_codepage_bits(os2_table: dict[str, Any]) -> None:
    """Summary: Enable Far East related codepage bits in OS/2.

    Args:
        os2_table: The OS/2 table object to update in-place.

    Returns:
        None

    Example:
        set_fe_codepage_bits(font_json["OS_2"])
    """

    codepage = os2_table.setdefault("ulCodePageRange1", {})
    if not isinstance(codepage, dict):
        codepage = {}
        os2_table["ulCodePageRange1"] = codepage

    for key in ("jis", "gbk", "big5", "korean"):
        codepage[key] = True


def apply_rename_rules(font_json: dict[str, Any], name_records: list[dict[str, Any]], version: str) -> None:
    """Summary: Apply all required rename and metadata update rules.

    Args:
        font_json: Font JSON object from otfccdump.
        name_records: Name records to write into font_json.
        version: Version string in 0.YYMMDD format.

    Returns:
        None

    Example:
        apply_rename_rules(font_json, name_records, "0.260310")
    """

    font_json["name"] = name_records

    os2 = font_json.setdefault("OS_2", {})
    if isinstance(os2, dict):
        os2["achVendID"] = "TNOZ"
        set_fe_codepage_bits(os2)

    head = font_json.setdefault("head", {})
    if isinstance(head, dict):
        head["created"] = compute_head_created()
        head["fontRevision"] = float(version)

