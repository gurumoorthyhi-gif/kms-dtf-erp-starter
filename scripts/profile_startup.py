"""Repeatable import profiling for measured startup work."""

import sys
from pathlib import Path
from time import perf_counter

started = perf_counter()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app.main  # noqa: E402,F401

print(f"app.main import: {(perf_counter() - started) * 1000:.1f} ms")
