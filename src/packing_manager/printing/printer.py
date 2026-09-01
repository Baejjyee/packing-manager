"""Platform-independent printer contract."""

from pathlib import Path
from typing import Protocol


class Printer(Protocol):
    """Contract implemented by platform-specific PDF printers."""

    def print_pdf(self, pdf_path: Path, parent: object | None = None) -> bool:
        """Send a PDF file to a printer; return false when the user cancels."""
        ...
