## 4. Resolution Algorithm

**Document status:** Draft v0.1  
**Depends on:** sec2_architecture.md, sec3_rules_dsl.md

---

### 4.1 Overview

The resolution algorithm is Canon's core. It answers one question recursively:

> *Does an artifact matching this specification exist in Hippo? If yes, return its URI.
> If no, find a rule that can produce it, resolve its inputs the same way, execute, and
> return the resulting URI.*

The algorithm has four phases, executed in order for every `canon get` call:

1. **Entity reference resolution** — resolve all `ref:T{...}` expressions to Hippo UUIDs
2. **Registry lookup** — query Hippo for an existing entity matching the resolved spec
3. **Rule matching** — find a production rule if no entity was found
4. **Recursive input resolution + execution** — resolve required inputs, execute CWL, ingest output

Phases 1–2 are always executed. Phases 3–4 only run on a cache miss (BUILD path).

---

### 4.2 Phase 1: Entity Reference Resolution

Before any Hippo query, all `ref:EntityType{...}` expressions in the request parameters
are resolved to concrete Hippo UUIDs.

**Algorithm:**

```python
def resolve_entity_ref(ref_expr: str) -> str:
    """Resolve ref:T{field=val, ...} to a Hippo entity UUID."""

    entity_type, field_constraints = parse_ref_expr(ref_expr)
    # e.g. "ref:ToolVersion{tool.name=STAR, version=2.7.11a}"
    # → entity_type="ToolVersion", constraints={"tool.name": "STAR", "version": "2.7.11a"}

    # Resolve dot-notation field paths
    resolved_constraints = {}
    for path, value in field_constraints.items():
        if "." in path:
            resolved_constraints[path] = resolve_dot_path(path, value)
            # "tool.name=STAR" → follow 'tool' ref field, match 'name' field
        else:
            resolved_constraints[path] = value

    # Query Hippo
    results = hippo.find_entities(entity_type, resolved_constraints)

    if len(results) == 0:
        raise CanonResolutionError(
            f"No {entity_type} entity found matching {field_constraints}. "
            f"Ensure the entity exists in Hippo (run 'hippo reference install' "
            f"if this is a reference entity type)."
        )
    if len(results) > 1:
        raise CanonResolutionError(
            f"Ambiguous reference: {len(results)} {entity_type} entities match "
            f"{field_constraints}. Provide additional fields to disambiguate."
        )

    return results[0].id  # UUID
```

**Dot-notation traversal:**

`tool.name=STAR` means: find entities of the target type where the `tool` reference field
points to an entity whose `name` field equals `"STAR"`. This is implemented as a Hippo
JOIN query, not a client-side filter.

Maximum traversal depth: 3 levels. Deeper paths raise `CanonResolutionError`.

**Wildcard fields inside refs:**

If a ref expression contains wildcards (`ref:GenomeBuild{name={genome_build}}`), wildcards
are substituted from the request spec before resolution. If the wildcard is not yet bound,
`CanonPlanningError: unbound wildcard` is raised.

---

### 4.3 Phase 2: Registry Lookup

With all entity references resolved to UUIDs and all wildcards bound to concrete values,
Canon queries Hippo for an existing entity matching the full parameter set.

```python
def lookup(entity_type: str, resolved_params: dict) -> Entity | None:
    """Query Hippo for an existing entity. Returns None on cache miss."""

    return hippo.find_entity(
        entity_type=entity_type,
        filters={k: v for k, v in resolved_params.items()}
        # All filters are exact-match in v0.1
    )
```

**Exact match semantics (v0.1):** every field in `resolved_params` must match exactly.
Extra fields on the Hippo entity (not in the request spec) are ignored — Hippo entities
may carry additional metadata beyond what Canon's spec declares.

**Hit → REUSE:** if a matching entity is found, Canon returns its `uri` field immediately.
No rule lookup, no execution, no ingestion.

**Miss → BUILD:** proceed to Phase 3.

---

### 4.4 Phase 3: Rule Matching

On a cache miss, Canon searches the `RuleRegistry` for a rule whose `produces.match`
specification is compatible with the request.

```python
def find_rule(entity_type: str, resolved_params: dict) -> Rule | None:
    """Find a production rule matching the request spec."""

    candidates = rule_registry.rules_for_entity_type(entity_type)

    for rule in candidates:
        if rule_matches(rule, entity_type, resolved_params):
            return rule

    return None  # No rule found → CanonNoRuleError
```

**Rule matching logic:**

A rule matches a request if:
- `rule.produces.entity_type == request.entity_type`
- For every **fixed parameter** in `rule.produces.match` (non-wildcard):
  `rule.produces.match[param] == resolved_params[param]`
- For every **wildcard parameter** in `rule.produces.match`:
  `param` exists as a key in `resolved_params` (any value is acceptable —
  the wildcard binds to whatever the request provided)

**Fixed vs. wildcard parameters in rules:**

```yaml
produces:
  entity_type: AlignmentFile
  match:
    aligner: "ref:ToolVersion{tool.name=STAR, version=2.7.11a}"  # FIXED — only matches STAR 2.7.11a
    genome_build: "{genome_build}"   # WILDCARD — matches any GenomeBuild
    sample: "{sample}"               # WILDCARD — matches any Sample
    quality_cutoff: "{quality_cutoff}"  # WILDCARD — matches any value
```

A request for `AlignmentFile{aligner=toolv-hisat2, genome_build=..., ...}` would NOT
match this rule because `aligner` is fixed to the STAR ToolVersion UUID. A separate
`align_reads_hisat2` rule would be needed.

**No rule found:**

```
CanonNoRuleError: No rule found to produce AlignmentFile with parameters:
  aligner: uuid:toolv-hisat2-200
  genome_build: uuid:gbuild-grch38
  sample: uuid:sample-ad001
  quality_cutoff: 20
  min_length: 30

Installed rules for AlignmentFile:
  align_reads  (aligner=uuid:toolv-star-2711a, genome_build=*, sample=*, ...)

Suggestion: Install a Canon workflow package that provides HISAT2 alignment,
or author a canon_rules.yaml entry for this combination.
```

The error message includes the installed rules and a suggestion — this is the primary
user-facing error for missing workflow coverage.

---

### 4.5 Phase 4: Recursive Input Resolution + Execution

Once a matching rule is found, Canon resolves its required inputs recursively and then
executes.

#### 4.5.1 Wildcard Binding

First, bind the rule's wildcards to concrete values from the request spec:

```python
def bind_wildcards(rule: Rule, resolved_params: dict) -> dict:
    """Bind rule wildcards to values from the request spec."""
    bindings = {}
    for param_name, param_expr in rule.produces.match.items():
        if is_wildcard(param_expr):
            wildcard_name = extract_wildcard_name(param_expr)  # "{sample}" → "sample"
            if wildcard_name not in resolved_params:
                raise CanonPlanningError(f"Unbound wildcard: {wildcard_name}")
            bindings[wildcard_name] = resolved_params[param_name]
    return bindings
```

#### 4.5.2 Cycle Detection

Before recursing into required inputs, Canon checks whether this resolution is already
in progress (which would indicate a circular rule dependency):

```python
# Grey set: entity specs currently being resolved (in the call stack)
_in_progress: set[tuple] = set()

def resolve(entity_type: str, resolved_params: dict) -> str:
    spec_key = (entity_type, frozenset(resolved_params.items()))

    if spec_key in _in_progress:
        cycle = find_cycle_path(_in_progress, spec_key)
        raise CanonCycleError(
            f"Circular rule dependency detected: {' → '.join(cycle)}",
            cycle_path=cycle
        )

    _in_progress.add(spec_key)
    try:
        return _resolve_inner(entity_type, resolved_params)
    finally:
        _in_progress.discard(spec_key)
```

Cycles are detected before any execution begins. The error includes the full cycle path
so the rule author can identify which rules need to be fixed.

#### 4.5.3 Recursive Input Resolution

For each `requires:` entry in the matched rule, resolve the required input by calling
`resolve()` recursively with the binding-substituted parameters:

```python
def resolve_inputs(rule: Rule, bindings: dict) -> dict[str, str]:
    """Resolve all required inputs. Returns {binding_name: uri}."""
    resolved_inputs = {}

    for req in rule.requires:
        # Substitute wildcards in requires.match using current bindings
        req_params = substitute_wildcards(req.match, bindings)

        # Resolve entity refs in req_params
        req_params = resolve_all_entity_refs(req_params)

        # Recursive call — may REUSE or trigger further BUILD
        input_uri = resolve(req.entity_type, req_params)
        resolved_inputs[req.bind] = input_uri

    return resolved_inputs
```

Each recursive call is fully independent — it may hit Hippo (REUSE) or trigger its own
BUILD recursively. The tree of BUILD decisions forms the minimal set of computations
needed to satisfy the original request.

**Execution order:** inputs are resolved sequentially in the order listed in `requires:`.
In v0.1, Canon does not parallelize input resolution. Sequential resolution means a BUILD
at a deep level completes before Canon attempts the next input at the same level.

#### 4.5.4 Execution

With all inputs resolved to concrete URIs, Canon invokes the CWL executor:

```python
def execute(rule: Rule, bindings: dict, resolved_inputs: dict) -> str:
    """Execute the CWL workflow. Returns the output entity URI."""

    # Build CWL inputs.json from execute.inputs expressions
    cwl_inputs = evaluate_input_expressions(
        rule.execute.inputs,
        bindings=bindings,
        resolved_inputs=resolved_inputs,
        hippo=hippo_client
    )

    # Stage any remote URIs to local paths if executor requires it
    staged_inputs = input_staging_layer.stage(cwl_inputs, executor)

    # Execute CWL workflow
    cwl_result = executor.run(
        cwl_path=resolve_workflow_path(rule.execute.workflow),
        inputs=staged_inputs,
        work_dir=new_work_dir(rule.name)
    )

    # Ingest outputs into Hippo
    output_uri = output_ingestion.ingest(
        cwl_result=cwl_result,
        sidecar=load_sidecar(rule.execute.workflow),
        bindings=bindings,
        resolved_inputs=resolved_inputs
    )

    return output_uri
```

#### 4.5.5 Execution Atomicity

Canon writes a `WorkflowRun` entity to Hippo with `status=running` before execution
begins. On completion, it updates to `status=completed`. On failure, it updates to
`status=failed` with error details.

This means interrupted executions leave a `WorkflowRun` entity in `status=running` in
Hippo. On the next `canon get` for the same spec:

1. Registry lookup finds no `AlignmentFile` entity (the output wasn't ingested)
2. Canon checks for in-progress `WorkflowRun` entities for the same rule + parameters
3. If found with `status=running`: Canon raises `CanonExecutorError: execution already in
   progress` rather than launching a duplicate run
4. If found with `status=failed`: Canon re-runs (the previous failure is logged but doesn't
   block retry)

This prevents duplicate execution of the same artifact while allowing transparent retry
after failures.

---

### 4.6 Complete Algorithm Pseudocode

```python
def canon_get(entity_type: str, raw_params: dict) -> str:
    """
    Main entry point. Returns URI of the requested artifact.
    Raises CanonError subclass on failure.
    """

    # Phase 1: Resolve entity references
    resolved_params = {}
    for key, value in raw_params.items():
        if is_entity_ref(value):
            resolved_params[key] = resolve_entity_ref(value)  # → UUID
        else:
            resolved_params[key] = value  # scalar passes through

    # Phase 2: Registry lookup
    entity = hippo.find_entity(entity_type, resolved_params)
    if entity:
        return entity.uri  # REUSE — done

    # Check for in-progress WorkflowRun
    in_progress = hippo.find_workflow_run(entity_type, resolved_params, status="running")
    if in_progress:
        raise CanonExecutorError(
            f"Execution already in progress (WorkflowRun {in_progress.id}). "
            f"Wait for it to complete or check 'canon status'."
        )

    # Phase 3: Rule matching
    rule = rule_registry.find_rule(entity_type, resolved_params)
    if not rule:
        raise CanonNoRuleError(entity_type, resolved_params,
                               available=rule_registry.rules_for_entity_type(entity_type))

    # Cycle detection
    spec_key = (entity_type, frozenset(resolved_params.items()))
    if spec_key in _resolution_stack:
        raise CanonCycleError(..., cycle_path=list(_resolution_stack) + [spec_key])

    _resolution_stack.add(spec_key)
    try:
        # Phase 4a: Bind wildcards
        bindings = bind_wildcards(rule, resolved_params)

        # Phase 4b: Resolve required inputs (recursive)
        resolved_inputs = {}
        for req in rule.requires:
            req_params = substitute_wildcards(req.match, bindings)
            req_params = {k: resolve_entity_ref(v) if is_entity_ref(v) else v
                         for k, v in req_params.items()}
            resolved_inputs[req.bind] = canon_get(req.entity_type, req_params)

        # Phase 4c: Execute
        return execute(rule, bindings, resolved_inputs)

    finally:
        _resolution_stack.discard(spec_key)
```

---

### 4.7 `canon plan` — Dry Run Mode

`canon plan` runs Phases 1–3 for the full dependency tree without executing anything.
It reports the REUSE/BUILD decision for every node in the dependency graph:

```bash
canon plan AlignmentFile \
  --param "aligner=ref:ToolVersion{tool.name=STAR,version=2.7.11a}" \
  --param "genome_build=ref:GenomeBuild{name=GRCh38}" \
  --param "sample=ref:Sample{id=AD002}" \
  --param quality_cutoff=20 \
  --param min_length=30 \
  --param cutadapt_version=4.4
```

Output:
```
Canon execution plan
────────────────────────────────────────────────────────
🟡 BUILD  AlignmentFile
           aligner=STAR/2.7.11a  genome_build=GRCh38  sample=AD002
           rule: align_reads → workflows/star_align.cwl

  🟢 REUSE  TrimmedFastqFile
             sample=AD002  trimmer=cutadapt/4.4  quality_cutoff=20  min_length=30
             entity: uuid:trimmed-ad002  uri: s3://bucket/AD002.trimmed.fastq.gz

  🟢 REUSE  StarIndex
             genome_build=GRCh38  aligner=STAR/2.7.11a
             entity: uuid:starindex-grch38  uri: s3://refs/GRCh38_STAR_2.7.11a/

Summary: 1 BUILD (1 CWL execution), 2 REUSE (0 executions)
Estimated storage: ~4.5 GB (AlignmentFile)
```

`canon plan` is recommended before any `canon run` to verify the dependency tree is
resolved correctly and no unexpected BUILD nodes are present.

---

### 4.8 Error Taxonomy

| Error class | Phase | Cause | Recovery |
|---|---|---|---|
| `CanonResolutionError` | 1 | `ref:T{...}` matches zero or multiple entities | Add entity to Hippo, or refine ref expression |
| `CanonPlanningError` | 1, 4a | Unbound wildcard; required param missing from request | Supply the missing parameter |
| `CanonNoRuleError` | 3 | No rule can produce the requested artifact | Install a workflow package or author a rule |
| `CanonCycleError` | 4b | Circular rule dependency | Fix rule definitions |
| `CanonExecutorError` | 4c | CWL execution failed; duplicate execution in progress | Check CWL logs; wait for in-progress run |
| `CanonIngestionError` | 4c | Output ingestion to Hippo failed | Check Hippo connectivity; check sidecar mappings |
| `CanonConfigError` | startup | `canon.yaml` invalid; Canon entity types missing from Hippo | Run `hippo reference install canon` |
| `CanonRuleValidationError` | startup | Rule validation failed (bad syntax, missing CWL, etc.) | Fix rule definitions |

---

### 4.9 Wildcard Resolution Test Coverage Criteria

This section defines the minimum test scenarios required to validate the wildcard binding and resolution algorithm. All scenarios map to the test suite at `canon/tests/test_resolution_algorithm.py`.

#### 4.9.1 Wildcard Binding — Core Cases

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-01` | Single wildcard in `produces.match`, bound by request | Wildcard binds to request value; rule matches; BUILD proceeds |
| `WC-02` | Multiple wildcards, all bound by request | All wildcards bind; rule matches |
| `WC-03` | Mixed: one fixed param + one wildcard; request matches fixed param | Rule matches; wildcard binds to request value |
| `WC-04` | Mixed: one fixed param + one wildcard; request provides different fixed param value | Rule does NOT match; `CanonNoRuleError` raised with available rules listed |
| `WC-05` | Wildcard present in rule but key absent from request | `CanonPlanningError: unbound wildcard` raised before rule matching |
| `WC-06` | Request has extra keys not in rule `produces.match` | Extra keys are ignored; rule still matches (rule declares minimum identity fields) |

#### 4.9.2 Wildcard in Entity Reference Expressions

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-10` | `ref:GenomeBuild{name={genome_build}}` — wildcard bound in request | Wildcard substituted before ref resolution; Hippo query uses concrete value |
| `WC-11` | `ref:ToolVersion{tool.name=STAR, version={star_version}}` — partial wildcard in nested ref | Dot-notation field is static; version field is wildcard; both resolved correctly |
| `WC-12` | Wildcard in ref but wildcard not yet bound (no value in request) | `CanonPlanningError: unbound wildcard in ref expression` raised in Phase 1 before Hippo query |
| `WC-13` | Ref expression wildcard resolves to zero Hippo entities | `CanonResolutionError: No <T> entity found` (not a planning error — the wildcard was bound but the entity doesn't exist) |
| `WC-14` | Ref expression wildcard resolves to multiple Hippo entities | `CanonResolutionError: Ambiguous reference` |

#### 4.9.3 Wildcard Propagation into `requires`

When a rule's wildcards are bound, those bindings are substituted into all `requires:` entries before recursive resolution begins.

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-20` | Top-level wildcard `{sample}` propagates into `requires.match: {sample: "{sample}"}` | Recursive `canon_get` receives concrete sample UUID, not the placeholder string |
| `WC-21` | Wildcard propagated to requires, required entity exists (REUSE) | Input resolved to URI without BUILD; outer BUILD proceeds with correct input |
| `WC-22` | Wildcard propagated to requires, required entity absent (BUILD) | Recursive BUILD triggered; outer BUILD receives URI from nested BUILD |
| `WC-23` | Wildcard binds differently at two requires levels in the same rule | Each `requires` entry substitutes from the shared bindings dict; no cross-contamination between entries |

#### 4.9.4 Rule Ambiguity — Multiple Matching Rules

In v0.1, if two rules both match a request (same entity type, compatible wildcards, same fixed params), Canon should raise an error rather than silently picking one.

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-30` | Two rules for same entity type, both fully wildcard on all params | `CanonConfigError: ambiguous rules` at startup validation (rules are validated at load time, not per-request) |
| `WC-31` | Two rules for same entity type, one more specific (fixed param) than the other | More specific rule matches first; less specific rule is not selected (specificity ordering: more fixed params win) |

**Note on specificity ordering (v0.1):** Rules are ranked by the count of fixed (non-wildcard) parameters — more fixed params = higher specificity. When specificity is equal and both rules match, a startup validation error is raised. This ensures deterministic rule selection without silent surprises.

#### 4.9.5 Cycle Detection

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-40` | Rule A requires B; rule B requires A (direct cycle) | `CanonCycleError` raised on the second visit; cycle path is `[A, B, A]` |
| `WC-41` | Rule A requires B requires C requires A (transitive cycle) | `CanonCycleError` raised when A is encountered again; full path included |
| `WC-42` | Diamond dependency: A requires B and C; both B and C require D (not a cycle) | Resolves correctly; D is built once (REUSE on second resolution of D) |

#### 4.9.6 Interrupted Execution Re-entry

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-50` | `WorkflowRun` entity with `status=running` exists for same spec | `CanonExecutorError: execution already in progress` — duplicate execution blocked |
| `WC-51` | `WorkflowRun` entity with `status=failed` exists for same spec | Canon proceeds to re-run (failed state does not block retry) |
| `WC-52` | `WorkflowRun` entity with `status=completed` but no output entity in Hippo | Treated as a BUILD miss — re-run proceeds (output was lost or not ingested) |

#### 4.9.7 `canon plan` Dry-Run Coverage

| Test ID | Scenario | Expected Outcome |
|---------|----------|-----------------|
| `WC-60` | All inputs REUSE, top-level BUILD | Plan shows 1 BUILD node, N REUSE nodes; no execution triggered |
| `WC-61` | Top-level REUSE | Plan shows single REUSE node; no BUILD nodes |
| `WC-62` | Nested BUILD chain (A builds B builds C) | Plan shows all three as BUILD; correct depth ordering in output |
| `WC-63` | Cycle in dependency tree during `canon plan` | `CanonCycleError` raised during planning phase; error includes cycle path |
