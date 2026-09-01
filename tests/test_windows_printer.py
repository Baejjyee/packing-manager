from pathlib import Path
from unittest.mock import patch
import unittest

from packing_manager.printing.windows_printer import (
    WindowsPrinter,
    _selected_page_indexes,
)


class WindowsPrinterTest(unittest.TestCase):
    def test_rejects_use_outside_windows_before_loading_printer_modules(self) -> None:
        with patch(
            "packing_manager.printing.windows_printer.sys.platform", "darwin"
        ):
            with self.assertRaises(OSError):
                WindowsPrinter().print_pdf(Path("labels.pdf"))

    def test_translates_all_pages_and_selected_ranges(self) -> None:
        self.assertEqual(list(_selected_page_indexes(8, 0, 0)), list(range(8)))
        self.assertEqual(list(_selected_page_indexes(8, 3, 5)), [2, 3, 4])

    def test_rejects_invalid_page_range(self) -> None:
        with self.assertRaises(ValueError):
            _selected_page_indexes(8, 7, 3)


if __name__ == "__main__":
    unittest.main()
