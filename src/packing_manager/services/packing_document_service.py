"""Prepare and generate packing documents from reviewed order data."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol, Sequence

from packing_manager.models import (
    PackingDocument,
    PackingLine,
    PackingLineDetails,
    PackingPackage,
    PurchaseOrder,
)

from .pdf_generator import PackingPdfGenerator


_PACKAGE_PATTERN = re.compile(
    r"^\s*(?P<quantity>\d+(?:\.\d+)?)"
    r"(?:\s*\+\s*(?P<loss>\d+(?:\.\d+)?))?"
    r"(?:\s*[xX*]\s*(?P<count>\d+))?\s*$"
)


class PackingPdfWriter(Protocol):
    def create_packing_list(
        self, document: PackingDocument, output_path: Path
    ) -> None: ...

    def create_packing_labels(
        self, document: PackingDocument, output_path: Path
    ) -> None: ...


class PackingDocumentService:
    """Build validated document data and delegate PDF rendering."""

    def __init__(self, generator: PackingPdfWriter | None = None) -> None:
        self.generator = generator or PackingPdfGenerator()

    def build_document(
        self,
        order: PurchaseOrder,
        shipping_date: date,
        packing_list_number: str,
        details: Sequence[PackingLineDetails],
    ) -> PackingDocument:
        """Combine reviewed order fields with user-entered packing details."""
        if len(details) != len(order.materials):
            raise ValueError("자재 행과 포장 정보 행의 수가 다릅니다.")

        lines = [
            PackingLine(
                material_name=material.material_name,
                english_name=material.english_name or "",
                specification=material.specification,
                color=material.color,
                unit=material.unit,
                order_quantity=material.order_quantity,
                loss=material.loss,
                weight_kg=detail.weight_kg,
                cbm=detail.cbm,
                packages=list(detail.packages),
            )
            for material, detail in zip(order.materials, details, strict=True)
        ]
        document = PackingDocument(
            supplier=order.supplier,
            buyer=order.brand,
            po_number=order.on_code,
            item_name=order.erp_item_english_name or "",
            finished_goods_quantity=order.finished_goods_quantity,
            shipping_date=shipping_date,
            packing_list_number=packing_list_number.strip(),
            lines=lines,
        )
        document.validate()
        return document

    def generate(
        self,
        document: PackingDocument,
        packing_list_path: Path,
        label_path: Path,
    ) -> None:
        """Generate both PDFs from the same validated data."""
        self.generator.create_packing_list(document, packing_list_path)
        self.generator.create_packing_labels(document, label_path)


def parse_package_expression(expression: str) -> list[PackingPackage]:
    """Parse `quantity+loss*count` groups separated by commas.

    Example: ``53+1*3, 8+2*1`` creates four package labels.
    """
    groups = [group.strip() for group in expression.split(",") if group.strip()]
    if not groups:
        raise ValueError("포장 구성을 입력해 주세요.")

    packages: list[PackingPackage] = []
    for group in groups:
        match = _PACKAGE_PATTERN.fullmatch(group)
        if match is None:
            raise ValueError(
                f"포장 구성 형식이 올바르지 않습니다: {group!r} "
                "(예: 53+1*3, 8+2*1)"
            )
        try:
            quantity = Decimal(match.group("quantity"))
            loss = Decimal(match.group("loss") or "0")
            count = int(match.group("count") or "1")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"포장 구성 숫자가 올바르지 않습니다: {group!r}") from exc
        if count < 1:
            raise ValueError("포장 개수는 1개 이상이어야 합니다.")
        packages.extend(PackingPackage(quantity, loss) for _ in range(count))
    return packages
