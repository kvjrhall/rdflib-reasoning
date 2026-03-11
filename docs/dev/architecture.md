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

These rules are aligned with, and further elaborated in, [DR-002 Structural Elements and Middleware Integration](decision-records/DR-002%20Structural%20Elements%20and%20Middleware%20Integration.md).

## Middleware composition and capability gating

Middleware composition is the primary mechanism by which runtime capabilities are exposed to, or withheld from, a Research Agent.
This is an architectural constraint for both correctness and experimental control.

- Experimental conditions MUST be realizable by middleware composition alone. Baseline, retrieval-enabled, and inference-enabled conditions SHOULD differ by inclusion or exclusion of middleware capabilities, not by hidden prompt changes or ad hoc harness behavior.
- Inference capabilities MUST be enabled or disabled by inclusion or exclusion of inference middleware. A Research Agent without inference middleware MUST NOT be able to invoke inference or explanation behavior accidentally through some alternate path.
- Knowledge retrieval capabilities MUST be enabled or disabled by inclusion or exclusion of retrieval middleware. A Research Agent without retrieval middleware MUST NOT be able to access remote entity-resolution or remote import functionality accidentally through some alternate path.
- Knowledge retrieval middleware and inference middleware depend on dataset middleware because they operate on dataset-backed runtime state. If `DatasetState` is replaced by a successor abstraction, that dependency MUST remain explicit at the architectural level.
- Middleware that exposes capabilities to a Research Agent SHOULD do so through explicit tool/state surfaces with clear schemas rather than through hidden side effects.

### Dataset middleware

Dataset middleware is the foundational runtime layer for graph-backed experimentation.

- Dataset middleware is responsible for creating, loading, updating, serializing, and deleting RDF 1.1 graphs and datasets used by the Research Agent.
- Other middleware layers that retrieve knowledge or run inference MUST compose over dataset middleware rather than bypassing it.
- RDF 1.2 triple-statement or quoted-triple support MAY be considered in the future, but it is not part of the current architectural baseline.

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

### Engine event contract and entrypoint

The reasoning engine (e.g. RETE in `rdflib-reasoning-engine`) is driven by store events via `BatchDispatcher`.
This subsection codifies the contract and flow so that RETEStore and Development Agents have a clear foundation.

- **Store event contract:** Backing stores MUST emit `TripleAddedEvent` (respectively `TripleRemovedEvent`) on every `add()` / `remove()` call, even when the triple is already present or absent, and MUST do so *before* performing the mutation. The batch dispatcher filters duplicate events by determining whether the triple is already in the store for that context; that determination MUST use the store's own graph (or equivalent) for the context identifier, not the context object passed in the event (because `Store.add` passes the caller's context through unchanged, which may not be the store's graph). Only `rdflib.plugins.stores.memory.Memory` has been validated against this contract in this repository.
- **Event flow:** Store (add/remove) → `TripleAddedEvent` / `TripleRemovedEvent` → BatchDispatcher → `TripleAddedBatchEvent` / `TripleRemovedBatchEvent` → inference engine → materialization (derived triples) → fixed-point iteration (handled by BatchDispatcher's loop).
- **Inference entrypoint:** The entrypoint for the inference engine is subscription to `TripleAddedBatchEvent` (and optionally `TripleRemovedBatchEvent`). Batches are per-context; the dispatcher iterates to fixed point. The tests in `rdflib-reasoning-engine/tests/test_batch_dispatcher.py` are the validated specification for this behavior.
- **Persistence contract:** On open or attach, `RETEStore` MUST treat the current contents of the backing store as authoritative facts for each context. It MUST seed the engine from the fully materialized contents of that context; it MUST NOT attempt to reconstruct an asserted-versus-derived distinction from persisted RDF alone.
- **Warm-start contract:** Warm-start MUST proceed by creating the engine, reading the existing triples for the context from the backing store, warming the engine from those triples, and materializing any non-silent warmup deductions back into the store.
- **Engine update contract:** `RETEEngine.add_triples()` MUST be idempotent for already-known triples when derivation logging is disabled. `RETEEngine.add_triples()` and `RETEEngine.warmup()` MUST compute a fixed point for their input update set. `BatchDispatcher` provides store-level fixed-point iteration across reentrant materialization; it MUST NOT be relied upon to compensate for a partially saturating engine update step.

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

### Proof evaluation harness inputs and outputs

The initial proof evaluation harness is intended to support a baseline notebook without requiring full axiomatization or a complete reasoning profile.

- Inputs SHOULD include an input document, a proposed `DirectProof`, and any task metadata needed to interpret the assessment.
- Outputs SHOULD include a typed assessment object whose fields can be consumed by notebooks and later batch experiments.
- The output schema SHOULD support both coarse verdicts and fine-grained error categories so that observed Research Agent mistakes can guide future feature prioritization.

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

## Analysis Notebooks
