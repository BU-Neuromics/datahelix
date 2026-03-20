"""Tests for the Canon exception hierarchy."""

from __future__ import annotations

from canon.exceptions import (
    CanonCycleError,
    CanonError,
    CanonExecutorError,
    CanonIngestionError,
    CanonPlanningError,
    CanonValidationError,
)


def test_all_exception_types_importable():
    assert CanonError
    assert CanonPlanningError
    assert CanonCycleError
    assert CanonValidationError
    assert CanonExecutorError
    assert CanonIngestionError


def test_all_inherit_from_canon_error():
    assert issubclass(CanonPlanningError, CanonError)
    assert issubclass(CanonCycleError, CanonError)
    assert issubclass(CanonValidationError, CanonError)
    assert issubclass(CanonExecutorError, CanonError)
    assert issubclass(CanonIngestionError, CanonError)


def test_cycle_error_has_cycle_path():
    err = CanonCycleError("cycle detected!", cycle_path=["A", "B", "A"])
    assert err.cycle_path == ["A", "B", "A"]


def test_cycle_error_default_cycle_path():
    err = CanonCycleError("cycle detected!")
    assert err.cycle_path == []


def test_cycle_error_message():
    err = CanonCycleError("cycle detected!", cycle_path=["X", "Y"])
    assert str(err) == "cycle detected!"
