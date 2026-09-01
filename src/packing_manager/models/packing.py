"""Data prepared for Packing List and Packing Label documents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class PackingPackage:
    """One physical roll/package represented by one Packing Label."""

    order_quantity: Decimal
    loss: Decimal = Decimal("0")

    @property
    def total_quantity(self) -> Decimal:
        return self.order_quantity + self.loss


@dataclass(slots=True)
class PackingLineDetails:
    """User-entered physical packing values for one material."""

    weight_kg: Decimal
    cbm: Decimal
    packages: list[PackingPackage]
    packing_quantity: Decimal = Decimal("54")


@dataclass(slots=True)
class PackingLine:
    """One aggregated material row in the Packing List."""

    material_name: str
    specification: str
    color: str
    unit: str
    order_quantity: Decimal
    loss: Decimal
    english_name: str = ""
    weight_kg: Decimal = Decimal("0")
    cbm: Decimal = Decimal("0")
    packing_quantity: Decimal = Decimal("54")
    packages: list[PackingPackage] = field(default_factory=list)

    @property
    def total_quantity(self) -> Decimal:
        return self.order_quantity + self.loss


@dataclass(slots=True)
class PackingDocument:
    """All values required to generate a Packing List and its labels."""

    supplier: str
    buyer: str
    po_number: str
    item_name: str
    finished_goods_quantity: Decimal
    shipping_date: date
    lines: list[PackingLine]
    packing_list_number: str = ""
    company_name: str = "(주)삼덕통상"
    origin: str = "MADE IN KOREA"

    def validate(self) -> None:
        """Reject incomplete or internally inconsistent packing data."""
        required = {
            "공급처": self.supplier,
            "Buyer": self.buyer,
            "PO No.": self.po_number,
            "Item": self.item_name,
        }
        missing = [label for label, value in required.items() if not value.strip()]
        if missing:
            raise ValueError("필수값이 없습니다: " + ", ".join(missing))
        if not self.lines:
            raise ValueError("Packing List에 자재가 없습니다.")
        if self.finished_goods_quantity < 0:
            raise ValueError("완제품 수량은 0 이상이어야 합니다.")

        for index, line in enumerate(self.lines, 1):
            if not line.english_name.strip():
                raise ValueError(f"{index}행 자재 영문명이 없습니다.")
            if not line.packages:
                raise ValueError(f"{index}행 포장 수량 정보가 없습니다.")
            if line.packing_quantity <= 0:
                raise ValueError(f"{index}행 Packing 수량은 0보다 커야 합니다.")
            if any(
                value < 0
                for value in (
                    line.order_quantity,
                    line.loss,
                    line.weight_kg,
                    line.cbm,
                )
            ):
                raise ValueError(f"{index}행 수량, 중량, CBM은 0 이상이어야 합니다.")
            if any(
                package.order_quantity < 0 or package.loss < 0
                for package in line.packages
            ):
                raise ValueError(f"{index}행 포장별 수량은 0 이상이어야 합니다.")
            package_order = sum(
                (package.order_quantity for package in line.packages), Decimal()
            )
            package_loss = sum(
                (package.loss for package in line.packages), Decimal()
            )
            if package_order != line.order_quantity or package_loss != line.loss:
                raise ValueError(
                    f"{index}행의 포장별 수량/Loss 합계가 발주량/Loss와 다릅니다."
                )
