"""Dialog for values that are not present in the purchase-order PDF."""

from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from packing_manager.models import PackingLineDetails, PurchaseOrder
from packing_manager.services import build_equal_packages


_DEFAULT_PACKING_QUANTITY = Decimal("54")


class PackingDetailsDialog(QDialog):
    """Collect physical values and preview automatically divided rolls."""

    def __init__(self, order: PurchaseOrder, parent=None) -> None:  # noqa: ANN001
        super().__init__(parent)
        self.order = order
        self._details: list[PackingLineDetails] = []
        self.setWindowTitle("Packing 정보 입력")
        self.resize(1120, 470)

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
                "Packing 내역은 (발주량 + Loss) ÷ Packing 수량으로 자동 계산됩니다. "
                "Packing 수량 기본값은 54이며 자재별로 수정할 수 있습니다."
            )
        )
        self.table = QTableWidget(len(order.materials), 7)
        self.table.setHorizontalHeaderLabels(
            (
                "자재",
                "총수량",
                "중량(KG)",
                "C.B.M",
                "Packing 수량",
                "PACKING 내역",
                "R/L 수",
            )
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        self.table.verticalHeader().setVisible(False)
        for row, material in enumerate(order.materials):
            packages = build_equal_packages(
                material.order_quantity,
                material.loss,
                _DEFAULT_PACKING_QUANTITY,
            )
            self.table.setItem(
                row,
                0,
                _readonly_item(material.english_name or material.material_name),
            )
            self.table.setItem(
                row, 1, _readonly_item(_number(material.total_quantity), right=True)
            )
            self.table.setItem(row, 2, QTableWidgetItem("0"))
            self.table.setItem(row, 3, QTableWidgetItem("0"))
            self.table.setItem(
                row, 4, QTableWidgetItem(_number(_DEFAULT_PACKING_QUANTITY))
            )
            self.table.setItem(row, 5, _readonly_item(_package_summary(packages)))
            self.table.setItem(
                row, 6, _readonly_item(str(len(packages)), right=True)
            )
        for column in (1, 2, 3, 4, 6):
            self.table.setColumnWidth(column, 105)
        self.table.cellChanged.connect(self._refresh_calculation)
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
                weight = _decimal(self._text(row, 2), f"{row + 1}행 중량")
                cbm = _decimal(self._text(row, 3), f"{row + 1}행 CBM")
                packing_quantity = _decimal(
                    self._text(row, 4), f"{row + 1}행 Packing 수량"
                )
                packages = build_equal_packages(
                    material.order_quantity,
                    material.loss,
                    packing_quantity,
                )
                details.append(
                    PackingLineDetails(
                        weight,
                        cbm,
                        packages,
                        packing_quantity=packing_quantity,
                    )
                )
        except ValueError as exc:
            QMessageBox.warning(self, "포장 정보 확인", str(exc))
            return
        self._details = details
        self.accept()

    def _refresh_calculation(self, row: int, column: int) -> None:
        if column != 4 or not 0 <= row < len(self.order.materials):
            return
        material = self.order.materials[row]
        try:
            packing_quantity = _decimal(
                self._text(row, 4), f"{row + 1}행 Packing 수량"
            )
            packages = build_equal_packages(
                material.order_quantity, material.loss, packing_quantity
            )
            summary = _package_summary(packages)
            roll_count = str(len(packages))
        except ValueError:
            summary = "입력 확인"
            roll_count = "-"

        self.table.blockSignals(True)
        self.table.item(row, 5).setText(summary)
        self.table.item(row, 6).setText(roll_count)
        self.table.blockSignals(False)

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


def _package_summary(packages) -> str:  # noqa: ANN001
    totals = [_number(package.total_quantity) for package in packages]
    counts = Counter(totals)
    return "  ".join(f"{quantity}*{count}" for quantity, count in counts.items())


def _readonly_item(value: str, *, right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(value)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if right:
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
    return item
