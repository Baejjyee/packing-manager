"""Application bootstrap code."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .database import TranslationRepository
from .services import (
    OrderReviewService,
    PackingDocumentService,
    PackingService,
    TranslationService,
)
from .ui.main_window import MainWindow


def run() -> int:
    """Create and run the Qt application."""
    app = QApplication.instance() or QApplication(sys.argv)
    repository = TranslationRepository()
    repository.initialize()
    review_service = OrderReviewService(
        PackingService(), TranslationService(repository)
    )
    printer = None
    if sys.platform == "win32":
        from .printing.windows_printer import WindowsPrinter

        printer = WindowsPrinter()
    window = MainWindow(review_service, PackingDocumentService(), printer)
    if "--smoke-test" in sys.argv:
        window.close()
        return 0
    window.show()
    return app.exec()
