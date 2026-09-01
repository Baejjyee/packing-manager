"""Windows-only PDF printing through Qt and the native printer driver."""

from __future__ import annotations

import sys
from pathlib import Path


class WindowsPrinter:
    """Print each prepared A4 PDF page as one physical A4 sheet."""

    def print_pdf(self, pdf_path: Path, parent: object | None = None) -> bool:
        """Show the native dialog and print an A4 landscape PDF.

        Label pairing is deliberately not performed here. The input PDF must
        already contain the left/right two-up pages in their final order.
        """
        if sys.platform != "win32":
            raise OSError("WindowsPrinter is available only on Windows.")

        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"출력할 PDF를 찾을 수 없습니다: {path}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("출력 파일 확장자는 .pdf여야 합니다.")

        # Imports remain inside the Windows adapter so other platforms never
        # load printer-specific Qt modules as part of the normal app workflow.
        from PySide6.QtCore import QMarginsF, QRectF, Qt
        from PySide6.QtGui import QPageLayout, QPageSize, QPainter
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        from PySide6.QtWidgets import QDialog

        document = QPdfDocument()
        error = document.load(str(path))
        if error != QPdfDocument.Error.None_ or document.pageCount() < 1:
            raise OSError(f"PDF를 열 수 없습니다: {path.name}")

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(path.name)
        _configure_a4_landscape(printer, QMarginsF, QPageLayout, QPageSize, QPrinter)

        dialog = QPrintDialog(printer, parent)
        dialog.setWindowTitle("Packing Label 프린트")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            document.close()
            return False

        # Reapply the required physical layout after the native dialog. Printer
        # drivers may otherwise retain a previous duplex/portrait preference.
        _configure_a4_landscape(printer, QMarginsF, QPageLayout, QPageSize, QPrinter)
        if not printer.isValid():
            document.close()
            raise OSError("선택한 프린터를 사용할 수 없습니다.")

        page_indexes = _selected_page_indexes(
            document.pageCount(), printer.fromPage(), printer.toPage()
        )
        painter = QPainter()
        if not painter.begin(printer):
            document.close()
            raise OSError("프린터 출력 작업을 시작할 수 없습니다.")

        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            for output_index, page_index in enumerate(page_indexes):
                if output_index and not printer.newPage():
                    raise OSError("다음 출력 페이지를 만들 수 없습니다.")

                target = QRectF(printer.paperRect(QPrinter.Unit.DevicePixel))
                image_size = target.size().toSize()
                image = document.render(page_index, image_size)
                if image.isNull():
                    raise OSError(f"PDF {page_index + 1}페이지를 렌더링할 수 없습니다.")
                painter.drawImage(target, image)
        finally:
            painter.end()
            document.close()
        return True


def _configure_a4_landscape(
    printer: object,
    margins_type: object,
    page_layout_type: object,
    page_size_type: object,
    printer_type: object,
) -> None:
    """Set the non-negotiable label sheet settings."""
    layout = page_layout_type(
        page_size_type(page_size_type.PageSizeId.A4),
        page_layout_type.Orientation.Landscape,
        margins_type(0, 0, 0, 0),
        page_layout_type.Unit.Millimeter,
    )
    printer.setPageLayout(layout)
    printer.setFullPage(True)
    printer.setDuplex(printer_type.DuplexMode.DuplexNone)
    printer.setResolution(300)


def _selected_page_indexes(
    page_count: int, from_page: int, to_page: int
) -> range:
    """Translate QPrinter's 1-based optional page range to Python indexes."""
    start = max(from_page, 1) if from_page else 1
    end = min(to_page, page_count) if to_page else page_count
    if start > end:
        raise ValueError("출력 페이지 범위가 올바르지 않습니다.")
    return range(start - 1, end)
