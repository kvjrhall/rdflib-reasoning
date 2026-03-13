---
name: rdfs-ruleset-test-refactor
overview: Refactor the RDFS ruleset test suite to be spec-driven, cover all RDFS 1.1 entailment rules and key edge/error cases, and enforce RDF data model constraints on literals and predicates while keeping OWL 2 RL rules out of scope.
todos:
  - id: identify-rdfs-ruleset-gaps
    content: Enumerate and align RDFS rule ids (rdfs1–rdfs13) in RDFS_RULES and tests, filling in gaps or adding clear TODO markers if certain rules are not yet implemented.
    status: completed
  - id: refactor-rdfs-micro-tests
    content: Refactor RdfsTestCase parametrized tests in test_ruleset_rdfs.py to be spec-driven, cover all implemented RDFS rules, and avoid strict derivation-count or one-step assumptions.
    status: completed
  - id: add-rdfs-integration-tests
    content: Add a second layer of RDFS integration and edge-case tests covering chains, cycles, multiple domain/range declarations, interaction with rdfs_axioms, and explicit non-entailment scenarios.
    status: completed
  - id: implement-literal-predicate-constraints
    content: Implement and test engine-level enforcement of RDF term-type constraints for literal subjects and non-IRI predicates with configurable error vs warning policies.
    status: completed
  - id: add-multiple-derivation-xfail-tests
    content: Create xfail/skip tests that document intended multiple-derivation-path properties without asserting current behavior, to prevent the feature from being forgotten.
    status: completed
  - id: wire-spec-links-into-tests
    content: Ensure all RDFS tests and RDF data-model constraint tests include explicit W3C spec URLs (RDF 1.1 Semantics and RDF 1.1 Concepts) so reviewers without local specs can follow the associations.
    status: completed
isProject: false
---

### Goals

- **Spec-driven RDFS coverage**: Ensure tests cover all RDFS 1.1 entailment rules (rdfs1–rdfs13) using examples traceable to the W3C RDF 1.1 Semantics spec.
- **Robust, maintainable tests**: Decouple triple entailment assertions from exact derivation counts and one-step assumptions; separate micro rule tests from integration/edge-case tests.
- **RDF data model enforcement**: Add behavior and tests so the engine never materializes triples with literal subjects or non-IRI predicates, with configurable error vs warning behavior, aligned with RDF 1.1 Concepts.
- **OWL 2 RL framing only**: Optionally frame some tests in terms of RDFS support assumed by OWL 2 RL, without ever running or asserting OWL 2 RL rules or derivations.

### High-level approach

- **1. Rework the core RDFS micro tests** in `rdflib-reasoning-engine/tests/test_ruleset_rdfs.py` to be:
  - Parameterized over a complete set of RDFS rules (rdfs1–rdfs13) rather than a hand-picked subset.
  - Spec-driven: each test case references the corresponding W3C anchor (e.g. `https://www.w3.org/TR/rdf11-mt/#dfn-rdfs2`) in comments/docstrings, not local cached spec paths.
  - Independent of exact derivation counts or single firing steps: assert that required output triples are entailed and that there exists at least one matching derivation record for core RDFS rules, but do not require `len(logger.records) == 1` or a specific firing order.
- **2. Introduce a two-layer test structure** for RDFS:
  - **Layer A – Rule-focused micro tests**:
    - Keep something like `RdfsTestCase`, but:
      - Use rule ids that match the W3C spec exactly (`rdfs2`, `rdfs3`, `rdfs5`, etc.), dropping internal split ids like `rdfs5a`/`rdfs5b`.
      - Use `example_number` purely to distinguish multiple examples for the same rule id.
      - For each rule rdfs1–rdfs13, add at least one minimal test case whose input–output shape matches the spec’s pattern of entailment.
    - Update the shared fixture that wires `RDFS_RULES` into a `RETEStore` to be reused by both micro and integration tests.
  - **Layer B – Integration and edge-case tests**:
    - Add separate tests (or parametrized groups) that:
      - Use longer subClass/subProperty chains and cycles to check transitivity closure and termination.
      - Exercise multiple inheritance and multiple domain/range declarations.
      - Combine user triples with the `rdfs_axioms` fixture to validate schema-level closure for core vocabulary terms.
      - Include non-entailment scenarios to confirm the engine doesn’t over-generate.
    - These tests will typically assert only on triple entailment, not on derivation records.
- **3. Implement structural/graph-shape edge cases** (per your earlier request) in the integration layer:
  - **Transitive chains**:
    - Subproperty: chains of length ≥3 (e.g. `a ⊑ b`, `b ⊑ c`, `c ⊑ d` ⇒ `a ⊑ d`).
    - Subclass: similar chains for `rdfs:subClassOf`.
  - **Cycles**:
    - Symmetric subclass and subproperty cycles (e.g. `a ⊑ b`, `b ⊑ a`; `p ⊑ p`).
    - Assert that closure is finite (no infinite growth) and that expected reflexive/closure behavior holds.
  - **Multiple domain and range declarations**:
    - `p rdfs:domain C1`, `p rdfs:domain C2`, `x p y` ⇒ both `x rdf:type C1` and `x rdf:type C2`.
    - Similar for `rdfs:range`.
  - **Interaction with RDFS axioms inventory**:
    - Treat `rdfs_axioms` as an inventory of axioms entailed on the empty graph; design tests that:
      - Load both `rdfs_axioms` and additional schema/user triples.
      - Assert expected schema-level inferences without mutating the fixture.
- **4. Implement RDF term-type constraints in the engine and tests**
  - **4.1 Engine behavior for literals as subjects** (implementation + tests):
    - Introduce a dedicated `LiteralAsSubjectError` exception type in the engine layer.
    - Add a configuration flag or policy object for the RETE engine or store (e.g. `literal_subject_policy` with options `"error"` or `"warning"`).
    - At the point where new inferred triples are materialized or added to RETE memory, check the subject term:
      - If it is a literal and policy is `"error"`, raise `LiteralAsSubjectError` with an error message that cites the RDF 1.1 Concepts triples section (e.g. `https://www.w3.org/TR/rdf11-concepts/#section-triples`).
      - If policy is `"warning"`, emit a `LiteralAsSubjectWarning(UserWarning)` with the same reference and **do not** insert the triple into RETE memory or the output graph.
    - Ensure that literal subjects never propagate into match memories or user-visible entailments under any configuration.
  - **4.2 Engine behavior for non-IRI predicates**:
    - Similarly enforce that the predicate is always an IRI, per RDF 1.1 Concepts.
    - Introduce `[BlankNode|Literal]PredicateError` and `[BlankNode|Literal]PredicateWarning(UserWarning)` types (or an equivalent consolidated naming that still clearly encodes the problem), with messages that cite `https://www.w3.org/TR/rdf11-concepts/#section-triples`.
    - Ensure such illegal predicate bindings are filtered out before they enter RETE memory or the materialized graph when configured for warnings.
  - **4.3 Unit and integration tests for term-type enforcement**:
    - Add focused unit tests that:
      - Configure the engine for `"error"` mode and assert that attempting to derive or insert a triple with a literal subject or non-IRI predicate raises the appropriate error type with a message referencing the correct W3C section.
      - Configure the engine for `"warning"` mode and assert that the warning is emitted while the illegal triple does not appear in the graph, nor participates in subsequent inferences.
    - Add RDFS-focused tests that create conditions where domain/range or subclass rules would *try* to construct such illegal triples, verifying that the safety checks intercept these cases.
- **5. Non-entailment and robustness tests**
  - Add negative tests where certain entailments **must not** occur, such as:
    - `x p y` with no domain or range declarations for `p` ⇒ no new `rdf:type` assertions for `x` or `y`.
    - Subproperty / subclass links that are absent, ensuring no inferred triples appear solely from unrelated axioms.
  - Extend `graph_under_test` (or add helper assertions) to provide good diagnostics when unexpected triples appear or expected triples are missing, but without assuming a single derivation step.
  - Keep `rdfs_axioms` immutable and treat it explicitly as an inventory of axioms entailed by an RDFS reasoner on the empty graph.
- **6. Multiple-derivation path tests (xfail/skip)**
  - Design one or more unit tests (in the RDFS test module or a dedicated derivation-logging module) that:
    - Intend to assert properties about multiple derivation paths per entailed triple.
    - Are clearly documented with comments explaining their **intent**, but **do not** include code listings or example code in the comment or body (only high-level natural language about the desired property).
    - Are marked `xfail` or `skip` (choose whichever is more idiomatic for the project) so that:
      - The missing multiple-derivation functionality is visible and tracked.
      - The current behavior is not required to satisfy these properties yet.
- **7. Spec-driven coverage and explicit spec references**
  - For RDFS tests:
    - Maintain a small mapping in the tests from internal rule ids (`"rdfs2"`, `"rdfs3"`, etc.) to their **canonical W3C URLs**, using anchors like `https://www.w3.org/TR/rdf11-mt/#dfn-rdfs2`.
    - In test docstrings or comments, include the external spec link so external reviewers without local specs can follow the association.
    - Optionally, add a meta-test that asserts each rule id present in `RDFS_RULES` is known in the mapping and that the mapping covers rdfs1–rdfs13.
  - For RDF data-model constraints:
    - Reference `https://www.w3.org/TR/rdf11-concepts/#section-triples` in error/warning messages and in test descriptions, as the normative basis that subjects must be IRIs or blank nodes and predicates must be IRIs.
- **8. OWL 2 RL–framed but RDFS-only support tests**
  - Without loading or using OWL 2 RL rules, add a small set of tests that:
    - Use input/output shapes that correspond to RDFS support assumed by RL rules (e.g. class subsumption on individuals, domain/range propagation, schema closure on class and property hierarchies).
    - Are documented as "RDFS support assumed by OWL 2 RL" in comments, but:
      - Do **not** assert anything about RL rule ids or derivations.
      - Do **not** enable or refer to actual RL rulesets in fixtures.
    - Help ensure that if and when an RL ruleset is used elsewhere, the underlying RDFS entailment behavior will already satisfy the assumptions made by OWL 2 RL.

### Todos

- **identify-rdfs-ruleset-gaps**: Enumerate which RDFS rules (rdfs1–rdfs13) are currently implemented in `RDFS_RULES` and add missing rule ids or TODO markers if implementation is out of scope for now.
- **refactor-rdfs-micro-tests**: Redesign `RdfsTestCase` usage and parametrized tests in `test_ruleset_rdfs.py` to cover all implemented RDFS rules with spec-referenced examples while relaxing derivation-count and one-step assumptions.
- **add-rdfs-integration-tests**: Create a second layer of integration/edge-case tests for structural graph shapes (chains, cycles, multiple domain/range, interaction with `rdfs_axioms`, and non-entailment cases).
- **implement-literal-predicate-constraints**: Update the engine (RETE inference and triple materialization points) to enforce RDF term-type constraints with configurable error/warning policies, plus focused unit tests.
- **add-multiple-derivation-xfail-tests**: Introduce xfail/skip tests that describe the desired multiple-derivation-path properties without locking in current derivation mechanics.
- **wire-spec-links-into-tests**: Add and validate explicit W3C spec URLs in test docstrings and error/warning messages, ensuring alignment with RDF 1.1 Semantics and RDF 1.1 Concepts.
