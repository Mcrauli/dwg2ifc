"""Affine-matrix helper shared by every element builder."""

from __future__ import annotations

import math


def _z_rotation_matrix(x: float, y: float, z: float, angle: float) -> list[list[float]]:
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0.0, x],
        [s, c, 0.0, y],
        [0.0, 0.0, 1.0, z],
        [0.0, 0.0, 0.0, 1.0],
    ]
