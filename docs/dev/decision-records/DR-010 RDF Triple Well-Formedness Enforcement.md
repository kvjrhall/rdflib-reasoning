# RDF Triple Well-Formedness Enforcement

## Status

Accepted

## Context

The RETE engine is intended to materialize RDFS and OWL 2 RL consequences over RDF graphs.
Many RDF-oriented rule engines treat triples as permissive tuple-shaped values and may continue propagating or materializing triples even when those triples violate the RDF 1.1 data model, especially for literal subjects or non-IRI predicates.

This repository needs an explicit design choice for how the engine handles such cases.
The choice matters for correctness, interoperability expectations, and test design because malformed triples can otherwise enter working memory, derivation logging, proof reconstruction inputs, or store materialization paths.

The repository also wants this behavior to be configurable enough for experiments and migration: some callers may prefer immediate failure, while others may prefer a warning and skipping the malformed triple.

## Decision

- The RETE engine MUST enforce RDF 1.1 triple well-formedness for triples it accepts or materializes.
- A triple with a literal subject MUST NOT be admitted to engine working memory, persisted as a derived triple, or exposed as a derived conclusion.
- A triple with a non-IRI predicate MUST NOT be admitted to engine working memory, persisted as a derived triple, or exposed as a derived conclusion.
- The engine MUST support configurable handling for these violations:
  - `literal_subject_policy`: `"error"` or `"warning"`
  - `predicate_term_policy`: `"error"` or `"warning"`
- In `"error"` mode, the engine MUST raise a dedicated public exception type.
- In `"warning"` mode, the engine MUST emit a dedicated public warning type and skip the malformed triple rather than materializing it.
- This enforcement applies both to triples supplied to the engine as stated input and to triples instantiated from rule heads during inference.
- Public API documentation and relevant class docstrings MUST describe this behavior and reference the RDF 1.1 Concepts triples section as the governing normative source.
- Architecture and user-facing package documentation SHOULD call out this enforcement as a deliberate design feature that distinguishes the engine from more permissive RDF rule systems.

## Consequences

- The engine now has an explicit correctness boundary tied to the RDF 1.1 data model rather than treating all tuple-shaped triples as equally admissible.
- Invalid triples are prevented from polluting working memory, derivation traces, and store materialization.
- Tests for warning-mode behavior must verify both the warning emission and the absence of the malformed triple from engine state.
- Some integrations may need to opt into warning mode during migration or experimentation when upstream data quality is uncertain.
- This decision creates a clear documentation obligation across architecture, API docstrings, and implementation-facing package documentation.

## Supersedes

None.
