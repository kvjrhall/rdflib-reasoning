# Transitive Relation Index Intent

## Status

Accepted

## Context

The repository's current reasoning direction centers on a general-purpose forward-chaining RETE engine for RDFS and OWL 2 RL entailment.
That engine is an appropriate default for many rule forms, but some relations are more naturally and efficiently handled as reachability problems than as generic repeated rule firing.

Prior art such as Apache Jena uses specialized handling for transitive schema relations, especially `rdfs:subClassOf` and `rdfs:subPropertyOf`, to improve performance over a purely generic rule-engine path.
The same implementation discussion also surfaced a broader horizon question: whether a specialized transitive mechanism might later help with selected general transitive properties beyond the RDFS schema lattice.

The repository is not yet ready to standardize a concrete data structure, update algorithm, or proof/explanation strategy for such an optimization.
However, the architectural intent should be recorded now so that engine work does not unnecessarily preclude a dedicated relation-index path.

## Decision

- The repository intends to support a specialized relation index that the reasoning engine MAY use for selected transitive or reachability-oriented relations.
- The initial intended targets for this specialized handling are `rdfs:subClassOf` and `rdfs:subPropertyOf`.
- This specialized relation index is intended as an optimization and architectural extension of the engine, not as a separate alternate inference channel that bypasses engine correctness requirements.
- No specific algorithm, storage layout, proof representation, or update procedure is standardized by this record.
- Future design work SHOULD evaluate how such an index interacts with derivation logging, explanation reconstruction, support bookkeeping, warm-start behavior, and eventual retraction support before any implementation is treated as complete.
- Future design work MAY evaluate whether the same architectural pattern should be extended beyond the initial schema-lattice targets toward selected general transitive properties.

## Consequences

- Engine and store design discussions may now treat a specialized transitive relation index as an intended optimization direction rather than an out-of-scope idea.
- The first implementation focus remains narrow: schema-oriented transitive relations with clear reachability semantics.
- The repository avoids prematurely committing to a single indexing strategy, closure policy, or query integration boundary.
- Later design records can refine this intent into a concrete implementation contract once tradeoffs around proofs, invalidation, persistence, and truth maintenance are better understood.

## Supersedes

None.
