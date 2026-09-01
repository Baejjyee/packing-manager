from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from packing_manager.database import TranslationRepository


class TranslationRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "translations.db"
        self.repository = TranslationRepository(database_path)
        self.repository.initialize()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_initialize_is_idempotent(self) -> None:
        self.repository.initialize()

    def test_saves_reads_and_updates_erp_item_translation(self) -> None:
        self.assertIsNone(
            self.repository.get_erp_item_english_name("테스트 완제품")
        )

        self.repository.save_erp_item_translation("테스트 완제품", "Test Product")
        self.assertEqual(
            self.repository.get_erp_item_english_name("테스트 완제품"),
            "Test Product",
        )

        self.repository.save_erp_item_translation("테스트 완제품", "Updated Product")
        self.assertEqual(
            self.repository.get_erp_item_english_name("테스트 완제품"),
            "Updated Product",
        )

    def test_saves_and_reads_material_translation(self) -> None:
        self.repository.save_material_translation("메쉬", "Mesh")

        self.assertEqual(
            self.repository.get_material_english_name("메쉬"), "Mesh"
        )

    def test_rejects_empty_names(self) -> None:
        with self.assertRaises(ValueError):
            self.repository.save_material_translation("메쉬", "  ")


if __name__ == "__main__":
    unittest.main()
