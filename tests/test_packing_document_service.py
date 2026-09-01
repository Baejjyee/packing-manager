from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

from packing_manager.models import MaterialItem, PackingLineDetails, PurchaseOrder
from packing_manager.services import PackingDocumentService, parse_package_expression


class StubGenerator:
    def __init__(self) -> None:
        self.outputs: list[Path] = []

    def create_packing_list(self, document, output_path: Path) -> None:  # noqa: ANN001
        self.outputs.append(output_path)

    def create_packing_labels(self, document, output_path: Path) -> None:  # noqa: ANN001
        self.outputs.append(output_path)


class PackingDocumentServiceTest(unittest.TestCase):
    def test_parses_compact_package_expression(self) -> None:
        packages = parse_package_expression("53+1*3, 8+2*1")

        self.assertEqual(len(packages), 4)
        self.assertEqual(
            sum((package.order_quantity for package in packages), Decimal()),
            Decimal("167"),
        )
        self.assertEqual(
            sum((package.loss for package in packages), Decimal()), Decimal("5")
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
                parse_package_expression("53+1*3, 8+2*1"),
            )
        ]
        generator = StubGenerator()
        service = PackingDocumentService(generator=generator)

        document = service.build_document(
            order, date(2026, 9, 18), "PL-1", details
        )
        service.generate(document, Path("list.pdf"), Path("labels.pdf"))

        self.assertEqual(len(document.lines[0].packages), 4)
        self.assertEqual(generator.outputs, [Path("list.pdf"), Path("labels.pdf")])

    def test_rejects_invalid_expression(self) -> None:
        with self.assertRaises(ValueError):
            parse_package_expression("not-a-package")


if __name__ == "__main__":
    unittest.main()
