"""Turn confluence facts into short human-readable explanations."""
from __future__ import annotations

from typing import List

from ..analysis.confluence import ConfluenceResult


def summary(result: ConfluenceResult) -> str:
    if result.signal == "BUY":
        head = f"BUY setup, confidence {result.score}/100."
    elif result.signal == "SELL":
        head = f"SELL setup, confidence {result.score}/100."
    else:
        head = f"WAIT — confidence {result.score}/100 does not justify a trade yet."
    lines: List[str] = [head]
    if result.positive_evidence:
        lines.append("For: " + "; ".join(result.positive_evidence[:5]))
    if result.negative_evidence:
        lines.append("Against: " + "; ".join(result.negative_evidence[:5]))
    if result.warnings:
        lines.append("Warnings: " + "; ".join(result.warnings[:5]))
    return " ".join(lines)
