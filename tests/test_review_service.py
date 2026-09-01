from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from packing_manager.database import TranslationRepository
from packing_manager.models import MaterialItem, MissingTranslation, PurchaseOrder
from packing_manager.services import (
    OrderReviewService,
    PackingService,
    TranslationService,
)


class StubParser:
    def parse(self, pdf_path: Path) -> PurchaseOrder:
        return PurchaseOrder(
            supplier="원본 공급처",
            on_code="ON123456",
            brand="TEST",
            erp_item_name="완제품",
            finished_goods_quantity=Decimal("100"),
            materials=[
                MaterialItem("메쉬", '44"', "WHITE", Decimal("10"), unit="YD"),
                MaterialItem("원단", '44"', "PINK", Decimal("20"), unit="YD"),
            ],
        )


class OrderReviewServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        self.repository = TranslationRepository(
            Path(self.temp_directory.name) / "translations.db"
        )
        self.repository.initialize()
        self.repository.save_material_translation("메쉬", "Mesh")
        self.service = OrderReviewService(
            PackingService(StubParser()), TranslationService(self.repository)
        )

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_keeps_extracted_and_editable_orders_separate(self) -> None:
        session = self.service.load(Path("sample.pdf"))

        self.assertIsNot(session.extracted_order, session.current_order)
        self.assertIsNone(session.extracted_order.materials[0].english_name)
        self.assertEqual(session.current_order.materials[0].english_name, "Mesh")

        session.current_order.supplier = "수정 공급처"
        self.assertEqual(session.extracted_order.supplier, "원본 공급처")

    def test_saves_missing_names_and_updates_editable_order(self) -> None:
        session = self.service.load(Path("sample.pdf"))
        translations = {
            MissingTranslation("erp_item", "완제품"): "Finished Product",
            MissingTranslation("material", "원단"): "Fabric",
        }

        self.service.save_missing_translations(session, translations)

        self.assertEqual(session.missing_translations, [])
        self.assertEqual(
            session.current_order.erp_item_english_name, "Finished Product"
        )
        self.assertEqual(session.current_order.materials[1].english_name, "Fabric")


if __name__ == "__main__":
    unittest.main()
