"""Tests for the CSV import validation flow."""
from __future__ import annotations

import io
from datetime import datetime, timezone

import pytest

from app.api.upload import _parse_ts


def test_parse_ts_iso():
    dt = _parse_ts("2026-09-14T09:15:00+00:00")
    assert dt.year == 2026 and dt.month == 9 and dt.day == 14
    assert dt.tzinfo is not None


def test_parse_ts_epoch_seconds():
    dt = _parse_ts("1789379100")
    assert dt.tzinfo is not None


def test_parse_ts_epoch_millis():
    dt = _parse_ts("1789379100000")
    assert dt.year == 2026


def test_parse_ts_rejects_empty():
    with pytest.raises(ValueError):
        _parse_ts("")


def test_parse_ts_space_separator():
    dt = _parse_ts("2026-09-14 09:15:00")
    assert dt.hour == 9 and dt.minute == 15


def test_parse_ts_rejects_garbage():
    with pytest.raises(ValueError):
        _parse_ts("not-a-timestamp")
