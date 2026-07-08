"""Ledger data model — the certified triple and its serialization.

A ledger entry is, per ADR-0001, effectively the triple

    (aperture X @ digest, hippo Y @ digest, suite S @ sha)

plus pass/fail, the failing-check name (on fail), the line it certifies, and a
timestamp. We model the component set as an ordered map so the scheme
generalizes to a third component (Cappella, Bridge) without a format change,
while keeping the aperture+hippo convenience the current frontier needs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any

# Tag namespace for ledger records. Repo-global, branch-independent, visibly
# append-only (git tags survive branch deletion). Example:
#   certified/aperture-1.4.2+hippo-1.2.4 (pre-rename) or
#   certified/aperture-1.4.2+mosaic-1.2.4 (post-rename) — see COMPONENT_ALIASES.
TAG_PREFIX = "certified/"

# Component-name aliases (platform ADR-0004 / plan decision 1.7): Hippo was
# renamed to Mosaic, but the certification ledger is append-only — existing
# `hippo=` entries and `certified/...+hippo-Y` tags are never rewritten. New
# entries use the canonical `mosaic` key. Both spellings name the SAME
# component line, so queries and the deploy gate must resolve either spelling
# to the same set of ledger entries. This also covers the transition window
# where the hippo repo's own release pipeline still publishes images tagged
# `"component": "hippo"` (until the repo itself is renamed, Phase R).
COMPONENT_ALIASES: dict[str, frozenset[str]] = {
    "hippo": frozenset({"hippo", "mosaic"}),
    "mosaic": frozenset({"hippo", "mosaic"}),
}


def component_line_names(name: str) -> frozenset[str]:
    """All spellings that denote the same component line as ``name``.

    For most component names this is just ``{name}``; for ``hippo``/``mosaic``
    it is both spellings, so a lookup for either name matches ledger entries
    recorded under the other (see ``COMPONENT_ALIASES``).
    """
    return COMPONENT_ALIASES.get(name, frozenset({name}))

# A digest is the artifact's content address (e.g. an OCI image digest or a
# package hash). Semver is a *claim*; the digest is the *evidence* (ADR-0001).
_DIGEST_RE = re.compile(r"^[a-z0-9]+:[0-9a-f]{32,}$|^sha256-[0-9a-f]{32,}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-+.][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True, order=True)
class Component:
    """One component pinned in a certification: name + exact version + digest.

    ``digest`` is what was *actually* booted. A rebuilt release under the same
    version number will mismatch its certified digest and be refused by the
    deploy gate — this is how ADR-0001's immutability rule is enforced.
    """

    name: str
    version: str
    digest: str

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.name or not self.name.replace("-", "").isalnum():
            problems.append(f"component name {self.name!r} is not a bare slug")
        if not _VERSION_RE.match(self.version):
            problems.append(f"{self.name}: version {self.version!r} is not semver")
        if not _DIGEST_RE.match(self.digest):
            problems.append(
                f"{self.name}: digest {self.digest!r} is not a content address "
                "(expected e.g. 'sha256:<hex>'); a certified pair must pin the "
                "artifact digest, not just the version (ADR-0001)"
            )
        return problems

    @property
    def label(self) -> str:
        return f"{self.name}-{self.version}"


@dataclass
class LedgerEntry:
    """One append-only certification fact.

    ``result`` is ``"pass"`` or ``"fail"``. Failures are recorded too: an
    incompatible pair is paid-for information (prevents retries; lets ranges be
    inferred later). ``line`` names the release line certified — ``"frontier"``
    for latest, or a maintenance line id like ``"lts-1"``.
    """

    components: list[Component]
    suite_sha: str          # the certification suite (DataHelix commit) that ran
    fixture_version: str    # bootstrap fixture package version used to seed
    result: str             # "pass" | "fail"
    line: str = "frontier"
    failing_check: str | None = None   # set only on fail
    timestamp: str = ""     # ISO-8601 UTC; caller-supplied for determinism
    ci_run: str | None = None          # CI run URL/id for traceability

    RESULTS = ("pass", "fail")

    # ---- identity -------------------------------------------------------

    @property
    def label(self) -> str:
        """Stable pair label used as the tag name suffix.

        Components are sorted by name so the label is deterministic regardless
        of input order: ``aperture-1.4.2+hippo-1.2.4``.
        """
        return "+".join(c.label for c in sorted(self.components, key=lambda c: c.name))

    @property
    def tag(self) -> str:
        return TAG_PREFIX + self.label

    def component(self, name: str) -> Component | None:
        for c in self.components:
            if c.name == name:
                return c
        return None

    def component_line(self, name: str) -> Component | None:
        """Like :meth:`component`, but resolving the ``hippo``/``mosaic`` alias.

        Use this for queries/gating so a lookup for ``mosaic`` also matches an
        entry recorded under the legacy ``hippo`` name (and vice versa) —
        decision 1.7: the two spellings are one component line.
        """
        wanted = component_line_names(name)
        for c in self.components:
            if c.name in wanted:
                return c
        return None

    @property
    def passed(self) -> bool:
        return self.result == "pass"

    # ---- validation -----------------------------------------------------

    def validate(self) -> list[str]:
        problems: list[str] = []
        if len(self.components) < 2:
            problems.append("a certification pins at least two components")
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            problems.append(f"duplicate component names: {names}")
        for c in self.components:
            problems.extend(c.validate())
        if self.result not in self.RESULTS:
            problems.append(f"result {self.result!r} not in {self.RESULTS}")
        if self.result == "fail" and not self.failing_check:
            problems.append("a failing entry must name the failing_check")
        if self.result == "pass" and self.failing_check:
            problems.append("a passing entry must not carry a failing_check")
        if not self.suite_sha:
            problems.append("suite_sha is required (the suite is part of the triple)")
        if not self.fixture_version:
            problems.append("fixture_version is required")
        if not self.timestamp:
            problems.append("timestamp is required")
        return problems

    def raise_if_invalid(self) -> "LedgerEntry":
        problems = self.validate()
        if problems:
            raise ValueError(
                "invalid ledger entry:\n  - " + "\n  - ".join(problems)
            )
        return self

    # ---- serialization --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Sort components for a stable, diff-friendly document.
        d["components"] = [
            asdict(c) for c in sorted(self.components, key=lambda c: c.name)
        ]
        d["label"] = self.label
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LedgerEntry":
        comps = [
            Component(name=c["name"], version=c["version"], digest=c["digest"])
            for c in d["components"]
        ]
        return cls(
            components=comps,
            suite_sha=d["suite_sha"],
            fixture_version=d["fixture_version"],
            result=d["result"],
            line=d.get("line", "frontier"),
            failing_check=d.get("failing_check"),
            timestamp=d.get("timestamp", ""),
            ci_run=d.get("ci_run"),
        )

    @classmethod
    def from_json(cls, text: str) -> "LedgerEntry":
        return cls.from_dict(json.loads(text))
