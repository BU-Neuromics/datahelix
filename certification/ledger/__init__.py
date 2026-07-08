"""DataHelix certified-frontier ledger tooling.

The ledger is the append-only record of composition certifications described in
platform ADR-0001. Every certification of an exact version pair (with artifact
digests) becomes one annotated git tag ``certified/<label>`` whose message is a
small JSON document. Deploy tooling refuses any pair not present as a *passing*
ledger entry.

This package is pure stdlib + git-over-subprocess so it runs anywhere CI does.

Public surface:
    LedgerEntry          the certified triple + result (see ``model``)
    COMPONENT_ALIASES    hippo/mosaic same-component-line alias map (``model``)
    write_entry          create the annotated ``certified/*`` tag (see ``certify``)
    read_entries         read all ledger entries from tags (see ``assemble``)
    assemble             build ``compatibility.json`` from tags (see ``assemble``)
    partners_for_line    query certified partners of a line (see ``query``)
    is_certified         deploy-gate predicate (see ``gate``)
"""

from .model import (
    LedgerEntry,
    Component,
    TAG_PREFIX,
    COMPONENT_ALIASES,
    component_line_names,
)
from .certify import write_entry
from .assemble import read_entries, assemble
from .query import partners_for_line, find_entry
from .gate import is_certified, GateError, check_pair

__all__ = [
    "LedgerEntry",
    "Component",
    "TAG_PREFIX",
    "COMPONENT_ALIASES",
    "component_line_names",
    "write_entry",
    "read_entries",
    "assemble",
    "partners_for_line",
    "find_entry",
    "is_certified",
    "check_pair",
    "GateError",
]
