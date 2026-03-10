# Development Documentation

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- Documentation SHOULD adhere to modern standards for quality technical writing.
- Documentation MUST allow for ambiguity due to partial specification or non-normative content, but it SHOULD be optimized for Development Agent understanding, whenever possible.
- Documentation SHOULD use RFC 2119 keywords
- Markdown references to any file under `docs/dev/` MUST use a relative markdown link
- Markdown references to directories (e.g., `docs/dev/decision-records`) MAY use a markdown link, and SHOULD if doing so would improve Development Agent and developer QOL.

## Architecture, decision records, and code

- **Intended architecture ("as it should be")**: `docs/dev/architecture.md` is the authoritative description of the current intended architecture and design.
- **Rationale and history**: `docs/dev/decision-records/` capture why the architecture is the way it is and how it evolved; they are not, by themselves, the operational specification for the current state.
- **Implementation ("as it is")**: The codebase is the authority on the system’s actual behavior. When code and `architecture.md` disagree, this discrepancy MUST be treated as design drift to be resolved via code changes, documentation changes, and/or new decision records.
