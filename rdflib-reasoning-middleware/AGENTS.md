# Middleware Guidance

The `rdflib-reasoning-middleware` package exposes RDF dataset, vocabulary, tracing, continuation-control, and future inference capabilities through middleware surfaces that may cross the runtime boundary to a Research Agent.
Development Agents maintain this package and its Development Agent-facing documentation; they are not runtime callers of this package.

## Documentation and runtime visibility

- Research Agents may see package-exposed middleware prompts, tool descriptions, generated schemas, serialized responses, validation errors, and selected state fields.
- Research Agents MUST NOT see repository-local specs, `AGENTS.md`, design docs, source comments, or other Development Agent-only material.
- Public docstrings, module docstrings, `Field` descriptions, tool descriptions, middleware prompt text, and generated schema text are package-consumer or runtime-facing surfaces. They MUST NOT cite repository-local specs, crosswalks, `AGENTS.md`, design docs, or source comments.
- Non-rendered source comments that cannot become generated documentation MAY cite repository-local specs or design docs for Development Agents.
- Runtime-visible text SHOULD stand alone and SHOULD prefer official specification names, public API names, concrete tool behavior, explicit constraints, and compact lexical examples.

## Authoritative references

- Treat [`docs/dev/architecture.md`](../docs/dev/architecture.md) as the
  authoritative architecture, especially:
  - `Structural elements and middleware`
  - `Schema-facing RDF boundary models`
  - `Middleware composition and capability gating`
  - `Middleware stack layering and hook-role boundaries`
  - `Dataset middleware`
  - `Dataset middleware internal methods and tool adapters`
  - `Shared middleware services`
  - `RDF vocabulary middleware`
  - `Continuation guard middleware`
  - `Inference middleware`
  - `Proof evaluation harness`
  - `Proof rendering`
- Treat [`docs/dev/roadmap.md`](../docs/dev/roadmap.md) as the authoritative release and priority plan for substantial middleware work.
- Treat [`docs/dev/decision-records/DR-003 Research Agent and Development Agent Terminology.md`](../docs/dev/decision-records/DR-003%20Research%20Agent%20and%20Development%20Agent%20Terminology.md) as the authoritative rule set for role terminology and visibility boundaries.
- Treat [`docs/dev/decision-records/DR-011 Schema-Facing RDF Boundary Models.md`](../docs/dev/decision-records/DR-011%20Schema-Facing%20RDF%20Boundary%20Models.md) as the authoritative rule set for schema-facing RDF boundary models.
- Treat [`docs/dev/decision-records/DR-012 Middleware-Owned Dataset Sessions and Coordination.md`](../docs/dev/decision-records/DR-012%20Middleware-Owned%20Dataset%20Sessions%20and%20Coordination.md) and [`docs/dev/decision-records/DR-013 Dataset Middleware Internal Method and Tool Adapter Pattern.md`](../docs/dev/decision-records/DR-013%20Dataset%20Middleware%20Internal%20Method%20and%20Tool%20Adapter%20Pattern.md) as the local authority for dataset runtime ownership and tool adapters.
- Treat [`docs/dev/decision-records/DR-014 Namespace Whitelisting for Dataset Middleware.md`](../docs/dev/decision-records/DR-014%20Namespace%20Whitelisting%20for%20Dataset%20Middleware.md), [`docs/dev/decision-records/DR-017 Search-First RDF Vocabulary Retrieval.md`](../docs/dev/decision-records/DR-017%20Search-First%20RDF%20Vocabulary%20Retrieval.md), and [`docs/dev/decision-records/DR-019 Shared Middleware Services and Unified Vocabulary Configuration.md`](../docs/dev/decision-records/DR-019%20Shared%20Middleware%20Services%20and%20Unified%20Vocabulary%20Configuration.md) as the local authority for vocabulary configuration, whitelist behavior, and shared middleware services.
- Treat [`docs/dev/decision-records/DR-015 Correlated Turn Tracing over Raw Callback Events.md`](../docs/dev/decision-records/DR-015%20Correlated%20Turn%20Tracing%20over%20Raw%20Callback%20Events.md), [`docs/dev/decision-records/DR-018 State-Machine Continuation Control for Single-Run Harnesses.md`](../docs/dev/decision-records/DR-018%20State-Machine%20Continuation%20Control%20for%20Single-Run%20Harnesses.md), and [`docs/dev/decision-records/DR-020 Middleware Stack Layering and Hook-Role Boundaries.md`](../docs/dev/decision-records/DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md) as the local authority for tracing, continuation control, middleware layering, hook roles, and provider-bound repair.

## Development-Agent-only lookup

- Use [`docs/specs/rdf11-concepts-syntax/optimized.html`](../docs/specs/rdf11-concepts-syntax/optimized.html) for RDF term syntax, triples, IRIs, literals, and blank nodes.
- Use [`docs/specs/rdf11-datasets/optimized.html`](../docs/specs/rdf11-datasets/optimized.html) for named graph, dataset, and quad semantics.
- Use [`docs/specs/rdf11-schema/optimized.html`](../docs/specs/rdf11-schema/optimized.html) for RDFS vocabulary meaning.
- Use [`docs/specs/owl2-mapping-to-rdf/INDEX.md`](../docs/specs/owl2-mapping-to-rdf/INDEX.md) when `GraphBacked` or `StructuralElement` payloads cross middleware boundaries and exact OWL structural-element RDF mapping matters.
- Use [LangChain custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) for `AgentMiddleware` hook semantics.
- Use [LangChain tools](https://docs.langchain.com/oss/python/langchain/tools) for tool schemas, tool descriptions, and `Command`-returning tools.
- Use [LangGraph graph/message state](https://docs.langchain.com/oss/python/langgraph/graph-api) for message-state and reducer behavior.
- Use [DeepAgents `create_deep_agent` reference](https://reference.langchain.com/python/deepagents/graph/create_deep_agent) for DeepAgents integration points.
- These references guide Development Agents only. Do not surface them in Research Agent-visible prompts, tool descriptions, schemas, docstrings, or serialized responses.

## Middleware and tool cookbook

- Keep live RDFLib datasets in `DatasetRuntime` and session services, not copied into `AgentState`.
- Implement core RDFLib behavior in internal middleware methods; expose Research Agent-facing tools as thin adapters over those methods.
- Compose dataset, vocabulary, inference, tracing, and continuation capabilities explicitly by middleware inclusion and shared service injection.
- Keep middleware prompts concise. Put concrete parameter-level guidance in tool descriptions and schema fields.
- Use `wrap_model_call` for provider-bound request repair, prompt adaptation, and model-call control that must happen immediately before the provider call.
- Use `wrap_tool_call` for tool-call guarding, retry controls, and middleware misuse checks around a specific tool call.
- Use `after_model` for post-response nudges that can safely be represented as state updates after a model response.
- Keep provider-specific adaptation separate from capability middleware unless the architecture explicitly allows a combined layer.

## Schema and prompt guidance

- Serialized boundary models SHOULD prefer lexical RDF wire forms such as N3 strings.
- Heavy Python helper objects such as `rdflib.Graph`, live datasets, stores, and locks MUST NOT be required serialized inputs or outputs across the Research Agent boundary.
- Public docstrings SHOULD describe package-consumer behavior using official specification names and local public API names only.
- Tool descriptions and middleware prompt text SHOULD be operational, concise, and Research Agent-facing: what the capability does, when to use it, whether it mutates state, and what to do after validation or policy feedback.
- Schema-facing models SHOULD use explicit constraints and high-fidelity examples when they materially reduce misuse.

## Testing expectations

- Boundary-facing models SHOULD have focused Python round-trip tests using `model_dump` and `model_validate` when behavior changes.
- Boundary-facing models SHOULD have JSON round-trip tests using `model_dump_json` and `model_validate_json` when JSON behavior matters.
- Boundary-facing models SHOULD have `model_json_schema()` smoke tests.
- Tool surfaces SHOULD have input schema checks when the tool's public schema is intended to match a request model.
- Prompt, tool-description, and validation-error text SHOULD have targeted assertions when exact Research Agent-facing guidance is part of the behavior.
- Hook changes SHOULD have focused tests for state update shape, message transcript validity, and provider-safe repair behavior.
- Tests SHOULD NOT over-specify incidental Pydantic schema layout unless that layout is deliberately part of the runtime boundary contract.
