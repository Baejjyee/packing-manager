"""English-name lookup and registration workflow."""

from __future__ import annotations

from packing_manager.database import TranslationRepository
from packing_manager.models import MissingTranslation, PurchaseOrder


class TranslationService:
    """Apply stored translations and report names that still need input."""

    def __init__(self, repository: TranslationRepository) -> None:
        self.repository = repository

    def apply_known_translations(
        self, order: PurchaseOrder
    ) -> list[MissingTranslation]:
        """Apply saved names to an order and return unique missing entries."""
        missing: list[MissingTranslation] = []
        seen: set[MissingTranslation] = set()

        if not order.erp_item_english_name and order.erp_item_name.strip():
            english_name = self.repository.get_erp_item_english_name(
                order.erp_item_name
            )
            if english_name:
                order.erp_item_english_name = english_name
            else:
                _append_missing(
                    missing,
                    seen,
                    MissingTranslation("erp_item", order.erp_item_name.strip()),
                )

        for material in order.materials:
            if material.english_name or not material.material_name.strip():
                continue
            english_name = self.repository.get_material_english_name(
                material.material_name
            )
            if english_name:
                material.english_name = english_name
            else:
                _append_missing(
                    missing,
                    seen,
                    MissingTranslation("material", material.material_name.strip()),
                )

        return missing

    def save_translation(
        self, missing: MissingTranslation, english_name: str
    ) -> None:
        """Save a translation supplied by the user."""
        if missing.kind == "erp_item":
            self.repository.save_erp_item_translation(
                missing.korean_name, english_name
            )
            return
        self.repository.save_material_translation(missing.korean_name, english_name)


def _append_missing(
    result: list[MissingTranslation],
    seen: set[MissingTranslation],
    item: MissingTranslation,
) -> None:
    if item not in seen:
        seen.add(item)
        result.append(item)
