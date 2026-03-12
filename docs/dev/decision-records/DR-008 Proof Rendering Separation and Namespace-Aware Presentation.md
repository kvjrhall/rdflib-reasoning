# Proof Rendering Separation and Namespace-Aware Presentation

## Status

Accepted

## Context

The repository now has concrete proof data models such as `DirectProof`, `RuleApplication`, and `TripleFact`, plus an initial explanation reconstruction path from engine-native derivation logs.
Those data models are intended to serve as stable machine-facing interchange structures for Development Agents, middleware, notebooks, and future runtime interfaces.

As proof reconstruction becomes more useful in notebooks and demonstrations, the need for rendering becomes more immediate.
Human readers generally benefit from concise, namespace-aware formatting such as `rdf:type` or `rdfs:subClassOf` rather than full `URIRef(...)`-style detail.
At the same time, proof objects need to retain exact RDFLib terms so that they remain faithful, comparable, serializable, and suitable for downstream tooling.

The implementation discussion also surfaced an important presentation concern: namespace-aware shortening is context-sensitive.
Different graphs or namespace bindings may render the same proof with different compact names, and that display form SHOULD therefore be treated as presentation rather than canonical data.

## Decision

- Proof data models such as `DirectProof`, `RuleApplication`, `DerivationRecord`, and their payloads MUST remain machine-facing canonical structures and MUST NOT be mutated or simplified for presentation convenience.
- Proof rendering MUST be treated as a separate presentation layer over canonical proof data.
- Namespace-aware shortening MAY be used for presentation, but only as an explicitly presentation-oriented transformation. It MUST NOT redefine the canonical meaning or serialization of proof data.
- Proof rendering APIs SHOULD accept an optional namespace source such as an RDFLib `NamespaceManager`, graph, or dataset-derived equivalent so that notebook and middleware outputs can render compact names when available.
- When no namespace source is provided, proof rendering MUST fall back to a deterministic readable form that preserves the underlying RDF term identity as clearly as possible.
- Namespace-aware rendering MUST NOT be implemented by overloading `__repr__` for proof models or RDF term wrappers. `__repr__` SHOULD remain debugging-oriented and faithful to the underlying objects.
- Notebook-friendly proof rendering is a desired future capability. Markdown-oriented rendering is RECOMMENDED as an initial human-facing target, and Mermaid-oriented rendering MAY be added for structural proof visualization.
- Rendered proof output MUST be treated as a view. It MUST NOT be the repository's authoritative interchange format for proofs.

## Consequences

- Canonical proof objects remain stable for evaluation, caching, serialization, and Development Agent tooling.
- Notebook and middleware consumers can later gain more readable outputs without forcing presentation concerns into the proof data model itself.
- Namespace-aware shortening can improve usability while remaining safely optional and reversible at the data-model layer.
- The repository now has a clear place to evolve proof rendering later, including markdown-friendly summaries and graph-style visualizations, without conflating those outputs with proof reconstruction or engine execution.
