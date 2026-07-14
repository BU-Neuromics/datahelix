"""Smoke tests for the datahelix umbrella CLI.

Environment-tolerant by design: this repo does not necessarily have any
platform component (mosaic, canon, cappella, aperture, bridge) installed
alongside the metapackage, so these tests assert output *structure* and
internally-consistent behavior rather than any specific installed/not-
installed state.
"""

import subprocess
import sys
from pathlib import Path

from datahelix import cli


def test_build_parser_has_info_and_doctor_subcommands():
    parser = cli.build_parser()

    info_args = parser.parse_args(["info"])
    assert info_args.command == "info"

    doctor_args = parser.parse_args(["doctor"])
    assert doctor_args.command == "doctor"


def test_info_runs_and_mentions_mosaic(capsys):
    exit_code = cli.main(["info"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Mosaic" in captured.out
    assert "datahelix-mosaic" in captured.out

    # Table structure: header row + separator row + one row per component,
    # regardless of which components happen to be installed here.
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 2 + len(cli.COMPONENTS)


def test_info_reports_consistent_installed_state():
    for _display_name, dist_name, _import_name in cli.COMPONENTS:
        installed, ver = cli._installed_version(dist_name)
        if installed:
            assert isinstance(ver, str) and ver
        else:
            assert ver is None


def test_doctor_runs_and_reports_expected_sections(capsys):
    exit_code = cli.main(["doctor"])
    captured = capsys.readouterr()

    # doctor never crashes; it may exit 0 (all installed components import
    # cleanly, or none are installed) or 1 (an installed component fails to
    # import).
    assert exit_code in (0, 1)
    assert "Component health:" in captured.out
    assert "Entry-point groups (mosaic.*):" in captured.out
    for display_name, _dist_name, _import_name in cli.COMPONENTS:
        assert display_name in captured.out


def test_doctor_exit_code_matches_actual_import_failures(capsys):
    """The nonzero-exit contract: doctor must fail iff an *installed*
    component's import name fails to import. Holds whether zero, some, or
    all components are installed."""
    exit_code = cli.main(["doctor"])

    any_import_failure = False
    for _display_name, dist_name, import_name in cli.COMPONENTS:
        installed, _ver = cli._installed_version(dist_name)
        if not installed:
            continue
        try:
            __import__(import_name)
        except ImportError:
            any_import_failure = True

    assert exit_code == (1 if any_import_failure else 0)


def test_doctor_skips_uninstalled_components(capsys):
    cli.main(["doctor"])
    captured = capsys.readouterr()

    for _display_name, dist_name, _import_name in cli.COMPONENTS:
        installed, _ver = cli._installed_version(dist_name)
        if not installed:
            assert "not installed (skipped)" in captured.out


def test_cli_console_script_entrypoint_via_subprocess():
    src_dir = Path(__file__).resolve().parent.parent / "src"

    result = subprocess.run(
        [sys.executable, "-m", "datahelix.cli", "info"],
        cwd=str(src_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "mosaic" in result.stdout.lower()


def test_cli_requires_a_subcommand():
    parser = cli.build_parser()
    try:
        parser.parse_args([])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("expected argparse to require a subcommand")
