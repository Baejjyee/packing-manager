from decimal import Decimal
import unittest

from packing_manager.models import MaterialItem
from packing_manager.services import merge_materials


class MergeMaterialsTest(unittest.TestCase):
    def test_merges_matching_rows_and_sums_quantity_and_loss(self) -> None:
        rows = [
            MaterialItem("메쉬", '44"', "WHITE", Decimal("416"), Decimal("12"), "YD"),
            MaterialItem("메쉬", '44"', "WHITE", Decimal("413"), Decimal("12"), "YD"),
            MaterialItem("메쉬", '44"', "PINK", Decimal("330"), Decimal("10"), "YD"),
            MaterialItem("메쉬", '44"', "WHITE", Decimal("344"), Decimal("10"), "YD"),
            MaterialItem("메쉬", '44"', "WHITE", Decimal("645"), Decimal("19"), "YD"),
        ]

        merged = merge_materials(rows)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].order_quantity, Decimal("1818"))
        self.assertEqual(merged[0].loss, Decimal("53"))
        self.assertEqual(merged[0].total_quantity, Decimal("1871"))
        self.assertEqual(merged[1].color, "PINK")

    def test_does_not_modify_input_rows(self) -> None:
        row = MaterialItem("메쉬", '44"', "WHITE", Decimal("10"), Decimal("1"), "YD")

        merge_materials([row, row])

        self.assertEqual(row.order_quantity, Decimal("10"))
        self.assertEqual(row.loss, Decimal("1"))

    def test_rejects_different_units_for_same_merge_key(self) -> None:
        rows = [
            MaterialItem("메쉬", '44"', "WHITE", Decimal("10"), unit="YD"),
            MaterialItem("메쉬", '44"', "WHITE", Decimal("10"), unit="M"),
        ]

        with self.assertRaises(ValueError):
            merge_materials(rows)


if __name__ == "__main__":
    unittest.main()
