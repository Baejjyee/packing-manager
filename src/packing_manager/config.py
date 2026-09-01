"""Shared application paths and constants."""

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
FONT_DIR = RESOURCE_ROOT / "assets" / "fonts"
DATABASE_PATH = DATA_DIR / "packing_manager.db"
