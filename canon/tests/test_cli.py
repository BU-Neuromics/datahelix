"""Tests for Canon CLI commands via typer.testing.CliRunner."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from canon.cli.main import app

runner = CliRunner()


def test_canon_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "canon" in result.output.lower()


def test_rules_help_exits_zero():
    result = runner.invoke(app, ["rules", "--help"])
    assert result.exit_code == 0


def test_get_help_exits_zero():
    result = runner.invoke(app, ["get", "--help"])
    assert result.exit_code == 0


def test_plan_help_exits_zero():
    result = runner.invoke(app, ["plan", "--help"])
    assert result.exit_code == 0


def test_status_help_exits_zero():
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0
