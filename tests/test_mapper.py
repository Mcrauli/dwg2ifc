"""Unit tests for core.mapper."""
import pytest

from dxf2ifc.core.mapper import layer_matches


@pytest.mark.parametrize(
    "pattern,layer,expected",
    [
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA", True),
        ("KYL-ULKOSEINA*", "KYL-ULKOSEINA-200", True),
        ("KYL-ULKOSEINA*", "KYL-VALISEINA", False),
        ("KYL-*", "KYL-LEVYHYLLY", True),
        ("KYL-*", "WALL", False),
        ("LT IMU", "LT IMU", True),
        ("LT IMU", "lt imu", True),  # case-insensitive
    ],
)
def test_layer_matches(pattern: str, layer: str, expected: bool):
    assert layer_matches(pattern, layer) is expected
