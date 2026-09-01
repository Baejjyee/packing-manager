from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pdfplumber

from packing_manager.models import PackingDocument, PackingLine, PackingPackage
from packing_manager.services import PackingPdfGenerator
from packing_manager.services.pdf_generator import _label_pages


def _document() -> PackingDocument:
    return PackingDocument(
        supplier="(주)테스트섬유",
        buyer="MLB",
        po_number="ON260983",
        item_name="CHUNKY LINER MONOGRAM",
        finished_goods_quantity=Decimal("12030"),
        shipping_date=date(2026, 9, 18),
        packing_list_number="PL-260983",
        lines=[
            PackingLine(
                material_name="메쉬 A",
                english_name="CORDURA MESH",
                specification='44"',
                color="N-WHITE3",
                unit="YD",
                order_quantity=Decimal("100"),
                loss=Decimal("2"),
                weight_kg=Decimal("20.5"),
                cbm=Decimal("0.10"),
                packages=[
                    PackingPackage(Decimal("50"), Decimal("1")),
                    PackingPackage(Decimal("50"), Decimal("1")),
                ],
            ),
            PackingLine(
                material_name="메쉬 B",
                english_name="HEAVY MERRY MESH",
                specification='44"',
                color="PINK",
                unit="YD",
                order_quantity=Decimal("30"),
                loss=Decimal("1"),
                weight_kg=Decimal("8.2"),
                cbm=Decimal("0.05"),
                packages=[PackingPackage(Decimal("30"), Decimal("1"))],
            ),
        ],
    )


class PackingPdfGeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.output_directory = Path(self.temp_directory.name)
        self.generator = PackingPdfGenerator()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_generates_packing_list_with_expected_content(self) -> None:
        output = self.output_directory / "packing-list.pdf"

        self.generator.create_packing_list(_document(), output)

        with pdfplumber.open(output) as pdf:
            self.assertEqual(len(pdf.pages), 1)
            text = pdf.pages[0].extract_text()
        self.assertIn("PACKING LIST", text)
        self.assertIn("CORDURA MESH", text)
        self.assertIn("133", text)

    def test_generates_two_labels_per_page(self) -> None:
        output = self.output_directory / "labels.pdf"

        self.generator.create_packing_labels(_document(), output)

        with pdfplumber.open(output) as pdf:
            self.assertEqual(len(pdf.pages), 2)
            first_page = pdf.pages[0].extract_text()
            second_page = pdf.pages[1].extract_text()
        self.assertIn("P/G NO : 1", first_page)
        self.assertIn("P/G NO : 2", first_page)
        self.assertIn("P/G NO : 3", second_page)

    def test_rejects_package_totals_that_do_not_match_line(self) -> None:
        document = _document()
        document.lines[0].packages[0].order_quantity = Decimal("49")

        with self.assertRaises(ValueError):
            self.generator.create_packing_list(
                document, self.output_directory / "invalid.pdf"
            )

    def test_pairs_material_counts_in_strict_sequential_order(self) -> None:
        def line(name: str, count: int) -> PackingLine:
            return PackingLine(
                material_name=name,
                english_name=name,
                specification="",
                color="",
                unit="YD",
                order_quantity=Decimal(count),
                loss=Decimal(),
                packages=[PackingPackage(Decimal("1")) for _ in range(count)],
            )

        pages = _label_pages(
            [line("A", 5), line("B", 3), line("C", 2), line("D", 5)]
        )
        material_pairs = [
            (
                left[1].material_name,
                right[1].material_name if right is not None else None,
            )
            for left, right in pages
        ]

        self.assertEqual(
            material_pairs,
            [
                ("A", "A"),
                ("A", "A"),
                ("A", "B"),
                ("B", "B"),
                ("C", "C"),
                ("D", "D"),
                ("D", "D"),
                ("D", None),
            ],
        )


if __name__ == "__main__":
    unittest.main()
