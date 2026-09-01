"""Dialog for English names missing from the translation database."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from packing_manager.services import MissingTranslation


class TranslationDialog(QDialog):
    """Collect English translations from the user."""

    def __init__(
        self, missing: list[MissingTranslation], parent=None  # noqa: ANN001
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("미등록 영문명 입력")
        self.setMinimumWidth(620)
        self._editors: dict[MissingTranslation, QLineEdit] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel("등록되지 않은 영문명을 입력하면 다음 발주서부터 자동 적용됩니다.")
        )
        form = QFormLayout()
        for item in missing:
            editor = QLineEdit()
            editor.setPlaceholderText("영문명")
            kind = "ERP품목" if item.kind == "erp_item" else "자재"
            form.addRow(f"{kind}: {item.korean_name}", editor)
            self._editors[item] = editor
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def translations(self) -> dict[MissingTranslation, str]:
        """Return trimmed values entered by the user."""
        return {item: editor.text().strip() for item, editor in self._editors.items()}

    def _validate_and_accept(self) -> None:
        empty = [
            item.korean_name
            for item, editor in self._editors.items()
            if not editor.text().strip()
        ]
        if empty:
            QMessageBox.warning(self, "입력 확인", "모든 영문명을 입력해 주세요.")
            return
        self.accept()
