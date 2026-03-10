# External Specifications

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- `docs/specs/<specname>/` subdirectories are dynamically-retrieved files for some set of specifications
- `docs/specs/<specname>/optimized.html` MUST be optimized for Development Agent and script/tooling understanding, if it is present. Elements SHOULD be pruned of presentational content, retaining/adding elements where the semantics of the data become more clear. Element `class` attributes can serve as a way to denote the category of an item.
- One SHOULD use `make specs-normalize` [Makefile target](../../Makefile) to fetch & normalize these specifications if they are absent

| Specification | Description | Use When |
| ------------- | ----------- | -------- |
| `owl2-conformance` | | |
| `owl2-mapping-to-rdf` | | |
| `owl2-overview` | | |
| `owl2-reasoning-profiles` | | |
| `owl2-semantics-direct` | | |
| `owl2-semantics-rdf` | | |
| `owl2-structure-syntax` | | |
| `rdf11-concepts-syntax` | | |
| `rdf11-datasets` | | |
| `rdf11-primer` | | |
| `rdf11-schema` | | |
| `rdf11-semantics` | | |
