# Tutorials

Tutorials are learning-oriented walkthroughs for a first successful use of a
package capability. The current tutorial pages render selected checked-in
notebooks with saved outputs; Sphinx does not execute notebooks during the docs
build.

Read them in this order:

- [RDFS inference](notebooks/demo-rdfs-inference.ipynb): RDFLib-backed RDFS
  materialization and proof inspection for one inferred triple. Start here if
  you are new to the engine package.
- [RDFS retraction](notebooks/demo-rdfs-retraction.ipynb): support-aware
  retraction through ordinary RDFLib statement removal. Read this after the
  inference tutorial to see update behavior.
- [Contradiction rules](notebooks/demo-contradiction-rules.ipynb): OWL 2 RL
  contradiction diagnostics when contradiction rules are enabled. Read this
  when you need diagnostic events rather than additional inferred triples.
- [Proof reconstruction](notebooks/demo-proof-reconstructor.ipynb): proof
  rendering, raw proof inspection, and fallback-to-leaf behavior. Read this when
  you want to inspect or present proof-shaped outputs directly.

```{toctree}
:maxdepth: 1
:caption: Rendered Notebook Tutorials

notebooks/demo-rdfs-inference
notebooks/demo-rdfs-retraction
notebooks/demo-contradiction-rules
notebooks/demo-proof-reconstructor
```
