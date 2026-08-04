"""Phase 0 acceptance gate (backend half): Python enums must match the canonical registry
exactly — same names, same members, same order — and must not omit or add any enum group.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.enums import ENUM_REGISTRY

CANONICAL_PATH = Path(__file__).resolve().parents[2] / "docs" / "schemas" / "enums.json"


def _canonical() -> dict[str, list[str]]:
    data = json.loads(CANONICAL_PATH.read_text(encoding="utf-8"))
    return data["enums"]


def test_enum_group_names_match() -> None:
    canonical = _canonical()
    assert set(ENUM_REGISTRY.keys()) == set(canonical.keys()), "Python enum groups differ from docs/schemas/enums.json"


def test_each_enum_members_and_order_match() -> None:
    canonical = _canonical()
    mismatches: list[str] = []
    for name, enum_cls in ENUM_REGISTRY.items():
        expected = canonical[name]
        actual = enum_cls.values()
        if actual != expected:
            mismatches.append(f"{name}: python={actual} canonical={expected}")
    assert not mismatches, "Enum parity mismatches:\n" + "\n".join(mismatches)


def test_no_duplicate_values_within_enum() -> None:
    for name, enum_cls in ENUM_REGISTRY.items():
        values = enum_cls.values()
        assert len(values) == len(set(values)), f"Duplicate values in {name}"
