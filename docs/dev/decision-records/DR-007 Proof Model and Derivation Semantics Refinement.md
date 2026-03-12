# Proof Model and Derivation Semantics Refinement

## Status

Accepted

## Context

`DR-006` established the separation between engine-native derivation logging and reconstructed `DirectProof` values.
That separation remains correct, but implementation work on the proof and derivation stubs exposed several design details that needed to be made explicit.

The repository now has concrete proof models in `rdflib-reasoning-engine` that are intended to support both engine-reconstructed explanations and Research Agent-authored proofs.
Those models need to support:

- grouped conclusions from a single rule application;
- minimal engine-native rule identifiers that can be enriched later;
- richer semantic annotations for user-facing proof steps;
- agent-authored proof steps that may express intended semantics without a paired engine rule;
- immutable proof artifacts suitable for evaluation and interchange.

The earlier record did not distinguish sufficiently between engine-native rule identity and proof-level semantic description, and it did not capture the grouped-conclusion or immutability choices now reflected in the code stubs.

## Decision

- `rdflib-reasoning-engine` MUST distinguish between engine-native rule identity and proof-level semantic metadata.
- Engine-native derivation records MUST use a minimal `RuleRef`-style identifier sufficient to name the applied rule within a ruleset.
- User-facing proof steps such as `RuleApplication` MUST use a richer `RuleSemanticsRef`-style structure that can carry labels, descriptions, and authoritative references.
- `RuleSemanticsRef` MUST allow its paired engine rule identifier to be absent so that Research Agent-authored proofs can express intended semantics even when no engine-native `RuleRef` is available.
- When a `RuleApplication` carries both a derivation record and a paired engine rule identifier, the proof model MUST enforce their alignment.
- Engine-native derivation records and reconstructed proof steps MUST support grouped conclusions from a single rule application. A single inference step MAY therefore justify one or more related claims.
- Authoritative rule references stored in package `src/**` code MUST use distributable identifiers such as authoritative URIs. Runtime models MUST NOT depend on repository-local `docs/` paths or cached specification file paths.
- Proof and derivation data classes intended for interchange and evaluation SHOULD be immutable.

## Consequences

- The engine can emit compact provenance data while proof reconstruction enriches that provenance into a more human-meaningful explanation layer.
- Research Agent-authored proofs remain representable even when they do not correspond exactly to a known engine rule.
- A grouped `RuleApplication` can preserve the human-meaningful shape of a rule firing without requiring later reassembly from fragmented proof nodes.
- Immutable proof objects are safer to compare, cache, and reuse across evaluation tooling.
- `DR-006` remains directionally correct about the derivation-versus-proof split, but it is no longer the authoritative description of the proof model details.

## Supersedes

- [DR-006 Derivation Logging and DirectProof Reconstruction](DR-006%20Derivation%20Logging%20and%20DirectProof%20Reconstruction.md)
