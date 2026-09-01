"""Parser for the current material purchase-order PDF layout."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

import pdfplumber

from packing_manager.models import MaterialItem, PurchaseOrder


class PurchaseOrderParseError(ValueError):
    """Raised when a PDF does not contain the expected purchase-order data."""


class PurchaseOrderParser:
    """Parse a material purchase-order PDF into a domain model."""

    def parse(self, pdf_path: Path) -> PurchaseOrder:
        """Extract order metadata and raw material rows from a PDF."""
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"Purchase-order PDF not found: {path}")
        if path.suffix.lower() != ".pdf":
            raise PurchaseOrderParseError(f"Not a PDF file: {path}")

        tables: list[list[list[str | None]]] = []
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    tables.extend(page.extract_tables())
        except PurchaseOrderParseError:
            raise
        except Exception as exc:
            raise PurchaseOrderParseError(f"Unable to read PDF: {path.name}") from exc

        return self._parse_tables(tables)

    def _parse_tables(
        self, tables: Sequence[Sequence[Sequence[str | None]]]
    ) -> PurchaseOrder:
        order = PurchaseOrder()

        for table in tables:
            self._extract_order_fields(table, order)
            order.materials.extend(self._extract_materials(table))

        missing = [
            label
            for label, value in (
                ("공급처명", order.supplier),
                ("ON코드", order.on_code),
                ("브랜드", order.brand),
                ("ERP품목명", order.erp_item_name),
            )
            if not value
        ]
        if order.finished_goods_quantity <= 0:
            missing.append("완제품 수량")
        if not order.materials:
            missing.append("발주 상세내역")
        if missing:
            raise PurchaseOrderParseError(
                "Required fields were not found: " + ", ".join(missing)
            )

        return order

    def _extract_order_fields(
        self, rows: Sequence[Sequence[str | None]], order: PurchaseOrder
    ) -> None:
        for row in rows:
            cells = [_clean_cell(cell) for cell in row]
            order.supplier = order.supplier or _value_after_label(cells, "공급처명")
            order.on_code = order.on_code or _value_after_label(cells, "ON코드")
            order.brand = order.brand or _value_after_label(cells, "브랜드")
            order.erp_item_name = order.erp_item_name or _value_after_label(
                cells, "ERP품목명"
            )

            quantity = _value_after_label(cells, "수량")
            if quantity and order.finished_goods_quantity == 0:
                order.finished_goods_quantity = _parse_decimal(quantity, "완제품 수량")

    def _extract_materials(
        self, rows: Sequence[Sequence[str | None]]
    ) -> list[MaterialItem]:
        header_index = next(
            (
                index
                for index, row in enumerate(rows)
                if _has_labels(row, "No.", "품명", "규격", "색상", "단위", "발주량", "Loss")
            ),
            None,
        )
        if header_index is None:
            return []

        header = rows[header_index]
        columns = {
            label: _label_index(header, label)
            for label in ("No.", "품명", "규격", "색상", "단위", "발주량", "Loss")
        }
        materials: list[MaterialItem] = []
        for row in rows[header_index + 1 :]:
            cells = [_clean_cell(cell) for cell in row]
            number = _cell_at(cells, columns["No."])
            if not re.fullmatch(r"\d+", number):
                continue

            materials.append(
                MaterialItem(
                    material_name=_cell_at(cells, columns["품명"]),
                    specification=_cell_at(cells, columns["규격"]),
                    color=_cell_at(cells, columns["색상"]),
                    unit=_cell_at(cells, columns["단위"]),
                    order_quantity=_parse_decimal(
                        _cell_at(cells, columns["발주량"]), "발주량"
                    ),
                    loss=_parse_decimal(_cell_at(cells, columns["Loss"]), "Loss"),
                )
            )
        return materials


def _clean_cell(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _canonical(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").casefold()


def _value_after_label(cells: Sequence[str], label: str) -> str:
    wanted = _canonical(label)
    for index, cell in enumerate(cells):
        if _canonical(cell) != wanted:
            continue
        return next((value for value in cells[index + 1 :] if value), "")
    return ""


def _has_labels(row: Sequence[str | None], *labels: str) -> bool:
    present = {_canonical(cell) for cell in row if cell}
    return all(_canonical(label) in present for label in labels)


def _label_index(row: Sequence[str | None], label: str) -> int:
    wanted = _canonical(label)
    return next(index for index, cell in enumerate(row) if _canonical(cell) == wanted)


def _cell_at(cells: Sequence[str], index: int) -> str:
    return cells[index] if index < len(cells) else ""


def _parse_decimal(value: str, field_name: str) -> Decimal:
    normalized = value.replace(",", "").strip()
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise PurchaseOrderParseError(
            f"Invalid number for {field_name}: {value!r}"
        ) from exc
