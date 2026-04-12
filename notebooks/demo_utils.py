"""
Prompts for the rdflib-reasoning notebooks.
We stash them here so that we can be consistent across the notebooks.

We provide supplemental prompts for Research Agents when they are not using
specific middleware instances. The middleware instances give guidance as well as
describe their tools, so we also provide tool-agnostic guidance here. The goal
is not to give a baseline agent hidden capabilities, but to avoid disadvantaging
it merely because some modeling guidance would otherwise only be present in a
middleware-appended prompt.

Constants:
  - CORE_PROMPT: The core prompt for the agent.
  - DATASET_TIPS: Tool-agnostic RDF modeling guidance extracted from DatasetMiddleware.
  - VOCABULARY_TIPS: Tool-agnostic vocabulary-selection guidance extracted from VocabularyMiddleware.
  - WHITELIST_TIPS: Tool-agnostic vocabulary-constraint guidance extracted from namespace whitelisting.
  - STOPPING_CRITERIA: Completion criteria shared across notebook experiments.
  - TASK: The task for the agent to complete.
"""

from itertools import chain
from typing import Final

from rdflib import RDFS, Graph, URIRef

CORE_PROMPT: Final[str] = """
You are a research assistant specialized in knowledge graphs and the Semantic Web.

Task objective:
- Represent the provided source text as RDF, grounded in explicit claims from that text.
- Do not introduce uncertain or speculative facts unless explicitly requested.
- Produce one faithful, reasonable RDF representation rather than exhaustively
  exploring every possible modeling alternative.

Modeling requirements:
- Keep assertions faithful to source content.
- Prefer stable, atemporal statements over transient phrasing.
- Prefer a clear and defensible modeling choice over prolonged self-critique.
- Prefer representing explicit source claims over designing additional ontology
  structure that the source does not require.
- Reuse established RDF, RDFS, OWL, and other task-appropriate terms when they
  fit your intended meaning.
- Prefer the least ontology invention that still yields a faithful RDF
  representation.
- Do not introduce helper abstractions, organizing concepts, or auxiliary
  relations unless they are genuinely needed to represent explicit claims from
  the source.
- If several faithful encodings are possible, choose one reasonable approach,
  apply it consistently, and finish.
- If you mint terms, provide human-readable documentation (at minimum rdfs:label and rdfs:comment).
- If no base IRI is provided by the user, use <urn:example:> for minted IRIs.

Output requirements:
- Final answer MUST include exactly one `text/turtle` fenced block.
- Outside that block, include only brief explanatory text if necessary.
- Do not continue revising once you have produced a faithful Turtle answer that
  substantially satisfies the task.
"""

DATASET_TIPS: Final[str] = """
## RDF Modeling Guidance

- Treat RDF as the canonical representation of facts that should be stated clearly
  and unambiguously.
- Prefer assertions that remain true independent of the wording of the source
  text. Model stable relationships rather than transient phrasing when possible.
- Keep RDF assertions grounded in the provided content unless the user explicitly
  asks for inference, extrapolation, or hypothesis generation.
- Do not encode uncertainty, hedging, speculation, or disputed claims as settled
  triples unless the uncertainty itself is what is being modeled.
- Prefer representing explicit claims over inventing extra ontology structure
  that is not needed to state those claims.
- When transforming unstructured text into RDF, it is acceptable to build the
  graph incrementally, but each addition should still form a coherent fragment.
- Prefer concise, recoverable modeling decisions over large speculative graphs.

## Minting Terms

- If the user does not specify a base IRI, use <urn:example:> for newly
  minted IRIs.
- If you mint a new Class, Datatype, or Property, you MUST define it with at
  least `rdfs:label` and `rdfs:comment`.
- When minting a new local IRI for a Class or Datatype, the local name SHOULD
  be singular and use `PascalCase`, for example `ProjectReport`,
  `FieldObservation`, or `QualityRating`.
- When minting a new local IRI for a Property, the local name SHOULD use
  `camelCase`, for example `hasInventoryCode`, `recordedAtFacility`, or
  `reviewStatus`.
- Prefer minted IRIs for terms that you are introducing deliberately and expect
  to refer to again.
- Do not mint IRIs where RDF or OWL conventions expect an anonymous structural
  node instead, such as OWL restrictions or RDF collections.
- Prefer a meaningful existing IRI over a fresh blank node when an established
  identifier is already available and appropriate.

## RDF Shape and Serialization

- Turtle is the preferred serialization unless the user requests a different RDF
  format.
- Use RDF literals, not IRIs, for textual values such as labels and comments.
- A class or property definition should usually be self-describing enough that a
  reader can understand why it exists without needing the original prompt.
"""

VOCABULARY_TIPS: Final[str] = """
## Controlled Vocabulary Guidance

- Before minting new terms, think carefully about whether established RDF,
  RDFS, OWL, SKOS, PROV, or other task-appropriate vocabularies already express
  the intended meaning.
- Existing terms include terms already present in the RDF you are extending.
- Existing terms also include widely used controlled vocabularies that you know
  well enough to apply correctly.
- You MAY use `rdf:type`, `rdfs:label`, and `rdfs:comment` without extra
  deliberation when they are clearly appropriate.
- Prefer one quick vocabulary check over extended ontology exploration.
- Before first using another standard term that is semantically important to
  your modeling choice, slow down enough to confirm that it fits your intended
  meaning.
  - Terms such as `rdfs:Class`, `rdfs:subClassOf`, and `owl:Class` are often
    modeling-significant rather than mere bookkeeping.
- Once a vocabulary tool or prior reasoning step has already answered whether a
  candidate term fits, do not keep re-checking that same term.
- If a scan already returned plausible candidates, move to choosing among them
  rather than repeatedly widening the search.
- Do not assume the meaning of an existing term from its local name alone.
- Reuse an established term only when its intended semantics fit the source
  material and your intended assertion.
- When deciding whether to mint a local term or reuse a standard term, prefer
  checking whether a standard term fits before minting.
- If you are unsure whether an existing term is semantically appropriate, prefer
  minting a clearly documented local term over misusing a standard one.
- When you reuse a controlled-vocabulary term, stay compatible with its apparent
  role. For example, do not use a class as if it were a property, or a property
  as if it were an individual.
- When modeling document-derived facts, choose the narrowest established term
  that is still clearly justified by the source.
"""

WHITELIST_TIPS: Final[str] = """
## Vocabulary Constraint Guidance

- You SHOULD only use terms from established, well-known RDF vocabularies
  such as RDF, RDFS, OWL, and XSD for predicates and type assertions.
- If you need to use terms from additional vocabularies, prefer well-known
  ones (SKOS, PROV, FOAF, etc.) when they fit the source material.
- Before using a vocabulary term, verify that it exists in that vocabulary.
  For example, rdfs:type does not exist -- the correct term is rdf:type.
- The fact that the task permits minting terms under an open base IRI does not
  by itself justify creating a new local term.
- Treat local minting as a fallback to use when no fitting established term is
  available and a new term is genuinely needed for the representation.
- For your own minted terms, use the base IRI specified in the task.
"""

STOPPING_CRITERIA: Final[str] = """
## Completion / Stop Condition

You SHOULD stop and return your final answer once ALL of the following are
substantially true:
1) The major explicit claims you identified for representation have been
   captured in RDF.
2) Newly minted Classes, Datatypes, and Properties that remain in your answer
   have the required human-readable documentation.
3) If dataset tools were used, your final `text/turtle` block reflects the
   dataset state you intend to present to the user.

You do not need to keep searching for additional triples once your current RDF
graph is faithful, coherent, and responsive to the task.

When done:
- Stop calling tools.
- Return final answer immediately with exactly one `text/turtle` markdown code-fence block.
- If your current RDF already reflects the answer you intend to present, do not
  keep re-rendering, restating, or lightly rephrasing it; return the final
  answer.
- Do not include planning language such as “I will continue”, “next I will”, or similar.
- Do not ask yourself for another review pass unless the user explicitly asks
  for revision or critique.
"""

TASK: Final[str] = """
Please assist me in representing the subject matter of the following text as an RDF graph.
Please reuse established RDF, RDFS, OWL, or other appropriate standard terms
when they fit the source. Please use <urn:ex:> as the base only for IRIs that
you genuinely need to mint as part of your response. Do not invent helper
relations or organizing abstractions unless they are needed to represent an
explicit claim from the text. Be sure to label any new terms or properties that
you mint so that they are human readable.

```text
John is a person. Modern people are classified as _homo sapiens_. Apparently,
homo sapiens falls under the subtribe of Hominina. Every Hominidae is a
Haplorhini, and now the names don't even sound like they're related. Then
we get to primates, which can be controversial for some people, for some reason.
Nobody argues with the idea that primates are mammals, yet some people take
umbrage with the idea that _homo sapiens_ is an animal. Oh, Hominidae contains
Hominina, too. Emotions and theological views aside, can we formalize this?
```
"""

expected_graph: Final[Graph] = Graph().parse(
    data="""
@prefix ex: <urn:ex:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

ex:John a ex:Person .

# NOTE: We wouldn't expect owl:equivalentClass unless the agent knows OWL
ex:Person rdfs:subClassOf ex:HomoSapiens ;
          owl:equivalentClass ex:HomoSapiens .

ex:HomoSapiens rdfs:subClassOf ex:Hominina ;
               a rdfs:Class, owl:Class .

ex:Hominina rdfs:subClassOf ex:Hominidae ;
            a rdfs:Class, owl:Class .

ex:Hominidae rdfs:subClassOf ex:Haplorhini ;
             a rdfs:Class, owl:Class .

ex:Haplorhini rdfs:subClassOf ex:Primate ;
              a rdfs:Class, owl:Class .

ex:Primate rdfs:subClassOf ex:Mammal ;
           a rdfs:Class, owl:Class .

ex:Mammal rdfs:subClassOf ex:Animal ;
          a rdfs:Class, owl:Class .

""",
    format="turtle",
)


# FIXME: This is pretty important.
# TODO: We shouldn't penalize the agent for eagerly materializing RDFS inferences,
#       so we should use our rdflib-reasoning-engine to remove triples that we
#       can infer from the expected graph. This is the same as what we'd do for
#       comments & labels.
def evaluate_actual_graph(
    extracted_graph: Graph,
    expected_graph: Graph = expected_graph,
) -> tuple[dict, dict[str, Graph]]:
    """Evaluate an extracted graph against the expected notebook target graph.

    `rdfs:label` and `rdfs:comment` triples that appear only in the extracted
    graph are treated as acceptable best-practice documentation extras rather
    than automatic errors. Those triples are excluded from the returned
    `extra` and `union` graphs and from the extra/union/extracted counts used
    in overlap metrics.

    The `urns_in_namespace` measure intentionally does *not* ignore URIs that
    appear only in those filtered documentation triples, because documenting an
    otherwise unrelated minted IRI still pollutes the extracted graph.
    """
    urn_count: int = 0
    urn_valid_count: int = 0
    for node in extracted_graph.all_nodes():
        if isinstance(node, URIRef):
            if node.startswith("urn:"):
                urn_count += 1
                if node.startswith("urn:ex:"):
                    urn_valid_count += 1

    missing_triples: Graph = expected_graph - extracted_graph
    raw_extra_triples: Graph = extracted_graph - expected_graph

    best_practices_extras = set(
        filter(
            lambda t: t in raw_extra_triples,
            chain(
                extracted_graph.triples((None, RDFS.label, None)),
                extracted_graph.triples((None, RDFS.comment, None)),
            ),
        )
    )
    best_practices_count = len(best_practices_extras)

    extra_triples = Graph()
    for triple in raw_extra_triples:
        if triple not in best_practices_extras:
            extra_triples.add(triple)

    intersection_triples: Graph = expected_graph - missing_triples

    union_triples = Graph()
    for triple in expected_graph:
        union_triples.add(triple)
    for triple in extracted_graph:
        if triple not in best_practices_extras:
            union_triples.add(triple)

    graphs: dict[str, Graph] = {
        "intersection": intersection_triples,
        "missing": missing_triples,
        "extra": extra_triples,
        "union": union_triples,
    }

    expected_count = len(expected_graph)
    extracted_count = len(extracted_graph) - best_practices_count
    intersection_count = len(intersection_triples)
    missing_count = len(missing_triples)
    extra_count = len(extra_triples)
    union_count = len(union_triples)

    precision = intersection_count / extracted_count if extracted_count else 0.0
    recall = intersection_count / expected_count if expected_count else 1.0
    f1_score = (
        2 * precision * recall / (precision + recall) if precision + recall else 0.0
    )
    jaccard_index = intersection_count / union_count if union_count else 1.0
    triple_edit_distance = missing_count + extra_count
    normalized_triple_edit_distance = (
        triple_edit_distance / union_count if union_count else 0.0
    )
    exact_match = missing_count == 0 and extra_count == 0

    measures = {
        "urns_in_namespace": urn_valid_count / urn_count if urn_count > 0 else None,
        "exact_match": exact_match,
        "metrics": {
            "best_practices_excluded": best_practices_count,
            "f1_score": f1_score,
            "jaccard_index": jaccard_index,
            "normalized_triple_edit_distance": normalized_triple_edit_distance,
            "precision": precision,
            "recall": recall,
            "triple_edit_distance": triple_edit_distance,
        },
        "counts": {
            "expected": expected_count,
            "extracted": extracted_count,
            "intersection": intersection_count,
            "false_negatives": missing_count,
            "false_positives": extra_count,
            "union_count": union_count,
        },
    }
    return measures, graphs


def pprint_measures(measures: dict):
    expected_count = measures["counts"]["expected"]
    actual_count = measures["counts"]["extracted"]
    intersection_count = measures["counts"]["intersection"]
    missing_count = measures["counts"]["false_negatives"]
    extra_count = measures["counts"]["false_positives"]
    union_count = measures["counts"]["union_count"]

    precision = measures["metrics"]["precision"]
    recall = measures["metrics"]["recall"]
    f1_score = measures["metrics"]["f1_score"]
    jaccard_index = measures["metrics"]["jaccard_index"]
    triple_edit_distance = measures["metrics"]["triple_edit_distance"]
    normalized_triple_edit_distance = measures["metrics"][
        "normalized_triple_edit_distance"
    ]
    exact_match = measures["exact_match"]

    print(f"Expected triples: {expected_count}")
    print(f"Actual triples: {actual_count}")
    print(f"Intersection triples: {intersection_count}")
    print(f"Missing triples: {missing_count}")
    print(f"Extra triples: {extra_count}")
    print(f"Union triples: {union_count}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    print(f"F1 score: {f1_score:.3f}")
    print(f"Jaccard Index: {jaccard_index:.3f}")
    print(f"Triple Edit Distance: {triple_edit_distance}")
    print(f"Normalized Triple Edit Distance: {normalized_triple_edit_distance:.3f}")
    print(f"Exact Match: {exact_match}")
