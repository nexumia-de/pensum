"""Typing and showing durations."""
import pytest

from pensum import duration


@pytest.mark.parametrize("text, ms", [
    ("", 0), ("45m", 2_700_000), ("1h 30m", 5_400_000), ("1.5h", 5_400_000),
    ("1,5 h", 5_400_000), ("90", 5_400_000), ("2h", 7_200_000), ("1h30m", 5_400_000),
])
def test_parse(text, ms):
    assert duration.parse(text) == ms


@pytest.mark.parametrize("text", ["soon", "1x", "h"])
def test_parse_rejects(text):
    assert duration.parse(text) is None


def test_format():
    assert duration.format_short(5_400_000) == "1h 30m"
    assert duration.format_short(3_600_000) == "1h"
    assert duration.format_short(59_000) == "0m"
    assert duration.format_clock(3_909_000) == "1:05:09"
    assert duration.format_clock(309_000) == "5:09"
