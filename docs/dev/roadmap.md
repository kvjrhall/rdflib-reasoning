# Development Roadmap

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## 1. How to use this document

- `architecture.md` is the authoritative description of intended system structure and behavior.
- `roadmap.md` is the authoritative description of planned feature sequencing, release scope, and delivery priority.
- The codebase remains the authority on current implementation status.
- When `roadmap.md` and `architecture.md` disagree about whether a feature belongs in the current intended scope, Development Agents MUST stop and resolve that discrepancy before continuing with substantial implementation work.
- Roadmap entries SHOULD link to the corresponding `architecture.md` section when such a section already exists and the link improves navigation without overloading the document.

## 2. Planning assumptions

- The first planned release is `0.1.0`.
- Release planning is intentionally incremental. A later release MAY be re-scoped when implementation feedback, validation work, or design clarification shows that a planned feature is under-specified or too large for the target release.
- A roadmap item may appear before it has a full architectural section. In that case, the item MUST be treated as planned intent, not fully authorized design.

## 3. Release `0.1.0`: Reasoning and proof baseline

Priority: highest

This release establishes the minimum coherent platform for graph-backed reasoning experiments, proof interchange, and baseline evaluation.

### 3.1. In scope

1. Dataset-backed middleware foundation
   - Deliver the foundational dataset lifecycle needed by higher middleware layers.
   - Architecture: [Dataset middleware](architecture.md#dataset-middleware)
1. Middleware capability gating
   - Ensure dataset, retrieval, and inference capabilities are enabled or withheld through middleware composition rather than hidden prompt changes or ad hoc runtime paths.
   - Architecture: [Middleware composition and capability gating](architecture.md#middleware-composition-and-capability-gating)
1. Structural-element and middleware interoperability baseline
   - Preserve `GraphBacked` and `StructuralElement` as the schema-facing contract between middleware and Research Agents.
   - Architecture: [Structural elements and middleware](architecture.md#structural-elements-and-middleware)
1. RETE engine add-only baseline
   - Deliver the supported store integration path, fixed-point update behavior, derivation logging contract, and add-only JTMS-compatible support bookkeeping.
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
   - Architecture: [RETE Engine Design](architecture.md#rete-engine-design)
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
1. RDF triple well-formedness enforcement
   - Enforce RDF 1.1 subject and predicate constraints at the engine boundary with a configurable handling policy.
   - Architecture: [RDF Data-Model Enforcement](architecture.md#rdf-data-model-enforcement)
1. Proof interchange and baseline evaluation harness
   - Deliver `DirectProof`-oriented evaluation inputs and outputs sufficient for a baseline notebook and structured assessments.
   - Architecture: [Proof evaluation harness](architecture.md#proof-evaluation-harness)
   - Architecture: [Proof evaluation harness inputs and outputs](architecture.md#proof-evaluation-harness-inputs-and-outputs)
   - Architecture: [Baseline scope](architecture.md#baseline-scope)
   - Architecture: [Initial proof evaluation dimensions](architecture.md#initial-proof-evaluation-dimensions)
1. Initial proof rendering layer
   - Provide presentation-focused rendering over canonical proof data, with markdown-friendly output as the initial target.
   - Architecture: [Proof rendering](architecture.md#proof-rendering)
1. Initial contradiction signaling
   - Support contradiction detection and independently configurable signaling behavior.
   - Architecture: [Contradiction signaling](architecture.md#contradiction-signaling)

### 3.2. Exit criteria

- A Research Agent can operate over dataset-backed state with inference capability exposed only through explicit middleware composition.
- The engine supports the documented add-only fixed-point flow and derivation logging baseline.
- Proofs can be represented, assessed, and rendered through stable typed interfaces.
- Any `0.1.0` feature lacking sufficient architectural detail MUST either be clarified in `architecture.md` before implementation or deferred to a later release.

## 4. Release `0.2.0`: Retrieval and experiment expansion

Priority: high

This release expands the baseline into a more capable experimental platform by adding controlled knowledge import and richer evaluation ergonomics.

### 4.1. In scope

1. Knowledge retrieval middleware
   - Add remote RDF retrieval and structured site metadata ingestion as explicit middleware capabilities over dataset-backed state.
   - Architecture: [Knowledge retrieval middleware](architecture.md#knowledge-retrieval-middleware)
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

### 4.2. Exit criteria

- Retrieval remains capability-gated and composes cleanly over dataset middleware.
- Imported knowledge can be traced to its source in a way suitable for debugging and evaluation.
- Any new retrieval-facing schema exposed to a Research Agent is explicit, typed, and inspectable.

## 5. Release `0.3.0`: Retraction and advanced engine behavior

Priority: medium

This release completes the staged engine plan for support-aware removal and begins more advanced optimization and explanation work.

### 5.1. In scope

1. JTMS support verification APIs
   - Expose support-checking behavior needed to decide whether conclusions remain justified after a support path is invalidated.
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
1. Recursive retraction
   - Implement Mark-Verify-Sweep removal over the dependency graph and wire full removal through the supported integration path.
   - Architecture: [Truth Maintenance System (TMS)](architecture.md#truth-maintenance-system-tms)
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
1. Removal-aware store and engine flow
   - Complete the intended remove-event contract without treating event arrival alone as sufficient for logical removal.
   - Architecture: [Engine event contract and entrypoint](architecture.md#engine-event-contract-and-entrypoint)
1. Specialized relation indexes
   - Evaluate and implement targeted acceleration for selected schema-lattice relations where justified.
   - Architecture: [Rule Matching & Network Topology](architecture.md#rule-matching--network-topology)
1. Richer contradiction explanation
   - Improve explanation behavior for contradictions once derivation and support data are sufficient.
   - Architecture: [Contradiction signaling](architecture.md#contradiction-signaling)
   - Architecture: [Proof evaluation harness](architecture.md#proof-evaluation-harness)

### 5.2. Exit criteria

- Derived facts remain present or are removed according to support validity rather than naive event mirroring.
- Retraction behavior preserves the architectural support invariants for stated and derived facts.
- Performance-oriented engine additions do not weaken the explicit proof and derivation contracts established earlier.

## 6. Release review rules

- Development Agents SHOULD consult this roadmap when estimating scope, selecting the next feature to implement, or deciding whether a task belongs in the current release.
- Development Agents MUST verify that this roadmap remains accurate before closing a substantial feature task that changes Python behavior, middleware capability boundaries, release scope, or architectural assumptions.
- Development Agents MUST consider reprioritizing roadmap items or moving scope across releases when implementation uncovers missing architectural detail, hidden dependency chains, validation failures, or feature slices too large to complete coherently within the current release target.
