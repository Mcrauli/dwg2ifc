"""Plan D Task 13: end-to-end GUI roundtrip with the real convert_dxf."""

import os
from pathlib import Path

import ifcopenshell

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
