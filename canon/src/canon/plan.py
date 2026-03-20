"""Execution plan types for Canon."""

from __future__ import annotations

import dataclasses
import json
from enum import Enum

from canon.rules import OutputSpec
from canon.types import WildcardBinding


class NodeDecision(str, Enum):
    REUSE = 'REUSE'
    BUILD = 'BUILD'


@dataclasses.dataclass
class EntityRef:
    """Reference to an existing entity that can be reused."""

    entity_id: str
    entity_type: str
    metadata: dict
    decision: NodeDecision = NodeDecision.REUSE


@dataclasses.dataclass
class CanonTask:
    """A unit of work that builds a new entity via a production rule."""

    rule_name: str
    wildcard_bindings: WildcardBinding
    input_entities: dict[str, dict]
    output_spec: list[OutputSpec]
    decision: NodeDecision = NodeDecision.BUILD


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _default(obj: object) -> object:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, WildcardBinding):
        return obj.as_dict()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _node_to_dict(node: EntityRef | CanonTask) -> dict:
    d = dataclasses.asdict(node)
    # Flatten enum values
    if 'decision' in d:
        d['decision'] = node.decision.value
    d['__type__'] = type(node).__name__
    # WildcardBinding becomes a plain dict via asdict already (it's not a dataclass)
    # But dataclasses.asdict won't recurse into WildcardBinding — handle manually
    if isinstance(node, CanonTask):
        d['wildcard_bindings'] = node.wildcard_bindings.as_dict()
        d['output_spec'] = [o.model_dump() for o in node.output_spec]
    return d


def _node_from_dict(d: dict) -> EntityRef | CanonTask:
    typ = d.pop('__type__')
    decision = NodeDecision(d['decision'])
    if typ == 'EntityRef':
        return EntityRef(
            entity_id=d['entity_id'],
            entity_type=d['entity_type'],
            metadata=d['metadata'],
            decision=decision,
        )
    # CanonTask
    output_spec = [OutputSpec(**o) for o in d['output_spec']]
    return CanonTask(
        rule_name=d['rule_name'],
        wildcard_bindings=WildcardBinding(d['wildcard_bindings']),
        input_entities=d['input_entities'],
        output_spec=output_spec,
        decision=decision,
    )


@dataclasses.dataclass
class ExecutionPlan:
    """Ordered list of nodes (dependencies before dependents)."""

    nodes: list[EntityRef | CanonTask]

    @property
    def build_nodes(self) -> list[CanonTask]:
        return [n for n in self.nodes if isinstance(n, CanonTask)]

    @property
    def reuse_nodes(self) -> list[EntityRef]:
        return [n for n in self.nodes if isinstance(n, EntityRef)]

    def to_json(self) -> str:
        """Serialize the plan to a JSON string."""
        return json.dumps([_node_to_dict(n) for n in self.nodes], default=_default)

    @classmethod
    def from_json(cls, s: str) -> 'ExecutionPlan':
        """Deserialize a plan from a JSON string."""
        raw = json.loads(s)
        return cls(nodes=[_node_from_dict(d) for d in raw])
