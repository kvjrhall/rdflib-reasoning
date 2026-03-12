# Using Apache Jena References

- Use `fetch-jena.sh` to download `jena-docs/` and `jena-source/`

- Use `jena-docs/` to understand the approach that Jena has taken towards its design and the high-level types of documentation.

- Use `jena-source/` when asking _"how have other systems achieved this?"_ and _"what might we have overlooked?"_

- The `rdflib-reasoning` metapackage and its subpackages MUST NOT contain ANY content copied from Apache Jena or any other repository; citations are allowed, but there are STRICT restrictions on citations.
  - Our repository MUST NOT plagiarize ANY Apache Jena code; Even though the Apache 2.0 license permits reuse under certain conditions, this project's policy is that any such usage would be extremely rare and clearly disclosed.
  - [Our Documentation](../../) MAY cite Apache Jena documentation or code
    - Citations in our documentation MUST be accompanied by attribution, URL, and the citation must either be a markdown block-quotes ('>') or code listing ('```').
  - Our code MUST NOT EVER quote Apache Jena code or documentation verbatim; this is the definition of plagiarism
    - Our code SHOULD link to the URL of any Apache Jena references that informed its design, making the design rationale transparent and giving credit, without copying text or code.

- IMPORTANT: You might not see `jena-source/**` or `jena-docs/**` files with your `Glob` or `Grep` tools.
- IMPORTANT: Use `Read` with an explicit file path (e.g. from the listing below). Use `SemanticSearch` scoped to this directory (e.g. `docs/specs/jena-inspiration`) with a query.
- IMPORTANT: Use the following listing as a source of file names:

```shellout
$ find docs/specs/jena-inspiration
docs/specs/jena-inspiration
docs/specs/jena-inspiration/fetch-jena.sh
docs/specs/jena-inspiration/jena-source
docs/specs/jena-inspiration/jena-source/jena-core
docs/specs/jena-inspiration/jena-source/jena-core/src
docs/specs/jena-inspiration/jena-source/jena-core/src/main
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl-b.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-fb.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-fb-tgc-noresource.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl-fb.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-fb-lp-expt.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-b-tuned.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-fb-tgc.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl-fb-old.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl-fb-mini.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-fb-tgc-simple.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl-fb-micro.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/owl.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-b.rules
docs/specs/jena-inspiration/jena-source/jena-core/src/main/resources/etc/rdfs-noresource.rules
docs/specs/jena-inspiration/jena-docs
docs/specs/jena-inspiration/jena-docs/inference.html
docs/specs/jena-inspiration/AGENTS.md
```
