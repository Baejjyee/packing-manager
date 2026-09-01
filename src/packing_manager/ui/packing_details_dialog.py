"""Dialog for values that are not present in the purchase-order PDF."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from packing_manager.models import PackingLineDetails, PurchaseOrder
from packing_manager.services import parse_package_expression


class PackingDetailsDialog(QDialog):
    """Collect ship date, weight, CBM, and per-package quantities."""

    def __init__(self, order: PurchaseOrder, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.order = order
        self._details: list[PackingLineDetails] = []
        self.setWindowTitle("Packing 정보 입력")
        self.resize(900, 430)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.packing_list_number_edit = QLineEdit(order.on_code)
        self.shipping_date_edit = QDateEdit(QDate.currentDate())
        self.shipping_date_edit.setCalendarPopup(True)
        self.shipping_date_edit.setDisplayFormat("yyyy. MM. dd.")
        form.addRow("선적 LIST No.", self.packing_list_number_edit)
        form.addRow("선적일", self.shipping_date_edit)
        layout.addLayout(form)

        layout.addWidget(
            QLabel(
                "포장 구성 형식: 발주량+Loss*개수 — 예: 53+1*3, 8+2*1 "
                "(총 4개 Label 생성)"
            )
        )
        self.table = QTableWidget(len(order.materials), 4)
        self.table.setHorizontalHeaderLabels(
            ("자재", "중량(KG)", "C.B.M", "포장 구성")
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        for row, material in enumerate(order.materials):
            name = QTableWidgetItem(material.english_name or material.material_name)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, QTableWidgetItem("0"))
            self.table.setItem(row, 2, QTableWidgetItem("0"))
            expression = (
                f"{_number(material.order_quantity)}+{_number(material.loss)}*1"
            )
            self.table.setItem(row, 3, QTableWidgetItem(expression))
        self.table.setColumnWidth(0, 230)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 100)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def packing_list_number(self) -> str:
        return self.packing_list_number_edit.text().strip()

    def shipping_date(self) -> date:
        value = self.shipping_date_edit.date()
        return date(value.year(), value.month(), value.day())

    def line_details(self) -> list[PackingLineDetails]:
        return list(self._details)

    def _validate_and_accept(self) -> None:
        try:
            details: list[PackingLineDetails] = []
            for row, material in enumerate(self.order.materials):
                weight = _decimal(self._text(row, 1), f"{row + 1}행 중량")
                cbm = _decimal(self._text(row, 2), f"{row + 1}행 CBM")
                packages = parse_package_expression(self._text(row, 3))
                package_quantity = sum(
                    (package.order_quantity for package in packages), Decimal()
                )
                package_loss = sum(
                    (package.loss for package in packages), Decimal()
                )
                if package_quantity != material.order_quantity:
                    raise ValueError(
                        f"{row + 1}행 포장 발주량 합계 {package_quantity}가 "
                        f"발주량 {material.order_quantity}와 다릅니다."
                    )
                if package_loss != material.loss:
                    raise ValueError(
                        f"{row + 1}행 포장 Loss 합계 {package_loss}가 "
                        f"Loss {material.loss}와 다릅니다."
                    )
                details.append(PackingLineDetails(weight, cbm, packages))
        except ValueError as exc:
            QMessageBox.warning(self, "포장 정보 확인", str(exc))
            return
        self._details = details
        self.accept()

    def _text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item else ""


def _decimal(value: str, label: str) -> Decimal:
    try:
        number = Decimal(value.replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{label}은(는) 숫자로 입력해 주세요.") from exc
    if number < 0:
        raise ValueError(f"{label}은(는) 0 이상이어야 합니다.")
    return number


def _number(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value, "f")
