"""Main order-review window."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from packing_manager.config import OUTPUT_DIR
from packing_manager.models import MaterialItem, OrderReviewSession
from packing_manager.printing import Printer
from packing_manager.services import OrderReviewService, PackingDocumentService

from .packing_details_dialog import PackingDetailsDialog
from .translation_dialog import TranslationDialog


_COLUMNS = (
    "자재명",
    "영문명",
    "규격",
    "색상",
    "단위",
    "발주량",
    "Loss",
    "총수량",
)
_CHANGED_COLOR = QColor("#fff1b8")


class MainWindow(QMainWindow):
    """Allow the user to load, inspect, and edit extracted order data."""

    def __init__(
        self,
        review_service: OrderReviewService,
        document_service: PackingDocumentService,
        printer: Printer | None = None,
    ) -> None:
        super().__init__()
        self.review_service = review_service
        self.document_service = document_service
        self.printer = printer
        self.session: OrderReviewSession | None = None
        self.last_label_path: Path | None = None

        self.setWindowTitle("Packing Manager")
        self.resize(1180, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        toolbar = QHBoxLayout()
        self.open_button = QPushButton("자재발주서 PDF 선택")
        self.open_button.clicked.connect(self._choose_pdf)
        toolbar.addWidget(self.open_button)
        self.file_label = QLabel("선택된 파일 없음")
        toolbar.addWidget(self.file_label, 1)
        self.apply_button = QPushButton("변경사항 적용")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._apply_changes)
        toolbar.addWidget(self.apply_button)
        self.generate_button = QPushButton("Packing PDF 생성")
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self._generate_pdfs)
        toolbar.addWidget(self.generate_button)
        self.print_button = QPushButton("Label 프린트")
        self.print_button.setEnabled(False)
        self.print_button.clicked.connect(self._print_labels)
        toolbar.addWidget(self.print_button)
        layout.addLayout(toolbar)

        information = QGroupBox("완제품 오더 정보")
        form = QFormLayout(information)
        self.supplier_edit = QLineEdit()
        self.on_code_edit = QLineEdit()
        self.brand_edit = QLineEdit()
        self.erp_item_edit = QLineEdit()
        self.erp_english_edit = QLineEdit()
        self.finished_quantity_edit = QLineEdit()
        form.addRow("공급처", self.supplier_edit)
        form.addRow("ON코드", self.on_code_edit)
        form.addRow("브랜드", self.brand_edit)
        form.addRow("ERP품목명", self.erp_item_edit)
        form.addRow("ERP품목 영문명", self.erp_english_edit)
        form.addRow("완제품 수량", self.finished_quantity_edit)
        layout.addWidget(information)

        materials = QGroupBox("자재 상세내역 (노란색은 추출 원본에서 변경된 값)")
        material_layout = QVBoxLayout(materials)
        self.material_table = QTableWidget(0, len(_COLUMNS))
        self.material_table.setHorizontalHeaderLabels(_COLUMNS)
        self.material_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.material_table.verticalHeader().setVisible(False)
        material_layout.addWidget(self.material_table)
        layout.addWidget(materials, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("자재발주서 PDF를 선택해 주세요.")

    def _choose_pdf(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "자재발주서 선택",
            str(Path.home()),
            "PDF 파일 (*.pdf)",
        )
        if not file_name:
            return

        try:
            session = self.review_service.load(Path(file_name))
        except Exception as exc:
            QMessageBox.critical(self, "PDF 처리 오류", str(exc))
            return

        self.session = session
        self._populate(session)
        self.file_label.setText(session.source_path.name)
        self.apply_button.setEnabled(True)
        self.generate_button.setEnabled(True)

        if session.missing_translations:
            self._request_missing_translations(session)
        else:
            self.statusBar().showMessage("PDF 추출이 완료되었습니다.")

    def _request_missing_translations(self, session: OrderReviewSession) -> None:
        missing = list(session.missing_translations)
        dialog = TranslationDialog(missing, self)
        if dialog.exec() != TranslationDialog.DialogCode.Accepted:
            self.statusBar().showMessage(
                f"PDF 추출 완료 · 미등록 영문명 {len(missing)}개"
            )
            return

        try:
            self.review_service.save_missing_translations(
                session, dialog.translations()
            )
        except Exception as exc:
            QMessageBox.critical(self, "영문명 저장 오류", str(exc))
            return
        self._populate(session)
        self.statusBar().showMessage("PDF 추출 및 영문명 저장이 완료되었습니다.")

    def _populate(self, session: OrderReviewSession) -> None:
        order = session.current_order
        self.supplier_edit.setText(order.supplier)
        self.on_code_edit.setText(order.on_code)
        self.brand_edit.setText(order.brand)
        self.erp_item_edit.setText(order.erp_item_name)
        self.erp_english_edit.setText(order.erp_item_english_name or "")
        self.finished_quantity_edit.setText(_format_decimal(order.finished_goods_quantity))

        self.material_table.setRowCount(len(order.materials))
        for row_index, material in enumerate(order.materials):
            values = _material_values(material)
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column_index >= 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if column_index == 7:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.material_table.setItem(row_index, column_index, item)
        self._highlight_changes()

    def _apply_changes(self) -> None:
        if self.session is None:
            return
        try:
            self._update_current_order(self.session)
        except ValueError as exc:
            QMessageBox.warning(self, "입력값 확인", str(exc))
            return
        self._populate(self.session)
        self.statusBar().showMessage("변경사항을 작업 데이터에 적용했습니다.")

    def _generate_pdfs(self) -> None:
        if self.session is None:
            return
        try:
            self._update_current_order(self.session)
        except ValueError as exc:
            QMessageBox.warning(self, "입력값 확인", str(exc))
            return

        order = self.session.current_order
        dialog = PackingDetailsDialog(order, self)
        if dialog.exec() != PackingDetailsDialog.DialogCode.Accepted:
            return

        try:
            document = self.document_service.build_document(
                order,
                dialog.shipping_date(),
                dialog.packing_list_number(),
                dialog.line_details(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Packing 정보 확인", str(exc))
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        directory = QFileDialog.getExistingDirectory(
            self, "PDF 저장 폴더 선택", str(OUTPUT_DIR)
        )
        if not directory:
            return
        output_directory = Path(directory)
        stem = _safe_file_stem(order.on_code)
        packing_list_path = output_directory / f"{stem}_packing_list.pdf"
        label_path = output_directory / f"{stem}_packing_labels.pdf"
        if packing_list_path.exists() or label_path.exists():
            answer = QMessageBox.question(
                self,
                "파일 덮어쓰기",
                "같은 이름의 PDF가 있습니다. 덮어쓸까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            self.document_service.generate(
                document, packing_list_path, label_path
            )
        except Exception as exc:
            QMessageBox.critical(self, "PDF 생성 오류", str(exc))
            return
        self.last_label_path = label_path
        self.print_button.setEnabled(self.printer is not None)
        self.statusBar().showMessage(
            f"PDF 생성 완료: {packing_list_path.name}, {label_path.name}"
        )
        QMessageBox.information(
            self,
            "PDF 생성 완료",
            f"Packing List:\n{packing_list_path}\n\nPacking Labels:\n{label_path}",
        )

    def _print_labels(self) -> None:
        if self.printer is None or self.last_label_path is None:
            QMessageBox.information(
                self, "프린트 안내", "Windows에서 Label PDF를 먼저 생성해 주세요."
            )
            return
        try:
            printed = self.printer.print_pdf(self.last_label_path, self)
        except Exception as exc:
            QMessageBox.critical(self, "프린트 오류", str(exc))
            return
        if printed:
            self.statusBar().showMessage(
                f"프린터로 전송했습니다: {self.last_label_path.name}"
            )

    def _update_current_order(self, session: OrderReviewSession) -> None:
        order = session.current_order
        order.supplier = _required(self.supplier_edit.text(), "공급처")
        order.on_code = _required(self.on_code_edit.text(), "ON코드")
        order.brand = _required(self.brand_edit.text(), "브랜드")
        order.erp_item_name = _required(self.erp_item_edit.text(), "ERP품목명")
        order.erp_item_english_name = self.erp_english_edit.text().strip() or None
        order.finished_goods_quantity = _decimal(
            self.finished_quantity_edit.text(), "완제품 수량"
        )

        for row_index, material in enumerate(order.materials):
            material.material_name = _required(
                self._table_text(row_index, 0), f"{row_index + 1}행 자재명"
            )
            material.english_name = self._table_text(row_index, 1) or None
            material.specification = self._table_text(row_index, 2)
            material.color = self._table_text(row_index, 3)
            material.unit = _required(
                self._table_text(row_index, 4), f"{row_index + 1}행 단위"
            )
            material.order_quantity = _decimal(
                self._table_text(row_index, 5), f"{row_index + 1}행 발주량"
            )
            material.loss = _decimal(
                self._table_text(row_index, 6), f"{row_index + 1}행 Loss"
            )

    def _table_text(self, row: int, column: int) -> str:
        item = self.material_table.item(row, column)
        return item.text().strip() if item else ""

    def _highlight_changes(self) -> None:
        if self.session is None:
            return
        current = self.session.current_order
        extracted = self.session.extracted_order
        field_pairs = (
            (self.supplier_edit, current.supplier, extracted.supplier),
            (self.on_code_edit, current.on_code, extracted.on_code),
            (self.brand_edit, current.brand, extracted.brand),
            (self.erp_item_edit, current.erp_item_name, extracted.erp_item_name),
            (
                self.erp_english_edit,
                current.erp_item_english_name,
                extracted.erp_item_english_name,
            ),
            (
                self.finished_quantity_edit,
                current.finished_goods_quantity,
                extracted.finished_goods_quantity,
            ),
        )
        for editor, current_value, extracted_value in field_pairs:
            editor.setStyleSheet(
                "background-color: #fff1b8;" if current_value != extracted_value else ""
            )

        for row_index, material in enumerate(current.materials):
            original = (
                extracted.materials[row_index]
                if row_index < len(extracted.materials)
                else None
            )
            current_values = _material_comparison_values(material)
            original_values = (
                _material_comparison_values(original) if original else (None,) * 8
            )
            for column_index, value in enumerate(current_values):
                item = self.material_table.item(row_index, column_index)
                if item and value != original_values[column_index]:
                    item.setBackground(_CHANGED_COLOR)


def _material_values(material: MaterialItem) -> tuple[str, ...]:
    return (
        material.material_name,
        material.english_name or "",
        material.specification,
        material.color,
        material.unit,
        _format_decimal(material.order_quantity),
        _format_decimal(material.loss),
        _format_decimal(material.total_quantity),
    )


def _material_comparison_values(material: MaterialItem) -> tuple[object, ...]:
    return (
        material.material_name,
        material.english_name,
        material.specification,
        material.color,
        material.unit,
        material.order_quantity,
        material.loss,
        material.total_quantity,
    )


def _required(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label}을(를) 입력해 주세요.")
    return normalized


def _decimal(value: str, label: str) -> Decimal:
    try:
        number = Decimal(value.replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{label}은(는) 숫자로 입력해 주세요.") from exc
    if number < 0:
        raise ValueError(f"{label}은(는) 0 이상이어야 합니다.")
    return number


def _format_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return f"{int(value):,}"
    return format(value, "f")


def _safe_file_stem(value: str) -> str:
    safe = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in value.strip()
    )
    return safe.strip("_") or "packing"
