# Notebooks

This directory contains the repository's checked-in notebooks for demos, experiments, and evaluation workflows.

## Suggested starting points

If you want a quick tour of the current reasoning surface, start here:

1. [demo-rdfs-inference.ipynb](./demo-rdfs-inference.ipynb): shortest tutorial for RDFLib-backed RDFS materialization and the rule applications behind one inferred triple
2. [demo-owl2-rl-inference.ipynb](./demo-owl2-rl-inference.ipynb): OWL 2 RL counterpart showing class-equivalence and subclass typing materialization plus proof inspection
3. [demo-rdfs-retraction.ipynb](./demo-rdfs-retraction.ipynb): companion tutorial showing that ordinary RDFLib statement removal retracts dependent RDFS inferences
4. [demo-contradiction-rules.ipynb](./demo-contradiction-rules.ipynb): contradiction diagnostics and explanation when OWL 2 RL contradiction rules are enabled
5. [demo-proof-reconstructor.ipynb](./demo-proof-reconstructor.ipynb): proof-focused companion notebook covering Mermaid rendering, markdown rendering, raw proof inspection, and fallback-to-leaf behavior

## Middleware demo series

These notebooks focus on Research Agent-facing middleware rather than direct RDFLib usage:

1. [demo-baseline-ontology-extraction.ipynb](./demo-baseline-ontology-extraction.ipynb): prompt-only RDF extraction baseline
2. [demo-dataset-middleware.ipynb](./demo-dataset-middleware.ipynb): dataset-backed middleware walkthrough with live trace rendering
3. [demo-vocabulary-middleware.ipynb](./demo-vocabulary-middleware.ipynb): vocabulary-aware middleware condition on top of the dataset baseline
4. [demo-vocabulary-middleware-ext.ipynb](./demo-vocabulary-middleware-ext.ipynb): extended vocabulary condition with an added domain-specific TBox

## Evaluation and supporting notebooks

- [baseline-proof.ipynb](./baseline-proof.ipynb): proof-evaluation baseline notebook

The notebooks in this directory are part of the repository's research and demonstration record rather than a separately published package.
