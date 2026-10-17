"""Puts the project root on sys.path so tests/ can import utils."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
