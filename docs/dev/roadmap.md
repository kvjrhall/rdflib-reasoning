# Development Roadmap

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## 1. How to use this document

- `architecture.md` is the authoritative description of intended system structure and behavior.
- `roadmap.md` is the authoritative description of planned feature sequencing, release scope, and delivery priority.
- The codebase remains the authority on current implementation status.
- When `roadmap.md` and `architecture.md` disagree about whether a feature belongs in the current intended scope, Development Agents MUST stop and resolve that discrepancy before continuing with substantial implementation work.
- Roadmap entries SHOULD link to the corresponding `architecture.md` section when such a section already exists and the link improves navigation without overloading the document.

## 2. Planning assumptions

- Release planning is intentionally incremental. A later release MAY be re-scoped when implementation feedback, validation work, or design clarification shows that a planned feature is under-specified or too large for the target release.
- A roadmap item may appear before it has a full architectural section. In that case, the item MUST be treated as planned intent, not fully authorized design.

## 3. Release `0.1.0`: Reasoning and proof baseline (released)

Priority: highest

This release establishes the minimum coherent platform for graph-backed reasoning experiments, proof interchange, and baseline demonstration.

### 3.1. In scope

1. Structural-element and middleware interoperability baseline
   - Preserve `GraphBacked` and `StructuralElement` as the schema-facing contract between middleware and Research Agents.
   - Architecture: [Structural elements and middleware](architecture.md#structural-elements-and-middleware)
1. RETE engine add-only baseline
   - Deliver the supported store integration path, fixed-point update behavior, derivation logging contract, complete informative RDFS entailment rules (`rdfs1`-`rdfs13`), and add-only JTMS-compatible support bookkeeping.
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
   - Architecture: [RETE Engine Design](architecture.md#rete-engine-design)
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
1. RDF triple well-formedness enforcement
   - Enforce RDF 1.1 subject and predicate constraints at the engine boundary with a configurable handling policy.
   - Architecture: [RDF Data-Model Enforcement](architecture.md#rdf-data-model-enforcement)
1. Proof interchange models
   - Implemented: `DirectProof` and related proof payload models provide stable typed proof interchange for baseline notebooks, engine-reconstructed explanations, and future evaluation tooling.
   - Architecture: [Proof reconstruction and explanation](architecture.md#proof-reconstruction-and-explanation)
1. Initial proof rendering layer
   - Provide presentation-focused rendering over canonical proof data, with markdown-friendly output as the initial target.
   - Architecture: [Proof rendering](architecture.md#proof-rendering)
1. Initial contradiction signaling
   - Implemented: dual-channel contradiction detection with independently configurable signaling behavior.
   - Implemented: contradiction detection targets currently modeled OWL 2 RL contradiction-producing `false` rules and records non-mutating diagnostics without requiring contradiction triple materialization.
   - Architecture: [Contradiction signaling](architecture.md#contradiction-signaling)
   - Decision: [DR-027 Dual-Channel Contradiction Diagnostics and Explanation Contract](decision-records/DR-027%20Dual-Channel%20Contradiction%20Diagnostics%20and%20Explanation%20Contract.md)

### 3.2. Exit criteria

- The engine supports the documented add-only fixed-point flow and derivation logging baseline.
- The engine provides the complete informative RDFS entailment baseline (`rdfs1`-`rdfs13`) within that add-only flow.
- Proofs can be represented and rendered through stable typed interfaces.

## 4. Release `0.2.0`: Dataset middleware and experiment foundation (released)

Priority: highest

This release delivers the foundational dataset-backed middleware and the initial experiment notebook series.

### 4.1. In scope

1. Dataset-backed middleware foundation
   - Deliver the foundational dataset lifecycle needed by higher middleware layers.
   - Keep copied runtime state lightweight by treating live RDFLib datasets and coordination objects as middleware-owned infrastructure rather than `AgentState` payload.
   - Provide per-dataset multi-reader / single-writer coordination for dataset-backed tool, retrieval, and inference access without expanding the scope to general transaction support.
   - Limit `0.2.0` dataset middleware scope to the default-graph baseline: list triples, add triples, remove triples, serialize current state, and reset the dataset.
   - Implement Research Agent-facing dataset tools as thin adapters over internal middleware methods so later middleware layers and tests can compose over one source of truth.
   - Architecture: [Dataset middleware](architecture.md#dataset-middleware)
1. Middleware capability gating
   - Ensure dataset, retrieval, and inference capabilities are enabled or withheld through middleware composition rather than hidden prompt changes or ad hoc runtime paths.
   - Architecture: [Middleware composition and capability gating](architecture.md#middleware-composition-and-capability-gating)
1. Schema-facing RDF boundary models
   - Deliver Pydantic-based boundary models with lexical RDF wire forms, reusable schema aliases, and concise normative descriptions for the Research Agent communication surface.
   - Architecture: [Schema-facing RDF boundary models](architecture.md#schema-facing-rdf-boundary-models)
1. Middleware-owned dataset sessions and coordination
   - Deliver per-dataset session ownership and multi-reader / single-writer coordination.
   - Architecture: [Dataset middleware](architecture.md#dataset-middleware)
1. Dataset middleware internal method and tool adapter pattern
   - Maintain a clear separation between internal RDFLib-native methods and Research Agent-facing tool adapters.
   - Architecture: [Dataset middleware internal methods and tool adapters](architecture.md#dataset-middleware-internal-methods-and-tool-adapters)
1. Baseline and middleware demo notebooks
   - Deliver the prompt-only baseline (`demo-baseline-ontology-extraction.ipynb`) and dataset middleware condition (`demo-dataset-middleware.ipynb`) with shared evaluation infrastructure (`demo_utils.py`).

### 4.2. Exit criteria

- A Research Agent can operate over dataset-backed state with capabilities exposed only through explicit middleware composition.
- The `0.2.0` dataset middleware surface is limited to the default-graph baseline and does not yet require named-graph management or generic quad-level CRUD.
- Baseline and middleware conditions are comparable through shared evaluation metrics with reduced prompt asymmetry.

## 5. Release `0.3.0`: Vocabulary middleware and namespace discipline (released)

Priority: high

This release adds vocabulary inspection and namespace-discipline capabilities to the middleware stack, enabling Research Agents to discover, inspect, and correctly use established RDF vocabularies.
This release is currently in progress. The items below describe the intended
`0.3.0` release target, and individual pull requests MAY deliver only a subset
of that target while the remaining items stay explicitly deferred.

### 5.1. In scope

1. RDF vocabulary middleware
   - Deliver indexed vocabulary retrieval and inspection tools (`list_vocabularies`, `list_terms`, `search_terms`, `inspect_term`) as an explicit middleware capability over locally-bundled specification files.
   - Make `search_terms` the intended primary discovery path when a Research Agent knows the meaning it wants to express but not yet the correct indexed term.
   - Architecture: [RDF vocabulary middleware](architecture.md#rdf-vocabulary-middleware)
   - Decision: [DR-017 Search-First RDF Vocabulary Retrieval](decision-records/DR-017%20Search-First%20RDF%20Vocabulary%20Retrieval.md)
1. Namespace whitelisting for dataset middleware
   - Deliver opt-in namespace whitelisting with three affordances: enforcement (rejecting non-whitelisted URIs), enumeration (listing allowed vocabularies in the prompt), and remediation (Levenshtein-based suggestions for near-miss terms in closed vocabularies).
   - Architecture: [Namespace whitelisting](architecture.md#namespace-whitelisting)
   - Decision: [DR-014 Namespace Whitelisting for Dataset Middleware](decision-records/DR-014%20Namespace%20Whitelisting%20for%20Dataset%20Middleware.md)
1. Shared middleware services and unified vocabulary configuration
   - Deliver explicit shared-service injection for dataset runtime, shared vocabulary policy, and run-local term telemetry.
   - Make `VocabularyConfiguration` the only declarative vocabulary setup surface.
   - Add `VocabularyContext` as the validated cached runtime vocabulary object injected into both dataset and vocabulary middleware.
   - Keep cross-middleware sharing explicit rather than relying on middleware composition order or raw whitelist/cache wiring.
   - Architecture: [Dataset middleware](architecture.md#dataset-middleware)
   - Architecture: [Shared middleware services](architecture.md#shared-middleware-services)
   - Architecture: [RDF vocabulary middleware](architecture.md#rdf-vocabulary-middleware)
   - Decision: [DR-020 Middleware Stack Layering and Hook-Role Boundaries](decision-records/DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md)
1. Expanded indexed vocabulary set
   - Enable declared bundled vocabulary resources for at minimum RDF, RDFS, OWL, SKOS, and PROV. Additional well-known vocabularies MAY be enabled by extending the standard bundled vocabulary declarations in the vocabulary layer.
   - Architecture: [RDF vocabulary middleware](architecture.md#rdf-vocabulary-middleware)
1. Using VANN annotation metadata
   - Implemented: `vann:preferredNamespacePrefix` and `vann:preferredNamespaceUri` are surfaced as advisory metadata for indexed vocabulary summaries when present in bundled or user-supplied vocabularies.
   - VANN metadata improves discovery ergonomics for `RDFVocabularyMiddleware`, but MUST NOT override declared namespace policy, `VocabularyContext`, or whitelist enforcement.
   - Architecture: [RDF vocabulary middleware](architecture.md#rdf-vocabulary-middleware)
1. Vocabulary middleware demo notebook
   - Align `demo-vocabulary-middleware.ipynb` with the shared evaluation infrastructure (`demo_utils.py`) established in `0.2.0`, including shared prompts, evaluation metrics, and the parseability gate pattern.
1. Middleware execution discipline hardening
   - Add optional `ContinuationGuardMiddleware` for single-run, completion-oriented Research Agent harnesses so unfinished recovery narration and plan-only exits can be re-prompted without coupling that behavior to model-specific prompt middleware.
   - Architecture: [Continuation guard middleware](architecture.md#continuation-guard-middleware)
   - Decision: [DR-020 Middleware Stack Layering and Hook-Role Boundaries](decision-records/DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md)
1. Silent-rule visibility and bootstrap-axiom execution
   - Introduce immutable rule-level silence semantics where `Rule.silent` defines default normal-operation visibility while `DerivationRecord.silent` carries effective per-firing visibility.
   - Require silent derivations to remain present in engine-native derivation logs using visibility metadata, while user-facing proof reconstruction excludes silent records.
   - Track bootstrap-phase firings explicitly in derivation logs so bootstrap overrides do not overload rule-level `silent`.
   - Execute zero-precondition bootstrap rules once per engine-context initialization before warmup over existing graph content; reopening a context MAY re-run bootstrap idempotently.
   - Keep triples produced solely by bootstrap and bootstrap-only closure internal to the engine so empty-graph startup does not materialize background vocabulary closure.
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
   - Decision: [DR-022 Bootstrap-Phase Effective Visibility and Derivation Metadata](decision-records/DR-022%20Bootstrap-Phase%20Effective%20Visibility%20and%20Derivation%20Metadata.md)

### 5.2. Exit criteria

- A Research Agent with the completed `0.3.0` vocabulary middleware can
  discover relevant indexed vocabulary terms through search and inspect them
  before using them in `add_triples`.
- Dataset-backed middleware uses an explicit `VocabularyContext` rather than
  bare constructors or separately wired whitelist/cache objects.
- Dataset and vocabulary middleware can share an explicitly injected runtime,
  vocabulary context, and run-local telemetry service without implicit
  middleware discovery.
- Vocabulary middleware can surface VANN annotation metadata for indexed
  vocabularies when it is present, without changing which namespaces are
  declared or whitelisted.
- The vocabulary middleware demo notebook uses the same shared evaluation infrastructure as baseline and dataset middleware demos, enabling quantitative comparison across all three conditions.
- The completed `0.3.0` indexed vocabulary set includes at minimum the core
  Semantic Web vocabularies (RDF, RDFS, OWL, SKOS, PROV).
- Optional continuation-guard middleware is available for single-run harnesses without being implied for multi-round conversational agents.
- Silent-rule visibility semantics are implemented so silent derivations remain logged while reconstructed user-facing proofs exclude silent records.
- Zero-precondition bootstrap rules execute once per engine-context initialization before warmup over existing graph content, with idempotent behavior across reopen/recreate and without materializing bootstrap-only closure back into the graph.

## 6. Release `0.4.0`: Retrieval and experiment expansion

Priority: high

This release expands the baseline into a more capable experimental platform by adding controlled knowledge import and richer evaluation ergonomics.

### 6.1. In scope

1. Knowledge retrieval middleware
   - Add remote RDF retrieval and structured site metadata ingestion as explicit middleware capabilities over dataset-backed state.
   - Architecture: [Knowledge retrieval middleware](architecture.md#knowledge-retrieval-middleware)
1. Named-graph dataset middleware expansion
   - Add named graph management and graph-scoped triple operations after the default-graph baseline is stable.
   - Architecture: [Dataset middleware capability phases](architecture.md#dataset-middleware-capability-phases)
1. Provenance-bearing retrieval outputs
   - Ensure imported facts or retrieval artifacts retain provenance sufficient for explanation and evaluation.
   - Architecture: [Knowledge retrieval middleware](architecture.md#knowledge-retrieval-middleware)
1. Schema-driven retrieval boundary objects
   - Model runtime-visible retrieval outputs as `GraphBacked` structures when they cross the Research Agent boundary.
   - Architecture: [Structural elements and middleware](architecture.md#structural-elements-and-middleware)
   - Architecture: [Knowledge retrieval middleware](architecture.md#knowledge-retrieval-middleware)
1. Broader proof-evaluation workflow support
   - Extend the harness only as needed for follow-on experiments while preserving the framework-agnostic typed contract.
   - Architecture: [Proof evaluation harness](architecture.md#proof-evaluation-harness)
1. Notebook-friendly proof presentation improvements
   - Improve human-readable proof outputs without mutating canonical proof structures.
   - Architecture: [Proof rendering](architecture.md#proof-rendering)

### 6.2. Exit criteria

- Retrieval remains capability-gated and composes cleanly over dataset middleware.
- Imported knowledge can be traced to its source in a way suitable for debugging and evaluation.
- Any new retrieval-facing schema exposed to a Research Agent is explicit, typed, and inspectable.

## 7. Release `0.5.0`: Retraction and advanced engine behavior

Priority: medium

This release completes the staged engine plan for support-aware removal and begins more advanced optimization and explanation work.

### 7.1. In scope

1. JTMS support verification APIs
   - Implemented: `TMSController` exposes read-only support snapshots, hypothetical support-path invalidation checks, transitive support verification, and dependency traversal APIs needed to decide whether conclusions remain justified after a support path is invalidated.
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
   - Decision: [DR-023 JTMS Support Verification API Surface](decision-records/DR-023%20JTMS%20Support%20Verification%20API%20Surface.md)
1. Explicit dataset and quad operations
   - Add generic quad-level CRUD and other explicitly dataset-scoped operations only after earlier graph-oriented middleware phases have proven necessary and stable.
   - Architecture: [Dataset middleware capability phases](architecture.md#dataset-middleware-capability-phases)
1. Recursive retraction
   - Implemented at the TMS-controller layer: `TMSController.retract_triple` performs Mark-Verify-Sweep over the dependency graph and returns a `RetractionOutcome` describing swept facts, dropped justifications, and stated-flag clearings.
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
   - Decision: [DR-024 TMSController Recursive Retraction](decision-records/DR-024%20TMSController%20Recursive%20Retraction.md)
1. Removal-aware store and engine flow
   - Implemented end-to-end: `RETEEngine.retract_triples(Iterable[Triple]) -> set[Triple]` composes `TMSController.retract_triple`, evicts stale alpha/beta partial matches, and is idempotent for already-absent triples (the symmetric counterpart of DR-004's add-side idempotence). `RETEStore.remove` snapshots concrete pattern matches, drives the `BatchDispatcher` event chain, and re-materializes triples the engine still derives with a `RetractionRematerializeWarning` per the policy in DR-025.
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
   - Decision: [DR-025 RETE Store Removal Wiring and Re-Materialization Policy](decision-records/DR-025%20RETE%20Store%20Removal%20Wiring%20and%20Re-Materialization%20Policy.md)
1. Specialized relation indexes
   - Evaluate and implement targeted acceleration for selected schema-lattice relations where justified.
   - Architecture: [Rule Matching & Network Topology](architecture.md#rule-matching--network-topology)
1. Richer contradiction explanation
   - Implemented: contradiction explanation reconstruction builds `DirectProof` for `ContradictionClaim` goals from retained `ContradictionRecord` data (rule application step showing matched premise triples); output uses the same proof rendering path (`ProofRenderer`, notebook adapters) as triple-goal proofs where applicable.
   - Further optional work (nested derivation proofs inside each contradiction premise, middleware harness evaluation surfaces, presentation polish) may be scheduled in later roadmap items without changing the baseline DR-027 contract fulfilled here.
   - Architecture: [Contradiction signaling](architecture.md#contradiction-signaling)
   - Architecture: [Proof rendering](architecture.md#proof-rendering)
   - Decision: [DR-027 Dual-Channel Contradiction Diagnostics and Explanation Contract](decision-records/DR-027%20Dual-Channel%20Contradiction%20Diagnostics%20and%20Explanation%20Contract.md)

### 7.2. Exit criteria

- Derived facts remain present or are removed according to support validity rather than naive event mirroring.
- Retraction behavior preserves the architectural support invariants for stated and derived facts.
- Performance-oriented engine additions do not weaken the explicit proof and derivation contracts established earlier.

## 8. Release `1.0.0`: Citation and presentation baseline

Priority: medium

This release establishes the public-facing citation and presentation baseline expected of a stable, citable software release.

### 8.1. In scope

1. Citation metadata
   - Provide maintained repository citation guidance through `CITATION.cff`.
1. Release citation and archival guidance
   - Document the release citation path and prepare stable DOI-oriented archival integration.
1. Zenodo presentation
   - Add Zenodo-oriented citation guidance and repository badges once the release workflow and metadata are stable.

### 8.2. Exit criteria

- The repository exposes citation metadata that GitHub and downstream users can consume directly.
- Citation guidance is visible to readers of the repository and release artifacts.
- Zenodo badge and citation guidance are present for stable releases.

### 8.3. Open question

- Decide whether repository citation metadata should cite the metapackage release, the software family as a whole, or both.

## 9. Release `1.1.0`: Proof evaluation harness

Priority: medium

This release adds reusable proof-evaluation infrastructure over the proof interchange models delivered in `0.1.0`. The exact scope MAY be re-scoped as experiment needs and evaluator design mature.

### 9.1. In scope

1. Framework-agnostic proof assessment models
   - Deliver Pydantic request/response models for assessing `DirectProof` outputs against task inputs and expected grounding.
   - Architecture: [Proof evaluation harness](architecture.md#proof-evaluation-harness)
   - Architecture: [Proof evaluation harness inputs and outputs](architecture.md#proof-evaluation-harness-inputs-and-outputs)
1. Baseline structured assessment flow
   - Implement a single-pass assessment contract suitable for notebooks and batch experiments before considering richer evaluator agents.
   - Architecture: [Baseline scope](architecture.md#baseline-scope)
   - Architecture: [Initial proof evaluation dimensions](architecture.md#initial-proof-evaluation-dimensions)
1. Baseline proof notebook integration
   - Update the baseline proof notebook to consume the reusable harness rather than defining evaluation ad hoc.

### 9.2. Exit criteria

- Development Agents can run a reusable proof assessment over a proposed `DirectProof` and receive structured results.
- Baseline proof-evaluation notebooks use the shared harness and report conclusions grounded in harness outputs.
- The harness remains framework-agnostic at its core, with any framework-specific adapters kept thin and secondary.

## 10. Release review rules

- Development Agents SHOULD consult this roadmap when estimating scope, selecting the next feature to implement, or deciding whether a task belongs in the current release.
- Development Agents MUST verify that this roadmap remains accurate before closing a substantial feature task that changes Python behavior, middleware capability boundaries, release scope, or architectural assumptions.
- Development Agents MUST consider reprioritizing roadmap items or moving scope across releases when implementation uncovers missing architectural detail, hidden dependency chains, validation failures, or feature slices too large to complete coherently within the current release target.
