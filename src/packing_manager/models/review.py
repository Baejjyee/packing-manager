"""State used while a user reviews an extracted order."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .order import PurchaseOrder


TranslationKind = Literal["erp_item", "material"]


@dataclass(frozen=True, slots=True)
class MissingTranslation:
    """A Korean name for which the UI needs to request an English name."""

    kind: TranslationKind
    korean_name: str


@dataclass(slots=True)
class OrderReviewSession:
    """Keep extracted data separate from the user's editable copy."""

    source_path: Path
    extracted_order: PurchaseOrder
    current_order: PurchaseOrder
    missing_translations: list[MissingTranslation] = field(default_factory=list)
