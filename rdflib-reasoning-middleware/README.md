# RDFLib Reasoning Middleware

This package exposes this repository's functionality to DeepAgents (runtime/Research Agents) as [Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom).

- `GraphBacked` and `StructuralElement` instances (from `rdflib-reasoning-axioms`) MUST be usable as tool argument/response models and as values carried inside middleware state. They are stateless, immutable domain snapshots.
- `GraphBacked` and `StructuralElement` MUST NOT subclass LangGraph `AgentState`. Middleware MAY map them into `AgentState` fields (e.g. as payloads or lists of axioms).

## Demo notebook

The package includes a checked-in demonstration notebook:

- [demo-dataset-middleware.ipynb](../notebooks/demo-dataset-middleware.ipynb): end-to-end walkthrough of `DatasetMiddleware` plus live notebook tracing of agent activity

## DatasetMiddleware tutorial

`DatasetMiddleware` is the baseline middleware layer for giving a Research Agent an RDF-backed working memory.

Current baseline capabilities:

- list triples in the default graph
- add triples to the default graph
- remove triples from the default graph
- serialize the default graph as RDF text
- reset the in-memory dataset session

Minimal usage:

```python
from deepagents import create_deep_agent
from rdflib_reasoning.middleware import DatasetMiddleware

agent = create_deep_agent(
    model=llm,
    middleware=[DatasetMiddleware()],
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Represent this text as RDF."}]}
)
```

The middleware contributes both tool implementations and capability-specific system guidance. The Research Agent sees a tool surface such as `add_triples` and `serialize_dataset`, while the live RDFLib dataset remains middleware-owned runtime infrastructure.

## Tracing tutorial

The tracing support is split into a core callback-based recorder and an optional notebook renderer.

- Core tracing lives in `rdflib_reasoning.middleware.tracing` and does not require `IPython`
- Notebook rendering lives in `rdflib_reasoning.middleware.tracing_notebook` and is optional via the `notebook` extra

Notebook example:

```python
from deepagents import create_deep_agent
from rdflib_reasoning.middleware import DatasetMiddleware
from rdflib_reasoning.middleware.tracing_notebook import LiveNotebookTrace

with LiveNotebookTrace(heading="Dataset Trace") as trace:
    agent = trace.attach(
        create_deep_agent(
            model=llm,
            middleware=[DatasetMiddleware()],
        )
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Represent this text as RDF."}]}
    )
```

The notebook renderer is intended for tutorial and demo scenarios. It presents model decisions, tool calls, tool results, and final responses as a live-updating notebook view without making `IPython` a required runtime dependency for the package.

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
| Default-graph triple access | Implemented | `0.1.0` baseline: list, add, and remove triples in the default graph |
| Default-graph serialization | Implemented | `0.1.0` baseline: serialize current state as RDF text for inspection |
| Dataset reset | Implemented | `0.1.0` baseline escape hatch for clearing the middleware-owned dataset session |
| Named graph management | Not started | Later phase: list graphs, create named graphs, and remove named graphs |
| Graph-scoped triple access | Not started | Later phase: extend triple tools with an optional graph/context argument while keeping the default graph as the default target |
| Dataset quad access | Not started | Later phase: explicit quad-level CRUD across graphs |
| Fully general dataset lifecycle | Not started | Later phase: broader create/load/save/delete and other dataset-wide concerns beyond the initial in-memory baseline |
| RDF 1.2 triple statement support | Out of scope | Forward-looking placeholder for RDF 1.2 quoted or triple-term support |

### Tracing and presentation

| Feature | Status | Notes |
| --- | --- | --- |
| Trace recording callbacks | Implemented | Normalized capture of model and tool lifecycle events for LangChain-based runs |
| Notebook-rendered tracing of agent activity | Implemented | Optional `IPython`-backed live rendering of model decisions, tool calls, tool results, and final responses |
| Non-notebook rich trace renderers | Not started | Future console, HTML, or serialized trace views over the same core trace sink |

### Dataset middleware implementation pattern

- Core dataset behavior SHOULD be implemented in internal middleware methods using RDFLib-native values.
- Research Agent-facing tools SHOULD remain thin adapters over those internal methods.
- Tool descriptions and schema models together form the runtime boundary contract; they SHOULD stay distinct from the middleware's internal implementation API.

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
