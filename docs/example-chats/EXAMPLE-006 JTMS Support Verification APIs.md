# EXAMPLE-006 JTMS Support Verification APIs

_Exported on 4/27/2026 at 15:59:55 EDT from Cursor (3.2.11)_

---

**User**

I'd like to actually work on a couple features from section **7. Release 0.5.0: Retraction and advanced engine behavior** of the @docs/dev/roadmap.md This is driven just by some personal motivation, as we'd technically be working on `v.0.4.0` now that `v0.3.0` has been released. What's a good entrypoint for some of the v0.5.0 features?

---

**Cursor**

The roadmap and architecture make the answer to this surprisingly specific. The `Truth Maintenance System (TMS)` architecture section pins down a 4‑step staged plan that explicitly orders the v0.5.0 work:

```466:472:docs/dev/architecture.md
- **Multi-Parent Support**: The `TMSController` MUST support multiple justifications for a single Fact. A Fact is considered logically supported if it has at least one valid `Justification` or is flagged as "Stated" (User-inserted).
- **Dependency Tracking**: Every `Justification` MUST capture a `PartialMatch` (as a tuple of FactIDs) to enable full **Derivation Tree** traversal. This is REQUIRED for both recursive retraction and generating human-readable explanations (e.g., Graphviz).
- **Recursive Retraction**: When a `Fact` is retracted, the `TMSController` MUST perform a **Mark-Verify-Sweep** operation. It MUST only retract downstream consequences if their `Justification` set becomes empty.
- **Support invariants**: A stated Fact MUST remain supported regardless of whether it also has zero, one, or many `Justification` records. A derived Fact MUST remain present if and only if it has at least one valid `Justification`.
- **Silent support semantics**: Silent status controls materialization and proof visibility only. It MUST NOT alter whether a derivation contributes support validity under JTMS invariants.
- **Removal propagation contract**: Low-level remove event forwarding MAY mirror add forwarding through `BatchDispatcher`, `RETEStore`, and `RETEEngine`, but logical removal MUST be governed by support validity rather than event arrival alone. A remove event MAY invalidate one support path without implying that the corresponding derived Fact is no longer present.
- **Staged implementation plan**: The intended Development Agent sequence is: (1) record support objects at production time for newly derived and already-known conclusions; (2) expose support verification APIs that can answer whether a Fact remains supported after one support path is invalidated; (3) implement recursive **Mark-Verify-Sweep** over the dependency graph; and only then (4) wire full triple removal through `RETEEngine`, `RETEStore`, and `BatchDispatcher`.
```

Mapped against today's code, step (1) is already done — `TMSController` records `Justification`s, a bidirectional `DependencyGraph`, and exposes a coarse `is_supported` / `support_count` / `justifications_for`:

```104:189:rdflib-reasoning-engine/src/rdflib_reasoning/engine/rete/tms.py
class TMSController(BaseModel):
    """
    Controller for truth-maintenance bookkeeping and recursive retraction.

    Retraction remains future work, but the controller scaffold marks the
    boundary that add-only implementations should remain compatible with.
    """
    ...
    def is_supported(self, triple: Triple) -> bool:
        fact = self.working_memory.get_fact(triple)
        if fact is None:
            return False
        return fact.stated or self.support_count(triple) > 0
```

…and `RETEEngine.retract_triples` / `RETEStore.remove` / `RETEStore._on_triples_removed` are still stubs:

```526:527:rdflib-reasoning-engine/src/rdflib_reasoning/engine/api.py
    def retract_triples(self, triple: Triple) -> None:
        raise NotImplementedError("RETEEngine.retract_triple is not implemented")
```

```117:122:rdflib-reasoning-engine/src/rdflib_reasoning/engine/rete_store.py
    def remove(
        self, triple: _TriplePatternType, context: _ContextType | None = None
    ) -> None:
        raise NotImplementedError(
            "Retractions (i.e., truth maintenance) are not yet supported"
        )
```

So the cleanly-scoped entry point for v0.5.0 is **step (2): JTMS support verification APIs** on `TMSController`.

## Recommended entrypoint: JTMS support verification APIs

This is roadmap item §7.1.1 and is the precondition for the higher-risk items (recursive retraction, removal-aware store flow, contradiction explanation). It is purely additive — read-only queries over data the engine is already recording — so it ships value without touching the add-only execution path or the store contract.

Concretely, what's missing today is anything that answers _"would this Fact remain supported if a specific support path were invalidated?"_ The current `is_supported` only checks whether _any_ justification exists; it can't tell you whether a _particular_ `Justification` is structural for that fact. That's what step (3) Mark-Verify-Sweep needs.

A reasonable shape for the new APIs on `TMSController`:

- `would_remain_supported(triple, *, without_justification=…)` / `…(without_antecedent=…)` — does the consequent have at least one _other_ valid justification if a given support path is removed?
- `transitively_supported(triple)` — verifies that every antecedent in every justification is itself supported (recursive descent over `DependencyGraph.antecedents_by_consequent`), required to make support validity meaningful when later cascades happen.
- `dependents_of(triple)` / `transitive_dependents_of(triple)` — read-only traversal over `consequents_by_antecedent` so callers (and the future Mark phase) can enumerate the candidate sweep frontier.
- A small `SupportSnapshot` / `SupportVerdict` value type (Pydantic, immutable, engine-internal — not a Research Agent boundary model) that captures `{is_stated, justification_count, has_alternative_support, dependents}` so tests and the future retractor consume one structured object rather than ad‑hoc tuples.
- Tighten the existing `is_supported` contract or replace it with a thin call into the new verifier so the "Silent support semantics" rule (silent does not affect support validity) is exercised explicitly in tests.

Existing tests at `rdflib-reasoning-engine/tests/test_engine.py` lines 1003–1097 already exercise `support_count` / `justifications_for` for both single-support and multi-support cases — they're the natural template for the new verification tests, particularly the multi-support test, which is exactly the case where "remove one path, fact still supported" is meaningful.

## Companion entrypoints, in order of decoupling

If you want a second, parallelizable thread that doesn't depend on the TMS sequence:

1. **Specialized relation indexes** (§7.1.5). Already has rationale captured in [DR-009 Transitive Relation Index Intent](docs/dev/decision-records/DR-009%20Transitive%20Relation%20Index%20Intent.md) and an explicit hook in the architecture (`Rule Matching & Network Topology` → "Specialized relation indexes"). It targets `rdfs:subClassOf` / `rdfs:subPropertyOf` reachability and is independent of retraction work, so it can advance in parallel without entangling the JTMS path.
2. **Richer contradiction explanation** (§7.1.6). Today's contradiction signaling per `architecture.md` line 372 is detection-only (`?x rdf:type owl:Nothing`). Derivation records already carry per-firing visibility/bootstrap metadata (DR-022) and grouped premises, so a notebook-quality contradiction explainer can be built over the existing `DerivationRecord` stream without waiting on retraction. This benefits from but doesn't strictly require the new support verification APIs.

## What I'd avoid as the first entry point

- **Recursive retraction (§7.1.3)** and **removal-aware store/engine flow (§7.1.4)** — these are the highest-risk items in the release and the staged plan explicitly puts them after support verification. Starting on Mark-Verify-Sweep without the verifier means you'll re-derive the same primitives ad hoc inside the retractor and likely duplicate them later.
- **Explicit dataset and quad operations (§7.1.2)** — `Dataset middleware capability phases` puts named-graph management in v0.4.0 (§6.1.2) and generic quad-level CRUD in v0.5.0 only "after earlier graph-oriented middleware phases have proven necessary and stable." Picking it up now would mean borrowing scope from v0.4.0 first, which cuts against your stated framing of "we're effectively on 0.4.0."

If you'd like, I can sketch a more detailed API surface for the support verification additions (signatures, the `SupportSnapshot` shape, and the test cases needed beyond the two existing ones at `test_rete_engine_tracks_*`), or pull the DR-009 index work into a similar concrete plan — your call which to expand.

---

**User**

Please prepare a plan to implement your recommended entrypoint: JTMS support verification APIs (roadmap item §7.1.1).

---

**Cursor**

Before I finalize the plan, two scope choices that meaningfully change the deliverable:

> **Two scope questions for the JTMS support verification APIs work — pick any that apply (or neither for a minimal landing).**
>
> - Include a small decision record (e.g., DR-023) committing to the verdict-type names and semantics that step (3) Mark-Verify-Sweep will depend on. ✔
> - Add a thin RETEEngine facade (e.g., engine.support_for(triple) / engine.dependents_of(triple)) so callers do not have to reach into engine.tms.
> - Tighten the existing TMSController.is_supported to require transitive support validity (currently checks only the local justification count). Today's add-only flow makes this a no-op semantically, but it locks in the architecture line 469 invariant.

I have everything I need. Drafting the plan now.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I’ll implement the approved JTMS support-verification slice exactly from the attached plan, starting with the TMS API additions and keeping the retraction/store stubs untouched.

I’ve confirmed the current TMS shape: support records already exist, so the code change can stay additive around `TMSController` plus exports and tests. Next I’m patching `tms.py` with the immutable snapshot and read-only verifier methods.

The TMS API layer is now in place. I’m wiring the new snapshot type through the internal RETE package exports before adding the behavioral tests.

The API and test coverage are drafted, including silent-rule parity and non-mutation checks. I’m adding the decision record now so the new verifier semantics are documented before I update the architecture text.

DR-023 is added and indexed. I’m updating the TMS architecture section now to reflect that support verification is the implemented second stage, while Mark-Verify-Sweep and removal wiring remain future work.

All planned code and documentation changes are in place. I’m starting validation using the project’s conda environment requirement and will fix any issues it surfaces.

Validation got as far as formatting: `ruff format` changed one file, so I’m inspecting the formatted diff and then rerunning the full validation.

The full validation run is taking longer than the first pass, so it’s continuing in the background. I’m waiting on that result before making any further changes.

`make validate test` passed. Because this change includes Markdown docs, I’m running the standalone `make check` pass as well to match the plan’s validation step.

All to-dos are complete and validation is green. I’m doing one final status check so I can summarize the exact files touched and any notable validation details.

Implemented the JTMS support verification APIs for roadmap §7.1.1.

Added `Justification.id`, immutable `SupportSnapshot`, and read-only verifier methods on `TMSController`: `support_snapshot`, `would_remain_supported`, `transitively_supported`, `dependents_of`, `transitive_dependents_of`, and `justifications_for_fact_id`. Exported `SupportSnapshot` from the RETE internals package.

Added focused coverage in `rdflib-reasoning-engine/tests/test_tms.py`, including alternative supports, single-path invalidation, stated-fact behavior, transitive support, cycle safety, dependency traversal, silent-rule support semantics, and non-mutation.

Also added `docs/dev/decision-records/DR-023 JTMS Support Verification API Surface.md`, indexed it, and updated `docs/dev/architecture.md` to mark TMS staged step (2) as implemented while leaving Mark-Verify-Sweep and removal wiring deferred.

Validation passed:

- `/Users/roberthall/miniforge3/bin/conda run -n rdflib-reasoning make validate test`
- `/Users/roberthall/miniforge3/bin/conda run -n rdflib-reasoning make check`
- `ReadLints` found no errors in edited Python files.

I did not edit the plan file.
