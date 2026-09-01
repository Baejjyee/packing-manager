from decimal import Decimal
from pathlib import Path
import unittest

from packing_manager.models import MaterialItem, PurchaseOrder
from packing_manager.services import PackingService


class StubParser:
    def parse(self, pdf_path: Path) -> PurchaseOrder:
        return PurchaseOrder(
            on_code="ON123456",
            materials=[
                MaterialItem("메쉬", '44"', "WHITE", Decimal("10"), Decimal("1"), "YD"),
                MaterialItem("메쉬", '44"', "WHITE", Decimal("20"), Decimal("2"), "YD"),
            ],
        )


class PackingServiceTest(unittest.TestCase):
    def test_load_purchase_order_parses_and_merges_materials(self) -> None:
        service = PackingService(parser=StubParser())

        order = service.load_purchase_order(Path("sample.pdf"))

        self.assertEqual(order.on_code, "ON123456")
        self.assertEqual(len(order.materials), 1)
        self.assertEqual(order.materials[0].order_quantity, Decimal("30"))
        self.assertEqual(order.materials[0].loss, Decimal("3"))


if __name__ == "__main__":
    unittest.main()
