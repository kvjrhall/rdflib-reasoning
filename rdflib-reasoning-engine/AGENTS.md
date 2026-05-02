# Engine Guidance

The `rdflib-reasoning-engine` package contains RETE-style engine internals and
a smaller set of schema-facing proof, derivation, rule, and contradiction
models. Those categories MUST be kept distinct.

Research Agents may consume package-exposed runtime surfaces through tools,
middleware, generated schemas, or serialized proof outputs. Development Agents
maintain this package and its Development Agent-facing documentation; they are
not runtime callers of this package.

## Authoritative references

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the
  authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Schema-facing RDF boundary models`
  - `Engine event contract and entrypoint`
  - `Proof evaluation harness`
  - `Proof rendering`
  - `RETE Engine Design`
- Treat [`docs/dev/roadmap.md`](../docs/dev/roadmap.md) as the authoritative
  release and priority plan for substantial engine work.
- Treat
  [`docs/dev/decision-records/DR-003 Research Agent and Development Agent Terminology.md`](../docs/dev/decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md)
  as the authoritative rule set for role terminology and visibility boundaries.
- Treat
  [`docs/dev/decision-records/DR-007 Proof Model and Derivation Semantics Refinement.md`](../docs/dev/decision-records/DR-007%20Proof%20Model%20and%20Derivation%20Semantics%20Refinement.md)
  as the authoritative rationale for proof model structure.
- Treat
  [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md)
  as the authoritative rule set for schema-facing runtime models.

## Development-Agent-only spec lookup

- Use [`docs/specs/rdf11-semantics/INDEX.md`](../docs/specs/rdf11-semantics/INDEX.md)
  for RDF and RDFS entailment rules, especially `rdfs1` through `rdfs13`.
- Use
  [`docs/specs/owl2-reasoning-profiles/INDEX.md`](../docs/specs/owl2-reasoning-profiles/INDEX.md)
  for OWL 2 RL operational rule anchors and profile-level rule families.
- Use [`docs/specs/owl2-crosswalks/INDEX.md`](../docs/specs/owl2-crosswalks/INDEX.md)
  for semantic anchors, rule/proof reconstruction context, and coverage
  planning across specifications.
- Use [`docs/specs/jena-inspiration/AGENTS.md`](../docs/specs/jena-inspiration/AGENTS.md)
  only for comparison and design awareness. It is not normative, and repository
  code MUST NOT copy Apache Jena code or documentation.
- These repository-local references are for Development Agents only. Research
  Agents MUST NOT see them at runtime.

## Boundary rules

- Engine-internal components MUST NOT be required serialized inputs or outputs
  across the Research Agent boundary.
- Engine-native derivation records, working-memory structures, agenda state, and
  RETE network objects MUST remain internal unless a separate boundary model
  explicitly reconstructs them for runtime use.
- Proof or derivation models that do cross the runtime boundary SHOULD expose
  concise schema guidance, explicit constraints, and high-fidelity lexical
  examples rather than raw engine internals or extended theory text.
- Heavy runtime helper objects such as stores, graphs, and engine instances MUST
  NOT be required serialized fields in schema-facing proof models.
- Public docstrings, module docstrings, `Field` descriptions,
  `RuleDescription`, tool descriptions, and generated schema text are
  package-consumer or runtime-facing surfaces. They MUST NOT cite
  repository-local specs, crosswalks, `AGENTS.md`, design docs, or source
  comments.
- Non-rendered source comments that cannot become generated documentation MAY
  cite repository-local specs and crosswalks for Development Agents.

## Rule-definition cookbook

- Start from the normative rule source, then encode triple-shaped antecedents as
  `TripleCondition` and explicit read-only guards as `PredicateCondition`.
- Encode materialized logical conclusions as `TripleConsequent`.
- Use `ContradictionConsequent` for non-mutating contradiction diagnostics.
- Use `CallbackConsequent` only for observational, non-logical callbacks.
- Preserve canonical `RuleId` values for spec-facing rules. Document
  production-profile splits, `silent` variants, and implementation-only helper
  rules separately from canonical rule identity.
- Keep runtime-visible `RuleDescription` references package-consumer-safe. Prefer
  official specification URIs over repository-local file paths or generated
  lookup artifacts.

## Builtin cookbook

- `PredicateHook` implementations are read-only tests. They MUST NOT emit
  triples, mutate graph state, or depend on engine-internal object layout.
- `CallbackHook` implementations are observational and non-mutating. They MUST
  NOT affect logical closure.
- Builtins SHOULD fail predictably on arity mismatch. Predicate builtins SHOULD
  return `False` for invalid argument shapes unless a stronger public API
  contract exists.
- Prefer explicit `PredicateCondition` guards for RDF 1.1 term legality,
  profile-specific filtering, and implementation-policy checks that should be
  visible in the rule definition.

## Editing guidance

- When editing proof-facing models, optimize for stable interchange and runtime
  clarity first, not for mirroring internal engine structures one-to-one.
- When editing engine internals, do not introduce shortcuts that accidentally
  make Research Agent boundary behavior depend on internal object layouts or
  debugging representations.

## Testing expectations

- Boundary-facing proof, derivation, rule, contradiction, or description models
  SHOULD have focused Python round-trip tests using `model_dump` and
  `model_validate` when behavior changes.
- Boundary-facing models SHOULD have JSON round-trip tests using
  `model_dump_json` and `model_validate_json` when JSON behavior matters.
- Boundary-facing models SHOULD have `model_json_schema()` smoke tests.
- Add stronger schema assertions when descriptions, aliases, examples, lexical
  RDF forms, required fields, or official reference shape are intended runtime
  contracts.
- Tests SHOULD NOT over-specify incidental Pydantic schema layout unless that
  layout is deliberately part of the runtime boundary contract.
