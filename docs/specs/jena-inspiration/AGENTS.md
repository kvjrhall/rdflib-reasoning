# Using Apache Jena References

- This directory is an external inspiration reference, not a normative source
  for this repository's behavior. Use it when asking "how have other systems
  achieved this?" or "what might we have overlooked?"
- Use `fetch-jena.sh` to download or refresh `jena-docs/` and `jena-source/`
  when the local references are absent or stale.
- High-value entry points:
  - `jena-docs/inference.html` for Jena's public inference documentation.
  - `jena-docs/flows.md` for local notes about inference-related design flows.
  - `jena-source/jena-core/src/main/resources/etc/` for Jena rule resources.
- Search within this directory or inspect explicit paths when comparing design
  choices. Treat Jena source and documentation as evidence for design
  inspiration, not as implementation material to copy.
- The `rdflib-reasoning` metapackage and its subpackages MUST NOT contain any
  content copied from Apache Jena or any other repository.
- Repository documentation MAY cite Apache Jena documentation or code when the
  citation includes attribution and a URL. Verbatim excerpts in documentation
  MUST be limited to clearly marked Markdown block quotes or code listings.
- Repository code MUST NOT quote Apache Jena code or documentation verbatim.
  Code MAY link to Apache Jena references that informed design rationale,
  without copying text or code.
