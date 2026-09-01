"""Use cases for loading and preparing an order for user review."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Mapping

from packing_manager.models import OrderReviewSession

from .packing_service import PackingService
from .translation_service import MissingTranslation, TranslationService


class OrderReviewService:
    """Prepare independent extracted and editable order models for the UI."""

    def __init__(
        self,
        packing_service: PackingService,
        translation_service: TranslationService,
    ) -> None:
        self.packing_service = packing_service
        self.translation_service = translation_service

    def load(self, pdf_path: Path) -> OrderReviewSession:
        """Parse, merge, translate, and create a review session."""
        extracted_order = self.packing_service.load_purchase_order(pdf_path)
        current_order = deepcopy(extracted_order)
        missing = self.translation_service.apply_known_translations(current_order)
        return OrderReviewSession(
            source_path=Path(pdf_path),
            extracted_order=extracted_order,
            current_order=current_order,
            missing_translations=list(missing),
        )

    def save_missing_translations(
        self,
        session: OrderReviewSession,
        translations: Mapping[MissingTranslation, str],
    ) -> None:
        """Save user-entered names and reapply translations to the session."""
        expected = set(session.missing_translations)
        unexpected = set(translations).difference(expected)
        if unexpected:
            raise ValueError("A translation does not belong to this review session.")

        for item, english_name in translations.items():
            self.translation_service.save_translation(item, english_name)

        session.missing_translations = list(
            self.translation_service.apply_known_translations(session.current_order)
        )
