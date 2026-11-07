# Intentional Exclusion of Forward-Only OWL 2 Mapping Packaging

## Status

Accepted

## Context

`rdflib-reasoning-axioms` is primarily a **graph → structural elements** package:
`axiomatize` lifts RDF into `StructuralElement` partitions for validation, rendering,
exchange, and Research Agent use. Serialization (`as_triples` / `as_quads`) is the
companion projection, not the main product posture.

The OWL 2 Mapping to RDF defines some **forward-only packaging** rows and n-ary
authoring shapes whose reverse parse recovers an **equivalent but different**
structural set. Examples include n-ary `EquivalentClasses` / `EquivalentObjectProperties`
/ `EquivalentDataProperties` / `SameIndividual` (serialized as chains of binary
triples) and the mapping-table id `ObjectPropertyAssertionInverseOf` (forward
encoding of `ObjectPropertyAssertion(ObjectInverseOf(OP) a1 a2)` as `a2 OP a1`).
Reverse parse cannot reconstruct the authored packaging; it recovers binaries or an
ordinary `ObjectPropertyAssertion` on `OP`.

Dedicated `StructuralElement` types for those packagings would mainly help
assemble-first workflows that preserve authorship shape across a round-trip. That is
not the package priority. Treating missing n-ary models as incomplete coverage of
already-Implemented binary forms would mis-signal Development Agents and package
consumers.

This decision complements [DR-031 Standalone Structural Elements](DR-031%20Standalone%20Structural%20Elements.md);
it does not supersede it. OWL 1 legacy encodings such as `owl:distinctMembers` (which
normalize to the same `DifferentIndividualsNary` element) are out of scope here.

## Decision

- Development Agents MUST NOT add `StructuralElement` types whose only purpose is an
  OWL 2 Mapping packaging that reverse parse cannot reconstruct as that packaging.
- Structural traversal MUST recover the mapping-prescribed equivalent forms instead
  (for example binary `EquivalentClasses` / `EquivalentObjectProperties` /
  `EquivalentDataProperties` / `SameIndividual` chains, and ordinary
  `ObjectPropertyAssertion` on `OP` for the InverseOf individual-swap encoding).
- Package documentation MUST enumerate excluded packagings by **explicit searchable
  names**, distinguishing mapping-table ids (such as `ObjectPropertyAssertionInverseOf`)
  from true n-ary structural packagings.
- Feature-matrix "Implemented" status for binary forms MUST NOT be treated as a gap
  solely because a non-recoverable n-ary packaging model is absent.

## Consequences

- Graph → axioms remains the authoritative success criterion; exact round-trip of
  forward-only packaging is intentionally non-guaranteed for the named forms.
- Assemble-first preservation of those packagings is deferred unless a future decision
  expands scope beyond parse-first traversal.
- The catalog of excluded names lives in
  [`rdflib-reasoning-axioms/README.md`](../../rdflib-reasoning-axioms/README.md)
  (Forward-only mapping packagings not reconstructed) and is mirrored in intended
  architecture under structural traversal.
- Development Agents SHOULD consult that catalog before proposing n-ary or InverseOf
  assertion packaging types.
