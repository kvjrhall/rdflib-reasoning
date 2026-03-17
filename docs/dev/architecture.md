# System Architecture

This repository's [high-level overview of system components](../../README.md#component-overview) is found in the root `README.md`.
In this document, we dive deeper into each component.

## How to use this document

- **Authoritative intended architecture**: This file is the single authoritative description of how the system *should* be structured and behave ("as it should be").
- **Decision records as history**: Decision records in `docs/dev/decision-records/` capture the rationale and history that led to this architecture. Do not infer the current architecture from a subset of decision records; always treat this document as the baseline.
- **Code as implementation**: The source code is the authority on how the system *currently* behaves ("as it is"). Where the code and this document disagree, that discrepancy represents design drift to be resolved by code changes, documentation changes, and/or new decision records.

## Agent roles

This repository distinguishes two agent types:

- **Research Agent**: A deployed or runtime agent that is the subject of or participant in research. It is implemented in code, sees tools and supplied system prompts, and may see generated schema of data classes exposed through middleware or MCP. It MUST NOT see repository content such as design docs, AGENTS.md, decision records, or source code.
- **Development Agent**: A code agent (e.g. Cursor, Claude Code) that accesses design documentation, module documentation, and repository content; modifies code and documentation; and develops code to support the Research Agent and documentation to support itself.

These definitions are summarized from and kept consistent with the root [AGENTS.md](../../AGENTS.md) and [DR-003 Research Agent and Development Agent Terminology](decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md), which provide historical context and additional guidance.

## Structural elements and middleware

Structural elements describe OWL 2 and related graph-scoped constructs in a way that can be consumed both by middleware and by Research Agents via JSON-schema-driven tools and state.

- The `rdflib-reasoning-axioms` project defines a Pydantic model hierarchy:
  - `GraphBacked` is the universal base for graph-scoped Pydantic models.
  - `StructuralElement` is the universal base for OWL 2 structural elements and closely related extensions.
- Each instance has a single required `context` (graph identifier). Related structural elements embedded in a field share the same `context`; cross-context relationships are expressed only at the triple/quad level.
- Structural elements expose `as_triples` and `as_quads` methods whose output conforms to the OWL 2 mapping to RDF and related RDF semantics specifications.
- Models avoid embedding heavy graph/session types (such as `rdflib.Graph` or SPARQL result objects) and instead rely on node-level terms and Pydantic-generated JSON Schema as the primary interface.
- The `rdflib-reasoning-middleware` project uses `GraphBacked` and `StructuralElement` models as tool argument/response schemas and as values embedded in middleware state for Research Agents.

### Schema-facing RDF boundary models

Schema-facing RDF boundary models are the Pydantic models and reusable schema aliases exposed by middleware across the runtime boundary to a Research Agent.
These models require stricter guidance than ordinary developer-only helper classes because their generated JSON Schema becomes part of the runtime contract.

- Boundary models MUST optimize for the Research Agent communication surface first. Their serialized form SHOULD be easy to inspect and SHOULD use lexical RDF forms such as N3 strings when those are the natural wire representation.
- Boundary models SHOULD keep RDF-specific validation rules close to the field or reusable type alias so the same constraints and descriptions are reused consistently across tools and state payloads.
- Boundary models SHOULD attach concise semantic descriptions, normative constraints, and a small number of high-fidelity lexical examples directly to the schema-visible field or reusable alias.
- Boundary models MAY cite formal specifications when that helps a Research Agent recover from validation errors, but schema descriptions SHOULD remain operational and brief rather than reproducing extended specification prose.
- Heavy runtime helper objects MAY exist as computed Python-only conveniences, but they MUST NOT be required serialized inputs or outputs across the Research Agent boundary.
- Module-level documentation for schema-facing boundary models SHOULD point Development Agents to the governing architecture section and decision record so local edits remain aligned with repository policy.

These rules are further elaborated in [DR-011 Schema-Facing RDF Boundary Models](decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md).

These rules are aligned with, and further elaborated in, [DR-002 Structural Elements and Middleware Integration](decision-records/DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md).

## Middleware composition and capability gating

Middleware composition is the primary mechanism by which runtime capabilities are exposed to, or withheld from, a Research Agent.
This is an architectural constraint for both correctness and experimental control.

- Experimental conditions MUST be realizable by middleware composition alone. Baseline, retrieval-enabled, and inference-enabled conditions SHOULD differ by inclusion or exclusion of middleware capabilities, not by hidden prompt changes or ad hoc harness behavior.
- Inference capabilities MUST be enabled or disabled by inclusion or exclusion of inference middleware. A Research Agent without inference middleware MUST NOT be able to invoke inference or explanation behavior accidentally through some alternate path.
- Knowledge retrieval capabilities MUST be enabled or disabled by inclusion or exclusion of retrieval middleware. A Research Agent without retrieval middleware MUST NOT be able to access remote entity-resolution or remote import functionality accidentally through some alternate path.
- Knowledge retrieval middleware and inference middleware depend on dataset middleware because they operate on dataset-backed runtime state. If the concrete state shape or dataset-session abstraction changes, that dependency MUST remain explicit at the architectural level.
- Middleware that exposes capabilities to a Research Agent SHOULD do so through explicit tool/state surfaces with clear schemas rather than through hidden side effects.

### Dataset middleware

Dataset middleware is the foundational runtime layer for graph-backed experimentation.

- Dataset middleware is responsible for creating, loading, updating, serializing, and deleting RDF 1.1 graphs and datasets used by the Research Agent.
- Dataset middleware MUST treat the live RDFLib dataset as middleware-owned runtime infrastructure rather than as copied `AgentState` payload.
- Middleware state exposed to LangChain MUST remain `TypedDict`-compatible and cheap to copy. Live RDFLib datasets, stores, locks, and similar heavy runtime objects MUST NOT be stored directly in copied runtime state.
- Dataset middleware SHOULD resolve the active working dataset through a middleware-owned per-dataset session or equivalent internal container.
- Each dataset session MUST own the live `rdflib.Dataset` together with the coordination primitive that protects it.
- Dataset middleware MUST provide multi-reader / single-writer coordination per dataset session so unrelated datasets do not block one another unnecessarily.
- Read-only dataset operations SHOULD execute under read coordination, and mutating dataset operations MUST execute under write coordination.
- Other middleware layers that retrieve knowledge or run inference MUST compose over dataset middleware rather than bypassing it.
- Retrieval and inference middleware that operate on the same dataset MUST use the same dataset-session coordination boundary as dataset tools.
- Dataset middleware MUST NOT claim general transaction semantics for the baseline. Rollback, snapshot isolation, branch-local dataset copies, and conflict-merge semantics are explicitly out of scope unless later architecture extends the contract.
- RDF 1.2 triple-statement or quoted-triple support MAY be considered in the future, but it is not part of the current architectural baseline.

These rules are aligned with [DR-012 Middleware-Owned Dataset Sessions and Coordination](decision-records/DR-012%20Middleware-Owned%20Dataset%20Sessions%20and%20Coordination.md).

#### Dataset middleware capability phases

Dataset middleware capability MUST be introduced in phased slices rather than as a fully general dataset surface from the start.

1. Phase 1: Default-graph baseline
   - The initial public tool surface SHOULD focus on the default graph only.
   - The default Phase 1 tool set SHOULD be limited to listing triples, adding triples, removing triples, serializing current state, and resetting the dataset.
   - `0.1.0` dataset middleware scope MUST be limited to this baseline unless architecture and roadmap are deliberately revised.

2. Phase 2: Named-graph management and graph-scoped triple access
   - A later phase MAY add named graph creation, listing, and removal.
   - That same phase MAY extend triple-oriented tools with an optional graph or context argument while preserving the default graph as the default target.

3. Phase 3: Explicit dataset and quad operations
   - Generic quad-level CRUD and other explicitly dataset-wide manipulation SHOULD remain a later phase.
   - These operations SHOULD be added only when the agent or higher middleware layers have a demonstrated need for cross-graph manipulation that graph-scoped triple tools cannot express cleanly.

This phased structure is intended to preserve a narrow `0.1.0` baseline while keeping later dataset semantics available as explicit future scope.

#### Dataset middleware prompt and tool-description strategy

Dataset middleware SHOULD follow the same broad prompt-layering pattern used by middleware systems such as Deep Agents' built-in middleware, where middleware contributes capability-specific instructions and tool descriptions define the concrete callable surface.

- The middleware-level system prompt SHOULD introduce the capability in task-oriented language first, for example as a "knowledge base", while also identifying the implementation substrate as RDF when operational precision is needed.
- The middleware-level system prompt SHOULD explain when the agent ought to use dataset tools, how those tools fit together, and what high-level modeling constraints or safety expectations apply.
- The middleware-level system prompt SHOULD remain concise and SHOULD NOT duplicate detailed parameter-level guidance already present in tool descriptions or schema fields.
- Tool descriptions SHOULD remain operational and concrete: what the tool does, what scope it acts on, when to use it, and whether it is destructive.
- Schema-visible request and response models SHOULD carry field-level validation, lexical examples, and format guidance rather than pushing all such detail into prompt prose.
- Custom agent prompts or experiment prompts SHOULD complement middleware-added instructions rather than re-describing the middleware tool surface.

This strategy is informed by Deep Agents documentation describing middleware-appended prompts and tool-specific descriptions as complementary layers rather than one monolithic instruction block:

- [Deep Agents customization docs](https://docs.langchain.com/oss/python/deepagents/customization)
- [Deep Agents repository overview](https://github.com/langchain-ai/deepagents)
- [FilesystemMiddleware reference](https://reference.langchain.com/python/deepagents/middleware/filesystem/FilesystemMiddleware)

#### Dataset middleware internal methods and tool adapters

Dataset middleware MUST maintain a clear separation between internal implementation methods and Research Agent-facing tool adapters.

- Internal middleware methods SHOULD implement the core RDFLib-native behavior and SHOULD be the source of truth for dataset operations.
- Tool implementations SHOULD remain thin adapters whenever possible.
- Thin adapters SHOULD validate or transform request payloads, delegate to internal middleware methods, and transform results into response payloads.
- Retrieval middleware, inference middleware, and tests SHOULD prefer composing with internal middleware methods rather than simulating agent tool calls when no schema-boundary behavior is under test.
- Tool adapters MUST NOT duplicate core implementation logic except for minimal glue required by the orchestration framework.

These rules are aligned with [DR-013 Dataset Middleware Internal Method and Tool Adapter Pattern](decision-records/DR-013%20Dataset%20Middleware%20Internal%20Method%20and%20Tool%20Adapter%20Pattern.md).

### Knowledge retrieval middleware

Knowledge retrieval middleware is responsible for importing structured knowledge into dataset-backed state.

- Retrieval middleware MAY support remote RDF retrieval from providers such as DBpedia and, later, Wikidata.
- Retrieval middleware MAY support extraction of structured site metadata such as embedded JSON-LD from HTML pages.
- Retrieval results SHOULD carry provenance sufficient to explain where imported facts originated.
- If entity resolution outputs or provenance artifacts are intended to cross the runtime boundary as schema-driven values visible to the Research Agent, they SHOULD be modeled as `GraphBacked` structures rather than ad hoc dictionaries or transport-specific payloads.
- The entity-resolution pipeline MAY be exposed either as a sequence of tools or as a dedicated subagent with a constrained prompt and structured output. The architectural requirement is that its inputs and outputs remain explicit, inspectable, and controllable for experiments.

### Inference middleware

Inference middleware is responsible for exposing reasoner-backed behavior to the Research Agent.

- Inference middleware MUST compose over dataset middleware so that inference operates on the same dataset-backed state as retrieval and manual graph updates.
- Inference execution, derivation tracing, and proof or explanation generation SHOULD be exposed as explicit runtime capabilities rather than being implicit side effects of unrelated operations.
- If derivations are exposed to the Research Agent, they SHOULD be available through a structured proof representation such as `DirectProof`, so that baseline and tool-enabled conditions can be compared against a common output schema.
- Middleware MAY reconstruct `DirectProof` values from engine-native derivation logs, agent-proposed proof content, or both, but the runtime boundary SHOULD expose a stable proof schema rather than raw engine internals.

### Engine event contract and entrypoint

The reasoning engine (e.g. RETE in `rdflib-reasoning-engine`) is driven by store events via `BatchDispatcher`.
This subsection codifies the contract and flow so that RETEStore and Development Agents have a clear foundation.

- **Store event contract:** Backing stores MUST emit `TripleAddedEvent` (respectively `TripleRemovedEvent`) on every `add()` / `remove()` call, even when the triple is already present or absent, and MUST do so *before* performing the mutation. The batch dispatcher filters duplicate events by determining whether the triple is already in the store for that context; that determination MUST use the store's own graph (or equivalent) for the context identifier, not the context object passed in the event (because `Store.add` passes the caller's context through unchanged, which may not be the store's graph). Only `rdflib.plugins.stores.memory.Memory` has been validated against this contract in this repository.
- **Event flow:** Store (add/remove) → `TripleAddedEvent` / `TripleRemovedEvent` → BatchDispatcher → `TripleAddedBatchEvent` / `TripleRemovedBatchEvent` → inference engine → materialization (derived triples) → fixed-point iteration (handled by BatchDispatcher's loop).
- **Inference entrypoint:** The entrypoint for the inference engine is subscription to `TripleAddedBatchEvent` (and optionally `TripleRemovedBatchEvent`). Batches are per-context; the dispatcher iterates to fixed point. The tests in `rdflib-reasoning-engine/tests/test_batch_dispatcher.py` are the validated specification for this behavior.
- **Supported store integration path:** `RETEStore` is the intended store-facing adapter for the engine package. Development and debugging SHOULD treat `Store` events -> `BatchDispatcher` -> `RETEStore` -> `RETEEngine` as the single supported integration flow.
- **Persistence contract:** On open or attach, `RETEStore` MUST treat the current contents of the backing store as authoritative facts for each context. It MUST seed the engine from the fully materialized contents of that context; it MUST NOT attempt to reconstruct an asserted-versus-derived distinction from persisted RDF alone.
- **Warm-start contract:** Warm-start MUST proceed by creating the engine, reading the existing triples for the context from the backing store, warming the engine from those triples, and materializing any non-silent warmup deductions back into the store.
- **Engine update contract:** `RETEEngine.add_triples()` MUST be idempotent for already-known triples when derivation logging is disabled. `RETEEngine.add_triples()` and `RETEEngine.warmup()` MUST compute a fixed point for their input update set. `BatchDispatcher` provides store-level fixed-point iteration across reentrant materialization; it MUST NOT be relied upon to compensate for a partially saturating engine update step.
- **Current implementation subset:** The current engine implementation MAY remain add-only so long as it preserves stable Fact identity, persistent alpha/beta memory, agenda-ordered execution, derivation logging, callback execution, and JTMS-compatible support bookkeeping for derived facts. This subset is intended to preserve the execution and support shapes required for future retraction without claiming full truth maintenance today.
- **Derivation logging contract:** If derivation logging is enabled, the engine MUST record rule applications in an engine-native structured form centered on grouped triple conclusions, supporting premises, a minimal rule identifier, and the context. Engine-native derivation logs MUST support arbitrary custom rules and MUST NOT require every derivation step to map one-to-one to a named OWL 2 structural axiom.
- **Explanation reconstruction contract:** Explanation reconstruction is distinct from derivation logging. The engine and related packages MAY reconstruct user-facing proof structures such as `DirectProof` from derivation logs, but `DirectProof` is not the engine's primitive execution format. Reconstructed proof steps MAY preserve grouped conclusions from a single rule application rather than fragmenting them into one proof node per output triple.
- **Proof metadata contract:** Engine-native derivation records SHOULD carry minimal rule identity such as a ruleset and rule id, while reconstructed proof steps SHOULD carry richer semantic metadata such as labels, descriptions, and authoritative URI-based references. Research Agent-authored proof steps MAY omit an engine-native rule identifier when only intended semantics are available.
- **Proof data model contract:** Proof and derivation models intended for interchange and evaluation SHOULD be immutable so they can be compared, cached, and reused safely across tooling.

These rules are aligned with [DR-004 RETE Store Persistence and Engine Update Contract](decision-records/DR-004%20RETE%20Store%20Persistence%20and%20Engine%20Update%20Contract.md).

### Contradiction signaling

Contradiction handling is related to, but distinct from, inference execution and explanation behavior.

- Contradiction detection is expected to be flagged by the derivation or observation of a triple of the form `?x rdf:type owl:Nothing`.
- The behavior of the system after contradiction detection (for example `silent`, `warn`, or `error`) MUST be independently configurable from contradiction detection itself.
- Whether the system can explain a contradiction depends independently on derivation logging or proof reconstruction capabilities and MUST NOT be assumed merely because contradiction detection is present.

## Proof evaluation harness

The repository SHOULD provide a reusable proof evaluation harness for baseline and follow-on experiments.
This harness is Development Agent evaluation infrastructure for assessing Research Agent outputs; it is not itself a capability that a Research Agent must see at runtime.

- The proof evaluation harness SHOULD live in `rdflib-reasoning-middleware`, because that package is the integration point between Research Agent-facing schemas, orchestration glue, and the reasoning packages.
- The proof evaluation harness MUST expose framework-agnostic structured inputs and outputs using Pydantic models so that notebooks, scripts, and multiple orchestration frameworks can consume the same contract.
- The proof evaluation harness MAY provide thin framework-specific adapters such as LangChain integration, but those adapters MUST remain secondary to the framework-agnostic data model and evaluation contract.
- The proof evaluation harness SHOULD begin with a single-pass structured assessment flow rather than a full planning agent. A multi-step Research Agent evaluator MAY be added later if experiments justify it.
- The proof evaluation harness SHOULD treat `DirectProof` as the common proof interchange format for baseline experiments, regardless of whether a proof originated from a Research Agent, a reconstructed engine derivation, or a hybrid of both.

### Proof evaluation harness inputs and outputs

The initial proof evaluation harness is intended to support a baseline notebook without requiring full axiomatization or a complete reasoning profile.

- Inputs SHOULD include an input document, a proposed `DirectProof`, and any task metadata needed to interpret the assessment.
- Outputs SHOULD include a typed assessment object whose fields can be consumed by notebooks and later batch experiments.
- The output schema SHOULD support both coarse verdicts and fine-grained error categories so that observed Research Agent mistakes can guide future feature prioritization.
- `DirectProof` SHOULD support proof payloads represented as graph-scoped Pydantic objects where that yields a natural typed claim or support, but it MUST also support triple-level claims directly because not every derivation step is most naturally represented as an OWL structural element.
- `DirectProof` SHOULD support proof steps whose conclusions are grouped when a single inference step naturally establishes multiple related outputs.

### Proof rendering

Proof rendering is distinct from proof reconstruction and proof interchange.

- Canonical proof structures such as `DirectProof` MUST remain machine-facing data models and MUST NOT be simplified in-place for presentation convenience.
- Rendering SHOULD be implemented as a separate presentation layer over canonical proof data.
- Rendering APIs MAY accept an RDFLib namespace source such as a `NamespaceManager`, graph, or dataset-derived equivalent in order to present compact names like `rdf:type` or `rdfs:subClassOf`.
- Namespace-aware shortening MUST be treated as presentation only. It MUST NOT replace the canonical RDFLib term content stored in the proof models.
- When no namespace source is available, renderers SHOULD fall back to a deterministic readable form rather than failing.
- Proof rendering MUST NOT be implemented by changing `__repr__` on proof models to use namespace-aware shortening. Debug-oriented representation and human-facing rendering SHOULD remain separate concerns.
- Notebook-friendly rendering is a desired future capability. Markdown-oriented rendering is RECOMMENDED as an initial target, and Mermaid-style structural rendering MAY be added later.

### Baseline scope

The baseline notebook SHOULD establish a narrow and defensible experiment.
It SHOULD avoid treating the first experiment as a complete test of all intended reasoning capabilities.

- The baseline SHOULD focus on whether a proposed `DirectProof` is acceptably grounded and structurally correct relative to the input document.
- The baseline SHOULD use the proof evaluation harness to produce structured assessments that can be analyzed after the fact.
- The baseline notebook SHOULD report conclusions based on actual harness outputs rather than attempting to pre-enumerate every current or future failure mode in its introduction.

### Initial proof evaluation dimensions

The proof evaluation harness feature matrix for the baseline SHOULD remain minimal.
Initial dimensions SHOULD be limited to those needed to run the first experiment and analyze common Research Agent errors.

- Groundedness of extracted entities and relationships
- Hallucinated entities or relationships
- Missing support required by the proposed proof
- Verdict on whether the proposed proof is acceptable for the baseline task
- Optional rationale and typed error labels

The following concerns are explicitly out of the initial baseline scope and SHOULD be added only when motivated by observed failures or a new experiment design:

- Complete set of proofs when multiple proofs exist
- Full contradiction detection and contradiction explanation
- Open World assumption handling for negative assertions
- Exhaustive completeness over all extractable entities and relations

## RETE Engine Design

### Overview

The engine MUST implement a forward-chaining **RETE-style** architecture with RETE-OO-inspired internals, specifically optimized for **OWL 2 RL** and **RDFS** entailment.
The design diverges from classic RETE by treating RDF triples as first-class objects and allowing Python extensibility, but the logical core MUST remain a pure RDF entailment engine.

- **Logical consequents** MUST be represented as declarative triple production handled by the engine itself.
- **Predicates / builtins** MAY use Python functions, but they MUST be read-only tests used during matching or internal evaluation.
- **Callbacks / hooks** MAY use Python functions for observability or integration, but they MUST NOT add triples, retract triples, or otherwise mutate graph state.
- **RDF data-model enforcement** MUST remain part of engine correctness, not just caller-side validation. The engine MUST refuse to admit or materialize triples that violate the RDF 1.1 triple constraints, especially literal subjects and non-IRI predicates.

### Rule Matching & Network Topology

The engine SHOULD employ a **Left-Deep** join tree by default but MUST support **Structural Node Sharing** through a canonicalizing `NodeRegistry`.

- **Alpha Layer**: MUST support literal constraints (e.g., `Triple p == "rdf:type"`) and `PredicateNodes`. `PredicateNodes` SHOULD wrap duck-typed Python callables. To minimize interpreter overhead, the `NetworkBuilder` SHOULD position `PredicateNodes` after literal `AlphaNodes` but before `BetaNodes`.
- **Beta Layer**: MUST maintain memories of `PartialMatch` objects. The `JoinOptimizer` SHOULD use basic selectivity heuristics (e.g., specific properties are more selective than `rdf:type`) to order joins.
- **Terminal Layer**: Upon a full match, the engine MUST produce an engine-managed logical production and MAY additionally enqueue non-mutating callbacks.
- **Specialized relation indexes**: The architecture MAY later incorporate specialized relation indexes for selected reachability-oriented relations when that is more efficient than routing the same work exclusively through generic rule matching. Current intent is limited to schema-lattice relations such as `rdfs:subClassOf` and `rdfs:subPropertyOf`; concrete algorithms and integration boundaries remain future design work.

### Truth Maintenance System (TMS)

The engine MUST provide a **Justification-based Truth Maintenance System (JTMS)** to manage the deductive closure of the RDF graph.

- **Current implementation subset:** The add-only implementation MAY stop at recording support-compatible `Fact`, `PartialMatch`, and `Justification` data so long as later recursive retraction is not precluded. This means support sets MAY be recorded before removal semantics are implemented, provided the recorded support objects are the ones future truth maintenance will use rather than disposable scaffolding.
- **Multi-Parent Support**: The `TMSController` MUST support multiple justifications for a single Fact. A Fact is considered logically supported if it has at least one valid `Justification` or is flagged as "Stated" (User-inserted).
- **Dependency Tracking**: Every `Justification` MUST capture a `PartialMatch` (as a tuple of FactIDs) to enable full **Derivation Tree** traversal. This is REQUIRED for both recursive retraction and generating human-readable explanations (e.g., Graphviz).
- **Recursive Retraction**: When a `Fact` is retracted, the `TMSController` MUST perform a **Mark-Verify-Sweep** operation. It MUST only retract downstream consequences if their `Justification` set becomes empty.
- **Support invariants**: A stated Fact MUST remain supported regardless of whether it also has zero, one, or many `Justification` records. A derived Fact MUST remain present if and only if it has at least one valid `Justification`.
- **Removal propagation contract**: Low-level remove event forwarding MAY mirror add forwarding through `BatchDispatcher`, `RETEStore`, and `RETEEngine`, but logical removal MUST be governed by support validity rather than event arrival alone. A remove event MAY invalidate one support path without implying that the corresponding derived Fact is no longer present.
- **Staged implementation plan**: The intended Development Agent sequence is: (1) record support objects at production time for newly derived and already-known conclusions; (2) expose support verification APIs that can answer whether a Fact remains supported after one support path is invalidated; (3) implement recursive **Mark-Verify-Sweep** over the dependency graph; and only then (4) wire full triple removal through `RETEEngine`, `RETEStore`, and `BatchDispatcher`.

### Execution & Side Effects

Rule execution MUST be decoupled from matching via an `Agenda`.

- **Conflict Resolution**: The `Agenda` SHOULD prioritize execution based on **Salience** (user-defined) and **Inference Depth** (Breadth-First). Breadth-First execution is RECOMMENDED to ensure shorter derivation paths are found before complex property chains.
- **Logical Production Path**: Logical triple production MUST occur only through engine-managed rule heads. Python callbacks MUST NOT be an alternate inference channel or graph-mutation path.
- **Callbacks**: Callbacks MUST interact with the engine only through a read-only `RuleContext` or equivalent hook context. They MAY emit logs, metrics, traces, or other external signals, but they MUST NOT modify graph state.
- **Retraction Compatibility**: Because callbacks are non-logical and non-mutating, `RetractionNotImplemented` MUST be interpreted as meaning that no reversal is required for logical consistency. Retraction support remains a future design goal; the initial implementation MAY remain add-only so long as its data structures and rule model do not preclude JTMS-backed removal later.

### RDF Data-Model Enforcement

The engine MUST enforce RDF 1.1 triple well-formedness for both stated inputs and inferred outputs.

- **Literal subjects**: The engine MUST NOT admit or materialize triples whose subject is a literal.
- **Predicate term constraints**: The engine MUST NOT admit or materialize triples whose predicate is not an IRI. Blank node predicates and literal predicates are explicitly disallowed.
- **Working-memory boundary**: Malformed triples MUST be filtered out before they enter working memory, support bookkeeping, or derivation outputs.
- **Policy surface**: The engine SHOULD expose configurable handling for malformed triples so that callers can choose fail-fast behavior or warning-and-skip behavior for experimental or migration scenarios.
- **Feature distinction**: This enforcement SHOULD be documented as a distinguishing engine feature because many RDF-oriented rule systems are more permissive about tuple-shaped inputs than this repository intends to be.

### Type Safety and Validation

The engine SHOULD utilize Python's `inspect` and `typing` modules at **Construction-Time** to validate rule signatures.

- Callback functions MUST accept `RuleContext` as the first argument.
- Subsequent callback arguments SHOULD be type-hinted as `Node` or `Fact` to facilitate "duck-typing" in the RETE network.

### Rationale

This hybrid approach balances the formal logic requirements of **OWL 2 RL** with the pragmatic need for procedural Python hooks. By separating declarative triple production from read-only predicates and non-mutating callbacks, the engine preserves deterministic fixed-point materialization while still supporting instrumentation and internal extensibility. By embedding the `PartialMatch` in the `Justification`, we ensure the engine is "Self-Explaining," while the `NodeRegistry` prevents the memory explosion typically associated with unoptimized RETE implementations.

These rules are aligned with [DR-005 RETE Consequent Partitioning and Retraction Compatibility](decision-records/DR-005%20RETE%20Consequent%20Partitioning%20and%20Retraction%20Compatibility.md).
Proof reconstruction and `DirectProof` layering are further aligned with [DR-007 Proof Model and Derivation Semantics Refinement](decision-records/DR-007%20Proof%20Model%20and%20Derivation%20Semantics%20Refinement.md), which supersedes [DR-006 Derivation Logging and DirectProof Reconstruction](decision-records/DR-006%20Derivation%20Logging%20and%20DirectProof%20Reconstruction.md).
Proof rendering and namespace-aware presentation are further aligned with [DR-008 Proof Rendering Separation and Namespace-Aware Presentation](decision-records/DR-008%20Proof%20Rendering%20Separation%20and%20Namespace-Aware%20Presentation.md).
Future specialized transitive handling intent is aligned with [DR-009 Transitive Relation Index Intent](decision-records/DR-009%20Transitive%20Relation%20Index%20Intent.md).
RDF triple well-formedness enforcement is aligned with [DR-010 RDF Triple Well-Formedness Enforcement](decision-records/DR-010%20RDF%20Triple%20Well-Formedness%20Enforcement.md).
