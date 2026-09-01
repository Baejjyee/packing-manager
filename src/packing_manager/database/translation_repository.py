"""SQLite repository for English-name translations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from packing_manager.config import DATABASE_PATH


_ERP_ITEM_TABLE = "erp_item_translations"
_MATERIAL_TABLE = "material_translations"


class TranslationRepository:
    """Store and retrieve ERP item and material English names."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Create translation tables when they do not already exist."""
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_ERP_ITEM_TABLE} (
                    korean_name TEXT PRIMARY KEY NOT NULL CHECK (length(trim(korean_name)) > 0),
                    english_name TEXT NOT NULL CHECK (length(trim(english_name)) > 0),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_MATERIAL_TABLE} (
                    korean_name TEXT PRIMARY KEY NOT NULL CHECK (length(trim(korean_name)) > 0),
                    english_name TEXT NOT NULL CHECK (length(trim(english_name)) > 0),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_erp_item_english_name(self, korean_name: str) -> str | None:
        """Return the saved English ERP item name, if any."""
        return self._get_translation(_ERP_ITEM_TABLE, korean_name)

    def save_erp_item_translation(self, korean_name: str, english_name: str) -> None:
        """Insert or update an ERP item translation."""
        self._save_translation(_ERP_ITEM_TABLE, korean_name, english_name)

    def get_material_english_name(self, korean_name: str) -> str | None:
        """Return the saved English material name, if any."""
        return self._get_translation(_MATERIAL_TABLE, korean_name)

    def save_material_translation(self, korean_name: str, english_name: str) -> None:
        """Insert or update a material translation."""
        self._save_translation(_MATERIAL_TABLE, korean_name, english_name)

    def _get_translation(self, table: str, korean_name: str) -> str | None:
        normalized_name = _required_text(korean_name, "Korean name")
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT english_name FROM {table} WHERE korean_name = ?",
                (normalized_name,),
            ).fetchone()
        return str(row[0]) if row else None

    def _save_translation(
        self, table: str, korean_name: str, english_name: str
    ) -> None:
        normalized_korean = _required_text(korean_name, "Korean name")
        normalized_english = _required_text(english_name, "English name")
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO {table} (korean_name, english_name)
                VALUES (?, ?)
                ON CONFLICT(korean_name) DO UPDATE SET
                    english_name = excluded.english_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (normalized_korean, normalized_english),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized
