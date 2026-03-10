# Decision Records

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

- All decision records MUST BE located in `docs/dev/decision-records/`
- The cumulative interpretation of all decision records MUST be consistent with [`docs/dev/architecture.md`](../architecture.md).
- Decision records are listed in [INDEX.md](INDEX.md); the next record number follows the most recent DR.

## Creating New Decision Records

- [`docs/dev/decision-records/template.md`](template.md) MUST be followed when creating a decision record.
- The decision record's filename MUST be `DR-XXX Short Title.md` where `XXX` is a zero-padded dense sequence number (e.g. 001) following the most recent DR, and "Short Title" is a brief descriptive name.
- When a new or updated decision record changes the intended architecture, [`docs/dev/architecture.md`](../architecture.md) MUST be updated to reflect that change (typically by treating the architecture as having been changed as of the new record's date).
- [`docs/dev/architecture.md`](../architecture.md) MAY also be updated directly (e.g., for clarifications or non-substantive adjustments), but for substantive architectural changes a new or updated decision record SHOULD be authored.
- The decision record MUST be added to [`docs/dev/decision-records/INDEX.md`](INDEX.md).

## How agents should use decision records

- **Architecture baseline**: When validating or reasoning about the current intended system design, Development Agents MUST use [`docs/dev/architecture.md`](../architecture.md) as the single source of truth for the "as it should be" architecture. Decision records provide supporting rationale and history only.
- **Avoid partial DR inference**: Development Agents MUST NOT attempt to infer the current architecture by applying only a subset of decision records; this risks inconsistency. They MUST always reason from `architecture.md` when talking about the present intended design.
- **Drafting new decision records**: When drafting a new decision record that affects architecture or design, Development Agents MUST first read [`docs/dev/architecture.md`](../architecture.md) and treat it as the baseline that the decision modifies.
- **Superseding**: When a new decision changes or overturns an older one, it MUST be expressed as a new decision record that explicitly supercedes the older record (see "Superceding" below), and `architecture.md` MUST be updated to reflect the newer decision. Older records generally SHOULD NOT be retroactively rewritten to match the architecture.

### Superceding

- The new decision record MUST enumerate & link to any documents that it supercedes
- Supercedes decision records MUST be updated to reference the new decision record
- Superceded records in [the decision record index](INDEX.md) MUST be updated to indicate which record superceded them.
