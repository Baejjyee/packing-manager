from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from packing_manager.database import TranslationRepository
from packing_manager.models import MaterialItem, PurchaseOrder
from packing_manager.services import MissingTranslation, TranslationService


class TranslationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        repository = TranslationRepository(
            Path(self.temp_directory.name) / "translations.db"
        )
        repository.initialize()
        repository.save_erp_item_translation("완제품", "Finished Product")
        repository.save_material_translation("메쉬", "Mesh")
        self.service = TranslationService(repository)

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_applies_known_names_and_returns_unique_missing_names(self) -> None:
        order = PurchaseOrder(
            erp_item_name="완제품",
            materials=[
                MaterialItem("메쉬", order_quantity=Decimal("1")),
                MaterialItem("원단", color="WHITE", order_quantity=Decimal("2")),
                MaterialItem("원단", color="PINK", order_quantity=Decimal("3")),
            ],
        )

        missing = self.service.apply_known_translations(order)

        self.assertEqual(order.erp_item_english_name, "Finished Product")
        self.assertEqual(order.materials[0].english_name, "Mesh")
        self.assertEqual(
            missing, [MissingTranslation("material", "원단")]
        )

    def test_saves_user_input_for_later_lookup(self) -> None:
        request = MissingTranslation("material", "원단")
        self.service.save_translation(request, "Fabric")
        order = PurchaseOrder(materials=[MaterialItem("원단")])

        missing = self.service.apply_known_translations(order)

        self.assertEqual(missing, [])
        self.assertEqual(order.materials[0].english_name, "Fabric")


if __name__ == "__main__":
    unittest.main()
