from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

from packing_manager.models import MaterialItem, PackingLineDetails, PurchaseOrder
from packing_manager.services import (
    PackingDocumentService,
    build_equal_packages,
)


class StubGenerator:
    def __init__(self) -> None:
        self.outputs: list[Path] = []

    def create_packing_list(self, document, output_path: Path) -> None:  # noqa: ANN001
        self.outputs.append(output_path)

    def create_packing_labels(self, document, output_path: Path) -> None:  # noqa: ANN001
        self.outputs.append(output_path)


class PackingDocumentServiceTest(unittest.TestCase):
    def test_splits_total_quantity_by_default_packing_quantity(self) -> None:
        packages = build_equal_packages(Decimal("191"), Decimal("6"))

        self.assertEqual(
            [package.total_quantity for package in packages],
            [Decimal("54"), Decimal("54"), Decimal("54"), Decimal("35")],
        )
        self.assertEqual(
            sum((package.order_quantity for package in packages), Decimal()),
            Decimal("191"),
        )
        self.assertEqual(
            sum((package.loss for package in packages), Decimal()), Decimal("6")
        )

    def test_calculates_sample_order_roll_counts(self) -> None:
        cases = (
            ("191", "6", 4),
            ("1818", "53", 35),
            ("330", "10", 7),
        )
        for order_quantity, loss, expected_count in cases:
            with self.subTest(order_quantity=order_quantity, loss=loss):
                packages = build_equal_packages(
                    Decimal(order_quantity), Decimal(loss), Decimal("54")
                )
                self.assertEqual(len(packages), expected_count)

    def test_uses_user_selected_packing_quantity(self) -> None:
        packages = build_equal_packages(
            Decimal("191"), Decimal("6"), Decimal("50")
        )

        self.assertEqual(
            [package.total_quantity for package in packages],
            [Decimal("50"), Decimal("50"), Decimal("50"), Decimal("47")],
        )

    def test_builds_document_and_delegates_both_pdfs(self) -> None:
        order = PurchaseOrder(
            supplier="공급처",
            brand="MLB",
            on_code="ON123456",
            erp_item_name="제품",
            erp_item_english_name="PRODUCT",
            finished_goods_quantity=Decimal("100"),
            materials=[
                MaterialItem(
                    "메쉬",
                    '44"',
                    "WHITE",
                    Decimal("167"),
                    Decimal("5"),
                    "YD",
                    "MESH",
                )
            ],
        )
        details = [
            PackingLineDetails(
                Decimal("32.7"),
                Decimal("0.10"),
                build_equal_packages(Decimal("167"), Decimal("5")),
            )
        ]
        generator = StubGenerator()
        service = PackingDocumentService(generator=generator)

        document = service.build_document(
            order, date(2026, 9, 18), "PL-1", details
        )
        service.generate(document, Path("list.pdf"), Path("labels.pdf"))

        self.assertEqual(len(document.lines[0].packages), 4)
        self.assertEqual(document.lines[0].packing_quantity, Decimal("54"))
        self.assertEqual(generator.outputs, [Path("list.pdf"), Path("labels.pdf")])

if __name__ == "__main__":
    unittest.main()
