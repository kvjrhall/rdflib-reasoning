# Shared Middleware Services and Vocabulary Context

## Status

Superseded by [DR-020 Middleware Stack Layering and Hook-Role Boundaries](DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md)

## Context

The middleware stack needs explicit coordination across components without
collapsing into a monolithic middleware module.

`DatasetMiddleware` already owns the live RDFLib dataset and its locking
boundary, but adjacent middleware also need shared state:

- dataset, retrieval, and future inference middleware need a stable shared
  runtime boundary for the same live RDF dataset
- dataset middleware and vocabulary middleware need one coherent vocabulary
  policy so the Research Agent cannot inspect terms that later fail
  `add_triples`
- future vocabulary ranking wants access to run-local term-usage telemetry
- developers need one vocabulary setup path rather than separately wiring a
  whitelist and a specification cache

The initial `VocabularyConfiguration` helper improved coordination, but it still
forced callers to decompose one conceptual vocabulary setup into separate
objects and pass them around manually. That preserved the risk of drift and kept
an incoherent public API surface alive.

## Decision

Middleware coordination SHALL use explicit shared runtime objects.

- `DatasetRuntime` remains the shared mutable coordination boundary for
  middleware operating on the same live RDF dataset.
- `DatasetSession` remains dataset-specific state owned by `DatasetRuntime`; it
  SHALL NOT become a container for vocabulary policy or telemetry concerns.
- `RunTermTelemetry` remains a separate run-local shared service. Dataset
  middleware MAY record asserted term usage into it, and later middleware MAY
  consume it.

Vocabulary setup SHALL use a two-step model:

- `VocabularyConfiguration` is the only public declarative input surface for
  vocabulary setup.
- `VocabularyDeclaration` remains the declarative unit: prefix, namespace, and
  optional `UserSpec`.
- `VocabularyContext` is the only public runtime vocabulary object injected into
  middleware.
- `VocabularyConfiguration.build_context()` is the public construction path for
  `VocabularyContext`.
- `VocabularyContext` exposes cached read-only vocabulary runtime state,
  including:
  - `whitelist`
  - `specification_cache`
- `VocabularyContext` SHALL enforce this invariant by construction:
  - `indexed_vocabularies ⊆ whitelisted_namespaces`

Declaration semantics SHALL be:

- every declaration contributes a whitelist entry
- a declaration contributes an indexed vocabulary if either:
  - the namespace matches a bundled specification enabled for that context, or
  - `user_spec` is provided
- declarations without bundled data and without `user_spec` remain allowed for
  dataset use but are not indexed
- bundled vocabularies are declaration-driven only; they are not ambiently
  available simply because the repository bundles them

The repository SHALL provide one convenience helper on the declarative surface:

- `VocabularyConfiguration.bundled_plus(...)` returns a fully explicit
  configuration containing the repository-standard bundled vocabularies plus any
  additional declarations

Middleware construction SHALL be symmetric and explicit:

- `DatasetMiddleware` SHALL require `DatasetMiddlewareConfig`
- `DatasetMiddlewareConfig` SHALL require `vocabulary_context: VocabularyContext`
- `RDFVocabularyMiddleware` SHALL require `RDFVocabularyMiddlewareConfig`
- `RDFVocabularyMiddlewareConfig` SHALL require
  `vocabulary_context: VocabularyContext`
- bare middleware constructors and raw whitelist/cache injection SHALL NOT
  remain supported public setup paths

Vocabulary middleware remains read-only with respect to dataset state, but it
SHALL consume the injected `VocabularyContext` for both visible indexed
vocabularies and vocabulary-policy enforcement.

## Consequences

Benefits:

- the FOAF-style mismatch becomes impossible through the public API: if a
  vocabulary is visible to vocabulary middleware, it is allowed by dataset
  middleware in the same context
- middleware users learn one coherent construction path instead of multiple
  special cases
- vocabulary policy and vocabulary indexing become one shared runtime concept
  rather than two independently wired objects
- `DatasetRuntime` stays focused on dataset coordination and does not absorb
  unrelated vocabulary concerns

Costs and follow-up considerations:

- the public middleware API is intentionally breaking: bare constructors and raw
  whitelist/cache wiring are removed rather than deprecated
- docs, notebooks, and tests must all move to the new config-to-context path at
  once
- lower-level types such as `SpecificationCache` and whitelist implementations
  still exist as internal building blocks, but they are no longer the normal
  middleware construction story
- `search_terms` remains a separate follow-up
- future inference-triggered triple accounting remains separate follow-up work

## Supersedes

None. This record revises the telemetry deferral noted in
[DR-017 Search-First RDF Vocabulary Retrieval](DR-017%20Search-First%20RDF%20Vocabulary%20Retrieval.md)
without replacing that record as a whole.
