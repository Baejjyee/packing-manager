"""Material-row consolidation rules."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from packing_manager.models import MaterialItem


def merge_materials(materials: Iterable[MaterialItem]) -> list[MaterialItem]:
    """Merge rows with the same material name, specification, and color.

    The original order is retained. Ordered quantity and loss are summed
    independently, as required by the purchase-order workflow.
    """
    merged: dict[tuple[str, str, str], MaterialItem] = {}

    for material in materials:
        key = (
            material.material_name.strip(),
            material.specification.strip(),
            material.color.strip(),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = replace(
                material,
                material_name=key[0],
                specification=key[1],
                color=key[2],
            )
            continue

        if existing.unit != material.unit:
            raise ValueError(
                "Cannot merge identical materials with different units: "
                f"{existing.unit!r} and {material.unit!r}"
            )
        existing.order_quantity += material.order_quantity
        existing.loss += material.loss

    return list(merged.values())
