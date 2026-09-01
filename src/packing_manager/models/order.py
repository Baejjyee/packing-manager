"""Domain models for extracted purchase-order data."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class MaterialItem:
    """One material row before or after user review."""

    material_name: str = ""
    specification: str = ""
    color: str = ""
    order_quantity: Decimal = Decimal("0")
    loss: Decimal = Decimal("0")
    unit: str = ""
    english_name: str | None = None

    @property
    def total_quantity(self) -> Decimal:
        """Return ordered quantity including loss."""
        return self.order_quantity + self.loss


@dataclass(slots=True)
class PurchaseOrder:
    """Information extracted from one purchase-order PDF."""

    supplier: str = ""
    on_code: str = ""
    brand: str = ""
    erp_item_name: str = ""
    finished_goods_quantity: Decimal = Decimal("0")
    erp_item_english_name: str | None = None
    materials: list[MaterialItem] = field(default_factory=list)
