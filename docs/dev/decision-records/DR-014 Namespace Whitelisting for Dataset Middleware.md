# Namespace Whitelisting for Dataset Middleware

## Status

Accepted

## Context

The notebook demo series (`demo-baseline-ontology-extraction.ipynb`, `demo-dataset-middleware.ipynb`, `demo-vocabulary-middleware.ipynb`) establishes a methodology for fair experimental comparison between baseline and middleware-enabled Research Agent conditions.
The core technique is **prompt asymmetry reduction**: tool-agnostic guidance is extracted from middleware prompts and provided to the baseline so that measured performance deltas reflect middleware capabilities rather than unfair prompting.
For example, `DATASET_TIPS` in `notebooks/demo_utils.py` is tool-agnostic guidance extracted from `DatasetMiddleware`'s prompt, and `VOCABULARY_TIPS` is guidance extracted from `RDFVocabularyMiddleware`'s prompt.

Observed Research Agent behavior in the middleware demos shows that vocabulary drift and misuse remain dominant quality problems:

- Agents mint variant terms (`ex:Primates` instead of `ex:Primate`) even when prompted to prefer controlled vocabularies.
- Agents use non-existent terms from standard namespaces (`rdfs:type` instead of `rdf:type`).
- Agents introduce unnecessary properties and classes that inflate the graph without contributing to the target semantics.

A potential mitigation is **namespace whitelisting**: configuring `DatasetMiddleware` with a set of allowed vocabularies so that `add_triples` rejects URIs from non-whitelisted namespaces.
The question was whether this feature would compromise experimental validity by introducing a capability asymmetry that cannot be reduced through the established prompt-extraction methodology.

The alternative — not introducing namespace whitelisting — was considered.
Analysis showed that whitelisting decomposes into an **information component** (enumerating allowed vocabularies in the prompt) and an **enforcement component** (rejecting non-whitelisted URIs at the tool boundary).
The information component can be extracted into a tool-agnostic prompt constant for the baseline, following the same pattern as `DATASET_TIPS` and `VOCABULARY_TIPS`.
The enforcement component is a genuine middleware affordance that the baseline cannot replicate through prompting alone.
This is the same information-vs-enforcement split that already exists for `DatasetMiddleware`'s parseability benefit, which the demo series treats as a valid middleware effect.

rdflib's `DefinedNamespace` (closed vocabularies such as `RDF`, `RDFS`, `OWL`) supports term-level membership testing, while `Namespace` (open vocabularies) supports prefix-based membership testing.
This distinction enables differentiated enforcement: closed vocabularies can reject specific non-existent terms, while open vocabularies can only enforce namespace-prefix membership.

## Decision

Namespace whitelisting SHALL be introduced as an opt-in configuration for `DatasetMiddleware` with three affordances:

1. **Enforcement**: When whitelisting is enabled, `add_triples` MUST reject URIs whose namespace is not among the allowed vocabularies. The error message MUST remind the Research Agent of its allowed vocabularies. For closed vocabularies (`DefinedNamespace` subclasses), enforcement MUST include term-level membership testing. For open vocabularies (`Namespace` instances), enforcement MUST be limited to namespace-prefix matching.

2. **Enumeration**: When whitelisting is enabled, the middleware-appended system prompt MUST include a structured enumeration of the allowed vocabularies. A corresponding tool-agnostic extraction of this enumeration SHOULD be maintained for baseline prompt-asymmetry reduction.

3. **Remediation**: For closed vocabularies, the middleware SHOULD use Levenshtein distance (or equivalent string-similarity metric) to suggest the nearest valid term when a rejected URI appears to come from a whitelisted closed vocabulary but names a non-existent term (e.g., `rdfs:type` rejected with a suggestion of `rdf:type`).

Whitelisting MUST accept both `Namespace` (open) and `DefinedNamespace` (closed) vocabulary specifications.
Whitelisting MUST be disabled by default so that existing experiments and demos are unaffected.
The feature MUST be configurable through `DatasetMiddlewareConfig` or an equivalent configuration surface.

## Consequences

- Existing experiments continue to operate without behavioral change because whitelisting is disabled by default.
- New experiments can enable whitelisting and study its effect as an independent variable within the middleware composition framework.
- The vocabulary enumeration prompt text MUST have a corresponding tool-agnostic extraction for baseline fairness, following the `DATASET_TIPS` / `VOCABULARY_TIPS` pattern established in `notebooks/demo_utils.py`.
- For open namespaces, enforcement is prefix-only and cannot catch intra-namespace term-naming errors (e.g., `ex:Primates` vs. `ex:Primate`). This limitation is inherent to open vocabularies and is not a deficiency of the whitelisting design.
- For closed namespaces, enforcement includes term-level membership testing, which can catch errors such as `rdfs:type` (non-existent) when `rdf:type` was intended.
- The remediation affordance (Levenshtein suggestions) adds implementation complexity but directly addresses the most actionable class of errors observed in demo runs.
- Architecture and roadmap documentation MUST be updated to reflect the new feature scope.
