# Prospective Use Cases

This document records research-facing use cases that this repository may support
directly or enable through downstream systems. It is a planning input, not a
commitment to implementation scope.

Authoritative scope remains in [architecture.md](architecture.md) and
[roadmap.md](roadmap.md). Development Agents MAY cite this document when
explaining motivation, identifying future dependencies, or deciding whether a
roadmap item should be split, deferred, or rephrased. Development Agents MUST NOT
treat this document as overriding architecture, roadmap, decision records, or
source code.

## Planning Role

Use this document to preserve the shape of long-horizon ideas while keeping the
near-term roadmap honest. A prospective use case can influence release planning
when it reveals a shared foundation, an ordering dependency, or a risk that would
make an earlier feature harder to integrate later.

The current planning implications are:

- Structural traversal and representation are core infrastructure, not merely a
  convenience around OWL 2 serialization.
- OWL 2 RDF mapping and OWL 2 RL inference SHOULD remain adjacent in roadmap
  planning so inferred triples can be lifted back into structural
  representations.
- Provenance is a cross-cutting concern for graph import, knowledge exchange,
  proof evaluation, and memory-oriented use cases.
- Remote retrieval, graph embeddings, learned inference layers, backward
  chaining, LangGraph skill packaging, and subagent packaging SHOULD remain
  post-core enhancements unless a concrete experiment pulls them forward.

## Use Case Index

| Use case | Planning posture |
| --- | --- |
| [Graph Inference Layers](#graph-inference-layers-gils) | Post-core research expansion |
| [Agent Knowledge Exploration](#agent-knowledge-exploration) | Core structural representation driver |
| [Graph Embeddings](#graph-embeddings) | Post-core research expansion |
| [RDF Graph Extraction](#rdf-graph-extraction) | Current and continuing middleware driver |
| [Knowledge Exchange](#knowledge-exchange) | Core post-structural capability |
| [Deductive Memory](#deductive-memory) | Later memory architecture driver |
| [Backward-Chaining Inference](#backward-chaining-inference) | Post-core reasoning expansion |
| [Proof Authoring and Exchange](#proof-authoring-and-exchange) | Proof and evaluation driver |
| [Packaging Experiments](#packaging-experiments) | Non-monotonic adoption experiments |

## Graph Inference Layers (GILs)

A Graph Inference Layer (GIL) is a learned graph-processing layer trained for
rule-learning tasks over RDF graphs. Conceptually, it approximates or replaces a
forward-chaining inference engine inside a larger machine-learning system. A GIL
could be pretrained over RDF graph tasks, transplanted into a larger network,
and optionally frozen to create a contract boundary between network segments.

This is not core infrastructure for the pre-`1.0.0` roadmap. It becomes more
tractable after the system can generate closure datasets, provide stable graph
or axiom ordering, and evaluate inferred output against formal reasoners.

### Edge Prediction GILs

Goal: train a network to produce inference closures over RDF graphs.

Procedure:

1. RDF statements are represented as a sequence of embedded triples, for example
   embeddings of N-Triples tokens.
2. The network produces a sequence of embedded triples containing the closure.
3. The embeddings are decoded into RDF statements.
4. The output sequence represents the input graph plus inferred statements.

RDF graphs have set semantics, so training should not rely on one canonical
statement order. Dataset generation MAY use shuffled traversals to augment graph
order. A permutation-invariant loss such as
[Set Cross Entropy](https://arxiv.org/abs/1812.01217) is a promising match for
this rule-learning scenario.

### Training GILs for Known Rules

For a known rule set, a symbolic inference engine can generate supervised
training data. Input statements are copied to an output buffer as they are fed
to the engine. Whenever the engine produces inferred triples in response to a
new input statement, those triples can be shuffled and appended to the output
buffer. The final output buffer should contain the deductive closure over the
input graph.

Dependencies:

- Deterministic closure generation for selected rule profiles
- Stable graph serialization and ordering utilities for evaluation
- Dataset generation tools that can preserve or vary statement order

### Training GILs for Unknown Rules

For an unknown rule set, the input and output graphs may be arbitrarily ordered
subject to structural constraints:

1. All input graph statements appear in the output graph.
2. Input graph statements preserve their relative order inside the output graph.
3. The output graph sequence MAY interleave inferred statements between
   subsequences of input statements.

Dependencies:

- Graph comparison and containment utilities
- Order-aware dataset generation
- Evaluation methods that separate stated triples from inferred candidates

### RDFLib GIL Reasoner

A GIL reasoner would be an alternative to the RETE engine. It would take learned
embedding, decoding, and prediction models. As triples are added to a graph, they
would be supplied to the GIL engine, and predicted triples would be materialized
into the output model.

Planning posture: post-`1.0.0` research expansion. This should not block the
symbolic inference, structural traversal, or middleware roadmap.

## Agent Knowledge Exploration

Agents can read RDF triples and RDF serializations, but this often forces them
to reconstruct structural intent from low-level statements. OWL 2 RDF mappings
are a common example: a single logical construct may require correlating several
triples and identifiers. Axiomatization reduces this cognitive load by lifting
graph content into structured objects that can be serialized, validated, and
rendered as prose.

### Axiom Traversal

Goal: produce an agent-readable description of an ontology or graph.

Procedure:

1. A graph is axiomatized into structured concepts.
2. The structured concepts are sorted into a stable order.
3. Each concept is rendered as text using labels, CURIEs, and deterministic
   fallback identifiers.
4. The resulting text is supplied to an agent or another downstream consumer.

Planning implications:

- Structural traversal SHOULD be planned as a core capability.
- Stable ordering is part of the representation contract, not just formatting.
- Prose rendering SHOULD use graph labels and vocabulary metadata when
  available, while remaining deterministic when labels are missing.
- Traversal SHOULD work over graphs containing inferred triples, even when the
  inference profile is incomplete.

## Graph Embeddings

Graph embeddings use a stable textual representation of a graph or subgraph as
input to text-oriented embedding, retrieval, or classification systems. This is
not a near-term core feature, but it depends heavily on structural traversal and
stable representation.

### Graph Representation for Embeddings

Goal: represent ABox data and relevant TBox context as an embedding-ready text
document.

Procedure:

1. A graph or subgraph is selected.
2. Referenced TBox background data is included when needed.
3. The graph is axiomatized into structured elements.
4. The structural elements are sorted into a stable order.
5. The stable text representation is passed to a text processing model.

Dependencies:

- Structural traversal over ABox and TBox content
- Stable text rendering
- Explicit graph or subgraph selection policy
- Optional inference over selected graph content

### Graph Retrieval

Goal: retrieve graph content by embedding its structural text representation.

A retrieval system may associate both a graph artifact and its rendered text with
the same vector. Retrieval may return full graph documents, embedded subgraphs,
or ranked documents based on matched embedded subsets. If retrieved context is
used by a GIL or another graph-level consumer, the retrieved RDF statements can
be appended to the existing graph sequence because RDF graph semantics are set
oriented.

Planning posture: post-core enhancement after graph import, provenance, and
stable structural representation are available.

### Graph Classification

Goal: classify graphs or subgraphs through their stable text representation.

The structural text representation can be supplied to a text classification
model. This should be treated as an enabled downstream use case rather than a
core repository milestone unless a concrete experiment requires it.

## RDF Graph Extraction

RDF graph extraction interprets unstructured or semi-structured documents as RDF
graphs. This requires identifying source concepts, choosing target vocabulary
terms, and deciding when local vocabulary creation is warranted.

Planning implications:

- Dataset middleware remains a central Research Agent capability.
- Vocabulary middleware remains important for grounded term selection.
- Structural traversal and stable text can support extraction by exposing
  relevant background ontology context.
- Extraction workflows SHOULD remain experimentally controllable through
  middleware composition.

This use case is already represented by the baseline, dataset, and vocabulary
notebook series. It should continue to inform middleware ergonomics, validation,
and evaluation.

## Knowledge Exchange

Knowledge exchange is multi-channel interchange between RDF graphs, structured
axioms, prose, proof objects, and schema-driven payloads. The same knowledge may
need to be supplied as RDF serialization, typed structural elements, generated
text, or a combination of these forms.

Goal: allow agents and tools to create, validate, store, and serialize structured
knowledge.

Procedure:

1. Middleware exposes an interface for creating structural elements or repeated
   knowledge patterns.
2. The interface validates the structure and checks grounding, provenance,
   citations, or trust metadata when available.
3. The agent adds the resulting content to a dataset through a controlled
   interface.
4. The dataset or selected subgraph is serialized as RDF, structural objects,
   prose, proof payloads, or other target output types.

Planning implications:

- Knowledge exchange depends on structural traversal and representation.
- Provenance should be modeled as a general capability, not only as remote
  retrieval metadata.
- Common patterns such as `skos:Concept` and `prov:Derivation` MAY eventually
  deserve structural helper models even when they are not OWL 2 mapping
  constructs.
- Append-only or time-sliced modeling patterns MAY become important for memory
  and trust workflows.

Planning posture: core post-structural capability, currently expected after OWL
system integration and graph import/provenance baselines.

## Deductive Memory

Deductive memory treats an RDF dataset as agent memory that can be reasoned over.
Long-term, episodic, short-term, and blackboard memory architectures may all use
RDF-backed state with different persistence and access policies.

Goal: allow memory-backed agents to store atemporal facts, infer consequences,
and expose those consequences through traversal, retrieval, or explanation.

Planning implications:

- Memory support SHOULD build on dataset middleware rather than bypassing it.
- Inference-enabled datasets may materialize deductions eagerly or answer
  selected questions through query-time inference.
- Axiomatization and graph embeddings should automatically benefit from enabled
  reasoners.
- Memory architecture should remain a later capability until dataset,
  inference, structural traversal, and provenance contracts are stable.

## Backward-Chaining Inference

Backward-chaining inference answers queries without necessarily materializing all
consequences. This resembles query-time reasoning systems such as Apache Jena's
LP rule engine and can support eventual hybrid reasoning architectures.

Planning implications:

- Backward chaining is a post-core reasoning expansion.
- It should not interfere with the forward-chaining RETE/JTMS substrate.
- If introduced, it SHOULD compose with proof/explanation and structural
  traversal contracts rather than creating a separate explanation universe.

## Proof Authoring and Exchange

Proof authoring lets agents construct formal proof payloads directly, rather
than relying entirely on stock reasoning engines. Proof exchange lets those
proofs be validated, serialized, evaluated, and reused across tools.

Goal: represent generated, reconstructed, or agent-authored reasoning in a
schema-driven proof format backed by graph content where appropriate.

Planning implications:

- `DirectProof` remains the common proof interchange format for baseline work.
- Middleware MAY validate proof payloads against graph content, provenance, and
  expected structure.
- Agent-authored proof steps may go beyond stock engine derivations, but they
  should still be inspectable and evaluable.
- Proof serialization and exchange should stay separate from proof rendering.

### Proof Evaluation Harness

Goal: interrogate a formally expressed agent rationale.

Evaluation can support fine tuning, hallucination detection, grounding checks,
and critique workflows. Proofs may be backed by RDF graph content, expected
claims, provenance records, or other structured context.

Planning posture: reusable evaluation infrastructure should remain incremental.
The initial harness should stay narrow, while later proof authoring and exchange
work can broaden the evaluation contract.

## Packaging Experiments

LangGraph skill packaging and subagent packaging are adoption experiments rather
than monotonic feature milestones. They may improve usability or performance for
specific workflows, but they may also add overhead, fragmentation, or premature
abstraction.

Planning implications:

- Skill packaging MAY be evaluated once a repeated workflow has stable inputs,
  outputs, and success criteria.
- Subagent packaging MAY be evaluated for bounded workflows such as retrieval,
  axiom authoring, proof critique, or structural summarization.
- These experiments SHOULD be measured against concrete use cases before they
  become committed architecture.
- Evaluation may result in adoption, partial adoption, or rejection.

Planning posture: post-core or use-case-driven experimental track. These efforts
SHOULD NOT be treated as required pre-`1.0.0` infrastructure unless a specific
milestone exposes a measurable need.
