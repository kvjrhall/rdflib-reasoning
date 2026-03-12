# RDFLib Reasoning Middleware

This package exposes this repository's functionality to DeepAgents (runtime/Research Agents) as [Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom).

- `GraphBacked` and `StructuralElement` instances (from `rdflib-reasoning-axioms`) MUST be usable as tool argument/response models and as values carried inside middleware state. They are stateless, immutable domain snapshots.
- `GraphBacked` and `StructuralElement` MUST NOT subclass LangGraph `AgentState`. Middleware MAY map them into `AgentState` fields (e.g. as payloads or lists of axioms).

## Proof Evaluation Harness

This package is also the intended home for a reusable proof evaluation harness used by Development Agents to assess `DirectProof` outputs produced in experiments.

- The harness SHOULD expose framework-agnostic Pydantic models for evaluation requests and responses.
- The harness SHOULD support a prompt and structured-output contract that can be used without committing to a specific orchestration framework.
- The harness MAY include thin LangChain or LangGraph glue code, but a full evaluator agent is not required for the baseline.
- The baseline notebook SHOULD consume the harness; it SHOULD NOT define the evaluation contract inline.

### Initial proof evaluation dimensions

The initial harness is intentionally narrow.
It is meant to support the baseline proof notebook before full axiomatization or a complete reasoning profile exists.

| Dimension | Purpose |
| --- | --- |
| Groundedness | Check whether proof elements are supported by the input document |
| Hallucination detection | Flag entities or relationships not grounded in the input document |
| Missing support | Identify support the proposed proof appears to require but does not provide |
| Baseline verdict | Decide whether the proposed proof is acceptable for the baseline task |
| Optional rationale | Preserve a short explanation or typed error labels for later analysis |

## Feature Matrix

Status values:

- `Implemented`: available in the package today
- `Not started`: identified feature target with no concrete implementation yet
- `Out of scope`: intentionally not roadmapped for the current implementation phase

### Dataset middleware

| Feature | Status | Notes |
| --- | --- | --- |
| Graph CRUD | Not started | Create, load, save, replace, and delete a single RDF 1.1 graph |
| Graph serialization | Not started | Render graph state as Turtle, N-Triples, or N3 for inspection |
| Graph triple access | Not started | List, query, add, and remove triples within a graph |
| Dataset CRUD | Not started | Create, load, save, and delete RDF 1.1 datasets |
| Named graph management | Not started | List graphs, create named graphs, and remove named graphs |
| Dataset quad access | Not started | List, query, add, and remove quads across graphs |
| RDF 1.2 triple statement support | Out of scope | Forward-looking placeholder for RDF 1.2 quoted or triple-term support |

### Knowledge retrieval middleware

| Feature | Status | Notes |
| --- | --- | --- |
| Remote entity search | Not started | Resolve labels or names to candidate external entities; initial provider target is DBpedia, with Wikidata open for later |
| Remote entity describe | Not started | Fetch RDF descriptions for resolved entities from remote providers |
| External RDF import | Not started | Fetch RDF over HTTP and normalize it into local graph or dataset state |
| Entity resolution pipeline | Not started | Search, disambiguate, fetch, and attach provenance for external entities |
| Site metadata extraction | Not started | Fetch HTML and extract embedded JSON-LD or related structured metadata for import |

### Inference middleware

| Feature | Status | Notes |
| --- | --- | --- |
| Reasoner-backed dataset interface | Not started | Middleware surface for datasets backed by an inference engine |
| Inference execution | Not started | Trigger rule materialization against current dataset state |
| Direct proof generation | Not started | Return a `DirectProof` for a supplied claim, structural element, or contradiction |
| Derivation trace access | Not started | Expose rule-level derivation traces produced by the engine |
| Proof rendering | Not started | Render canonical proof objects into notebook-friendly or other human-facing views without changing the underlying proof data |
| Consistency / contradiction checks | Not started | Detect and report contradictions or unsatisfiable states |

### Concrete middleware profiles

| Feature | Status | Notes |
| --- | --- | --- |
| RDFS middleware profile | Not started | Reasoner-backed dataset middleware configured for RDFS entailment |
| OWL 2 RL middleware profile | Not started | Reasoner-backed dataset middleware configured for OWL 2 RL entailment |
