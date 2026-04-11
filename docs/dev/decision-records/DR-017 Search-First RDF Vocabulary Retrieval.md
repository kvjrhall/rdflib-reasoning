# Search-First RDF Vocabulary Retrieval

## Status

Accepted

## Context

`RDFVocabularyMiddleware` currently emphasizes manual vocabulary browsing
through `list_vocabularies`, `list_terms`, and `inspect_term`.
That tool surface is useful for Development Agent inspection and for targeted
Research Agent confirmation, but observed notebook behavior shows that it can
also invite repetitive browsing and overly deep ontology exploration.

This problem is especially visible when the Research Agent begins from a
plausible modeling direction, finds a few relevant OWL or RDFS terms, and then
continues browsing further into the indexed vocabulary rather than making a
local modeling decision and continuing the task.
The result is that a middleware capability intended to support practical term
selection can drift toward manual ontology spelunking.

The repository also wants client ergonomics that scale beyond hand-curated W3C
vocabularies.
Software clients SHOULD be able to supply relevant vocabularies to
`SpecificationCache` without also needing to annotate "root terms" or teach the
Research Agent how to reason about an explicit frontier abstraction.
The middleware should own retrieval behavior locally so that the Research Agent
sees a simple task-oriented workflow rather than another conceptual control
surface to deliberate about.

## Decision

RDF vocabulary retrieval SHALL move toward a search-first workflow.

- `RDFVocabularyMiddleware` SHOULD expose `search_terms` as the primary
  discovery tool for meaning-first vocabulary lookup.
- `inspect_term` remains the confirmation tool for candidate terms whose
  semantics matter to the current modeling decision.
- `list_terms` and `list_vocabularies` remain available, but they SHOULD be
  treated as secondary or manual exploration tools rather than the default
  Research Agent path.
- Ranking and retrieval policy remain middleware-owned implementation concerns.
  The Research Agent SHOULD experience a simple "search, inspect if needed, and
  continue" workflow rather than an explicit frontier or neighborhood control
  model.
- Middleware-owned ranking MAY use lexical, structural, and other signals
  derivable from the local indexed vocabulary set.
- Shared run-term telemetry between `DatasetMiddleware` and
  `RDFVocabularyMiddleware` is deferred.
  This record does not require a cross-middleware coordination mechanism, and
  it does not decide whether future ranking should consume such signals.

Later follow-up: [DR-019 Shared Middleware Services and Unified Vocabulary Configuration](DR-019%20Shared%20Middleware%20Services%20and%20Unified%20Vocabulary%20Configuration.md)
(later superseded by [DR-020 Middleware Stack Layering and Hook-Role Boundaries](DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md))
revised this telemetry deferral by introducing an explicit shared-service
boundary for coordinated middleware composition. The search-first direction of
this record remains accepted.

## Consequences

Benefits:

- vocabulary middleware is reoriented toward practical term retrieval instead
  of manual ontology browsing
- Research Agents can ask for the meaning they need without first knowing which
  vocabulary namespace or paging slice to inspect
- the design works better for client-supplied cached vocabularies because the
  middleware owns ranking and discovery behavior
- prompt and tool guidance can stay simpler because the agent does not need to
  reason about an explicit frontier concept

Costs and follow-up considerations:

- the repository now has an intended vocabulary capability that is not yet
  implemented in code
- architecture, roadmap, and README documentation must all be updated together
  so the intended design remains synchronized
- the exact ranking formula, semantic-search strategy, and whether to expose
  search-result explanations remain open follow-up design questions
- future shared run-term telemetry remains available as a later architectural
  refinement if search quality needs stronger within-run locality signals
  - This follow-up was later taken in [DR-019 Shared Middleware Services and Unified Vocabulary Configuration](DR-019%20Shared%20Middleware%20Services%20and%20Unified%20Vocabulary%20Configuration.md), then folded into [DR-020 Middleware Stack Layering and Hook-Role Boundaries](DR-020%20Middleware%20Stack%20Layering%20and%20Hook-Role%20Boundaries.md)

## Supersedes

None.
