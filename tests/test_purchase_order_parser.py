from decimal import Decimal
import unittest

from packing_manager.pdf_parser import PurchaseOrderParseError, PurchaseOrderParser


SAMPLE_TABLE = [
    ["공급처명", "테스트 공급처", "공급처코드", "10000"],
    ["ON코드", "ON123456", "ERP품목명", "테스트 제품", "브랜드", "TEST"],
    ["오더상태", "", "수량", "12,030", "색상", "WHITE"],
    ["No.", "품 명", "가공조건", "규격", "색상", "단위", "발주량", "Loss", "총 수량"],
    ["1", "메쉬", "", '44"', "WHITE", "YD", "416", "12", "428"],
    ["2", "메쉬", "", '44"', "WHITE", "YD", "413", "12", "425"],
    ["", "", "", "", "TOTAL", "", "829", "24", "853"],
]


class PurchaseOrderParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = PurchaseOrderParser()

    def test_extracts_order_fields_and_material_rows(self) -> None:
        order = self.parser._parse_tables([SAMPLE_TABLE])

        self.assertEqual(order.supplier, "테스트 공급처")
        self.assertEqual(order.on_code, "ON123456")
        self.assertEqual(order.brand, "TEST")
        self.assertEqual(order.erp_item_name, "테스트 제품")
        self.assertEqual(order.finished_goods_quantity, Decimal("12030"))
        self.assertEqual(len(order.materials), 2)
        self.assertEqual(order.materials[0].order_quantity, Decimal("416"))
        self.assertEqual(order.materials[0].loss, Decimal("12"))

    def test_rejects_tables_missing_required_fields(self) -> None:
        with self.assertRaises(PurchaseOrderParseError):
            self.parser._parse_tables([[['ON코드', 'ON123456']]])


if __name__ == "__main__":
    unittest.main()
