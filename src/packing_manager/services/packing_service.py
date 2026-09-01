"""Application workflow service."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from packing_manager.models import PurchaseOrder
from packing_manager.pdf_parser import PurchaseOrderParser

from .material_merger import merge_materials


class PurchaseOrderReader(Protocol):
    def parse(self, pdf_path: Path) -> PurchaseOrder:
        """Parse a purchase-order PDF."""
        ...


class PackingService:
    """Coordinate purchase-order parsing and material consolidation."""

    def __init__(self, parser: PurchaseOrderReader | None = None) -> None:
        self.parser = parser or PurchaseOrderParser()

    def load_purchase_order(self, pdf_path: Path) -> PurchaseOrder:
        """Parse a PDF and return an order with consolidated material rows."""
        order = self.parser.parse(pdf_path)
        order.materials = merge_materials(order.materials)
        return order
