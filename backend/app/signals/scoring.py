"""Scoring config exposed so the UI can render the same weights."""
from __future__ import annotations

from ..analysis.confluence import GROUP_WEIGHTS


def default_weights() -> dict[str, int]:
    return dict(GROUP_WEIGHTS)


def bands() -> dict[str, tuple[int, int]]:
    """Confidence bands used in the UI."""
    return {
        "strong": (85, 100),
        "valid": (65, 84),
        "watch": (45, 64),
        "no_trade": (0, 44),
    }
