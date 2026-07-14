"""Umbrella CLI for the DataHelix platform metapackage.

Introspection only: reports which platform components are installed, their
versions, and runs lightweight import / entry-point health checks. No
business logic lives here (platform ADR-0002). Stdlib only (argparse +
importlib.metadata) so the metapackage itself carries zero dependencies.
"""

import argparse
import importlib
import sys
from importlib.metadata import PackageNotFoundError, entry_points, version

# (display name, distribution name, import name)
COMPONENTS = [
    ("Mosaic", "datahelix-mosaic", "mosaic"),
    ("Canon", "datahelix-canon", "canon"),
    ("Cappella", "datahelix-cappella", "cappella"),
    ("Aperture", "datahelix-aperture", "aperture"),
    ("Bridge", "datahelix-bridge", "bridge"),
]

ENTRY_POINT_GROUP_PREFIX = "mosaic."


def _installed_version(dist_name):
    """Return (installed, version_string) for a distribution name."""
    try:
        return True, version(dist_name)
    except PackageNotFoundError:
        return False, None


def cmd_info(args):
    """Print a table of the platform components: installed?, version."""
    rows = []
    for display_name, dist_name, _import_name in COMPONENTS:
        installed, ver = _installed_version(dist_name)
        rows.append((display_name, dist_name, "yes" if installed else "no", ver or "-"))

    headers = ("Component", "Distribution", "Installed", "Version")
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))
    ]

    def _fmt(row):
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(_fmt(headers))
    print(_fmt(tuple("-" * w for w in widths)))
    for row in rows:
        print(_fmt(row))

    return 0


def _entry_point_groups():
    """Return the set of entry-point group names visible in this environment."""
    eps = entry_points()
    if hasattr(eps, "groups"):
        return set(eps.groups)
    return {ep.group for ep in eps}


def cmd_doctor(args):
    """Import-check installed components and report mosaic.* entry points.

    Exits nonzero if an installed component fails to import.
    """
    exit_code = 0

    print("Component health:")
    for display_name, dist_name, import_name in COMPONENTS:
        installed, ver = _installed_version(dist_name)
        if not installed:
            print(f"  {display_name}: not installed (skipped)")
            continue

        try:
            importlib.import_module(import_name)
        except ImportError as exc:
            print(f"  {display_name}: FAILED to import '{import_name}' ({exc})")
            exit_code = 1
        else:
            print(f"  {display_name}: ok (v{ver}, import '{import_name}' succeeds)")

    print()
    print("Entry-point groups (mosaic.*):")
    groups = sorted(g for g in _entry_point_groups() if g.startswith(ENTRY_POINT_GROUP_PREFIX))
    if not groups:
        print("  (none found)")
    else:
        for group in groups:
            count = len(entry_points(group=group))
            print(f"  {group}: {count} entry point(s)")

    return exit_code


def build_parser():
    parser = argparse.ArgumentParser(
        prog="datahelix",
        description="DataHelix platform metapackage - umbrella CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    info_parser = subparsers.add_parser(
        "info", help="List installed platform components and versions"
    )
    info_parser.set_defaults(func=cmd_info)

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check installed components import cleanly and report entry points",
    )
    doctor_parser.set_defaults(func=cmd_doctor)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
