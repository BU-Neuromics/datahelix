"""``bass-ledger`` — command-line front end to the certified-frontier ledger.

Subcommands:
    certify   append a certification result as a ``certified/*`` tag
    assemble  build ``compatibility.json`` from the ledger tags
    query     list partner versions certified with a line
    gate      exit non-zero unless a requested pair is certified for deploy

Component pins are given as ``name=version@digest`` (repeatable), e.g.
    bass-ledger certify \
        --component aperture=1.4.2@sha256:ab...  \
        --component hippo=1.2.4@sha256:cd...     \
        --suite-sha $GITHUB_SHA --fixture-version 1.0.0 \
        --result pass --line frontier --timestamp 2026-07-07T00:00:00Z
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

from .assemble import assemble, write_compatibility_json
from .certify import write_entry
from .gate import GateError, check_pair
from .model import Component, LedgerEntry
from .query import partners_for_line


def _parse_component(spec: str) -> Component:
    # name=version@digest
    try:
        name, rest = spec.split("=", 1)
        version, digest = rest.split("@", 1)
    except ValueError:
        raise SystemExit(
            f"bad --component {spec!r}; expected name=version@digest"
        )
    return Component(name=name.strip(), version=version.strip(), digest=digest.strip())


def _now_iso() -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _cmd_certify(args: argparse.Namespace) -> int:
    entry = LedgerEntry(
        components=[_parse_component(s) for s in args.component],
        suite_sha=args.suite_sha,
        fixture_version=args.fixture_version,
        result=args.result,
        line=args.line,
        failing_check=args.failing_check,
        timestamp=args.timestamp or _now_iso(),
        ci_run=args.ci_run,
    )
    tag = write_entry(entry, repo=args.repo, ref=args.ref, push=args.push)
    print(f"wrote ledger entry {tag} (result={entry.result})")
    return 0


def _cmd_assemble(args: argparse.Namespace) -> int:
    if args.out:
        doc = write_compatibility_json(args.out, repo=args.repo)
        print(f"wrote {args.out}: {doc['counts']}")
    else:
        import json

        print(json.dumps(assemble(repo=args.repo), indent=2, sort_keys=True))
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    versions = partners_for_line(
        args.anchor,
        args.line,
        args.partner,
        passing_only=not args.include_failing,
        repo=args.repo,
    )
    if not versions:
        print(
            f"no {args.partner} versions certified with {args.anchor} {args.line}",
            file=sys.stderr,
        )
        return 1
    print("\n".join(versions))
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    requested = [_parse_component(s) for s in args.component]
    try:
        entry = check_pair(requested, repo=args.repo)
    except GateError as exc:
        print(f"DEPLOY BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"DEPLOY OK: pair {entry.label} certified passing at {entry.timestamp}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bass-ledger", description=__doc__)
    p.add_argument("--repo", default=".", help="path to the drylims git repo")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("certify", help="append a certification result")
    c.add_argument("--component", action="append", required=True,
                   help="name=version@digest (repeatable)")
    c.add_argument("--suite-sha", required=True)
    c.add_argument("--fixture-version", required=True)
    c.add_argument("--result", choices=LedgerEntry.RESULTS, required=True)
    c.add_argument("--line", default="frontier")
    c.add_argument("--failing-check", default=None)
    c.add_argument("--timestamp", default=None, help="ISO-8601 UTC; defaults to now")
    c.add_argument("--ci-run", default=None)
    c.add_argument("--ref", default="HEAD", help="git ref to tag")
    c.add_argument("--push", action="store_true", help="push the tag to origin")
    c.set_defaults(func=_cmd_certify)

    a = sub.add_parser("assemble", help="build compatibility.json from tags")
    a.add_argument("--out", default=None, help="write to this path (else stdout)")
    a.set_defaults(func=_cmd_assemble)

    q = sub.add_parser("query", help="partner versions certified with a line")
    q.add_argument("--anchor", required=True, help="component whose line we fix")
    q.add_argument("--line", required=True, help="version glob, e.g. 1.4.* or 1.4")
    q.add_argument("--partner", required=True, help="component to list versions of")
    q.add_argument("--include-failing", action="store_true")
    q.set_defaults(func=_cmd_query)

    g = sub.add_parser("gate", help="verify a pair is certified for deploy")
    g.add_argument("--component", action="append", required=True,
                   help="name=version@digest (repeatable)")
    g.set_defaults(func=_cmd_gate)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
