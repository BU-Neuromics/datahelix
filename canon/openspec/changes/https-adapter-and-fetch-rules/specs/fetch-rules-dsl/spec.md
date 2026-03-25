## ADDED Requirements

### Requirement: canon_rules.yaml supports fetch rule type

The `canon_rules.yaml` DSL SHALL support a `type: fetch` rule variant alongside the existing production rules. A fetch rule declares that a particular entity type can be materialized by downloading from a known URI rather than executing a CWL workflow.

Fetch rule YAML format:
```yaml
rules:
  - name: fetch_grch38_ensembl110
    type: fetch
    produces:
      entity_type: GenomeBuild
      match:
        name: GRCh38
        source: ensembl
        release: "110"
    fetch:
      source_uri: "https://ftp.ensembl.org/pub/release-110/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz"
      checksum_sha256: "abc123..."   # optional
```

#### Scenario: RulesLoader parses a valid fetch rule
- **WHEN** a `canon_rules.yaml` contains a rule with `type: fetch` and all required fields
- **THEN** `RulesLoader.load()` SHALL return a `FetchRule` instance with `name`, `produces`, `source_uri`, and optional `checksum_sha256` populated

#### Scenario: RulesLoader raises on fetch rule missing source_uri
- **WHEN** a fetch rule has no `fetch.source_uri` field
- **THEN** `RulesLoader.load()` SHALL raise `CanonRulesError` with a message identifying the missing field

#### Scenario: RulesLoader raises on fetch rule with invalid source_uri scheme
- **WHEN** a fetch rule declares `source_uri: "ftp://example.com/..."` (FTP not supported)
- **THEN** `RulesLoader.load()` SHALL raise `CanonRulesError` with a message listing supported schemes (https, http)

#### Scenario: Production rules and fetch rules coexist in same file
- **WHEN** `canon_rules.yaml` contains both `type: fetch` and standard production rules
- **THEN** `RulesLoader.load()` SHALL return both types without error

### Requirement: FetchRule dataclass

The system SHALL define a `FetchRule` dataclass in `canon/rules/models.py` with fields: `name: str`, `produces: ProducesSpec`, `source_uri: str`, `checksum_sha256: Optional[str] = None`.

#### Scenario: FetchRule is distinct from ProductionRule
- **WHEN** `isinstance(rule, FetchRule)` is evaluated on a fetch rule loaded from YAML
- **THEN** it SHALL return `True` and `isinstance(rule, ProductionRule)` SHALL return `False`

### Requirement: RuleRegistry stores and retrieves fetch rules

The `RuleRegistry` SHALL store `FetchRule` instances and expose a `find_fetch_rule(entity_type, params)` method returning the matching `FetchRule` or `None`.

#### Scenario: find_fetch_rule returns matching fetch rule
- **WHEN** `find_fetch_rule("GenomeBuild", {"name": "GRCh38", "source": "ensembl", "release": "110"})` is called
- **THEN** the matching `FetchRule` SHALL be returned

#### Scenario: find_fetch_rule returns None when no match
- **WHEN** `find_fetch_rule("GenomeBuild", {"name": "CHM13", "release": "2.0"})` is called with no matching rule
- **THEN** `None` SHALL be returned
