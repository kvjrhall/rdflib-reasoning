# Development Documentation

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- Documentation SHOULD adhere to modern standards for quality technical writing.
- Documentation MUST allow for ambiguity due to partial specification or non-normative content, but it SHOULD be optimized for Development Agent understanding, whenever possible.
- Documentation SHOULD use RFC 2119 keywords
- Markdown references to any file under `docs/dev/` MUST use a relative markdown link
- Markdown references to directories (e.g., `docs/dev/decision-records`) MAY use a markdown link, and SHOULD if doing so would improve Development Agent and developer QOL.

## Architecture, decision records, and code

- **Intended architecture ("as it should be")**: `docs/dev/architecture.md` is the authoritative description of the current intended architecture and design.
- **Planned scope and sequencing**: `docs/dev/roadmap.md` is the authoritative description of planned feature priority, release grouping, and current intended delivery scope.
- **Rationale and history**: `docs/dev/decision-records/` capture why the architecture is the way it is and how it evolved; they are not, by themselves, the operational specification for the current state.
- **Implementation ("as it is")**: The codebase is the authority on the system’s actual behavior. When code and `architecture.md` disagree, this discrepancy MUST be treated as design drift to be resolved via code changes, documentation changes, and/or new decision records.

## Architecture and roadmap synchronization

- `architecture.md` and `roadmap.md` MUST remain cross-referentially consistent when they describe the same feature area.
- When `roadmap.md` links to a section of `architecture.md`, the linked section SHOULD continue to describe the same feature scope after edits to either document.
- When a feature is added, removed, renamed, split, merged, or moved between releases in `roadmap.md`, the Development Agent MUST verify whether corresponding updates are needed in `architecture.md`.
- When `architecture.md` materially changes intended system behavior or feature boundaries, the Development Agent MUST verify whether `roadmap.md` still reflects the intended release scope and priority.
- A Development Agent SHOULD consult `roadmap.md` before starting substantial design or implementation work so the task is aligned with the current planned release and priority order.
- A Development Agent MUST stop and verify that `roadmap.md` is still accurate before concluding a substantial task that changes Python behavior, middleware capabilities, release scope, or other implementation-significant behavior.
- A Development Agent MUST consider reprioritizing work or changing release scope when implementation reveals that a roadmap item is under-specified, blocked by newly discovered dependencies, too large for the intended release, or no longer consistent with `architecture.md`.
