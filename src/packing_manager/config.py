"""Shared application paths and constants."""

import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
DATABASE_PATH = DATA_DIR / "packing_manager.db"
