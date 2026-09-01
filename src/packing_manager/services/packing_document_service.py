"""Prepare and generate packing documents from reviewed order data."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
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
                packing_quantity=detail.packing_quantity,
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


def build_equal_packages(
    order_quantity: Decimal,
    loss: Decimal,
    packing_quantity: Decimal = Decimal("54"),
) -> list[PackingPackage]:
    """Split order quantity plus Loss into equal rolls and one remainder.

    The order and Loss portions remain separately traceable for validation,
    while each package's total is capped at ``packing_quantity``.
    """
    values = (order_quantity, loss, packing_quantity)
    if any(value < 0 for value in values[:2]):
        raise ValueError("발주량과 Loss는 0 이상이어야 합니다.")
    if packing_quantity <= 0:
        raise ValueError("Packing 수량은 0보다 커야 합니다.")

    total = order_quantity + loss
    if total <= 0:
        raise ValueError("발주량과 Loss의 합계는 0보다 커야 합니다.")

    full_count = int(total // packing_quantity)
    remainder = total - packing_quantity * full_count
    package_totals = [packing_quantity] * full_count
    if remainder:
        package_totals.append(remainder)

    remaining_order = order_quantity
    remaining_loss = loss
    packages: list[PackingPackage] = []
    for package_total in package_totals:
        package_order = min(remaining_order, package_total)
        package_loss = package_total - package_order
        if package_loss > remaining_loss:
            raise ValueError("포장 수량을 발주량과 Loss로 나눌 수 없습니다.")
        packages.append(PackingPackage(package_order, package_loss))
        remaining_order -= package_order
        remaining_loss -= package_loss

    if remaining_order or remaining_loss:
        raise ValueError("포장 수량 계산 결과가 발주량/Loss와 다릅니다.")
    return packages
