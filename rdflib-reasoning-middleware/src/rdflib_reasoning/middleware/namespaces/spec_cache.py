from collections.abc import Mapping, MutableMapping, Sequence, Set
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Final

from rdflib import Graph, Namespace, URIRef
from rdflib.graph import ReadOnlyGraphAggregate
from rdflib.namespace import PROV, RDFS
from rdflib_reasoning.middleware.namespaces.spec_index import RDFVocabulary

# NOTE: Disabled caching and fetching remote specs for now; will revisit later.
# from platformdirs import user_cache_path
# KNOWN_SPECS: Final[Set[str]] = frozenset(
#     [
#         str(ns)
#         for ns in [
#             BRICK,
#             CSVW,
#             DC,
#             DCAM,
#             DCAT,
#             DCMITYPE,
#             DCTERMS,
#             DOAP,
#             FOAF,
#             ODRL2,
#             ORG,
#             OWL,
#             PROF,
#             PROV,
#             QB,
#             RDF,
#             RDFS,
#             SDO,
#             SH,
#             SKOS,
#             SOSA,
#             SSN,
#             TIME,
#             VANN,
#             VOID,
#             WGS,
#             XSD,
#         ]
#     ]
# )

BUNDLED_SPECS: Final[Set[str]] = frozenset([str(ns) for ns in [RDFS, PROV]])

URIS_TO_FILENAME: Final[Mapping[str, str]] = MappingProxyType(
    {
        # str(BRICK): "brick.ttl",
        # str(CSVW): "csvw.ttl",
        # str(DC): "dc.ttl",
        # str(DCAT): "dcat.ttl",
        # str(DCMITYPE): "dctype.ttl",
        # str(DCTERMS): "dcterms.ttl",
        # str(DCAM): "dcam.ttl",
        # str(DOAP): "doap.ttl",
        # str(FOAF): "foaf.ttl",
        # str(ODRL2): "odrl2.ttl",
        # str(ORG): "org.ttl",
        # str(OWL): "owl.ttl",
        # str(PROF): "prof.ttl",
        str(PROV): "prov-o.ttl",
        # str(QB): "qb.ttl",
        # str(RDF): "rdf.ttl",
        str(RDFS): "rdfs.ttl",
        # str(SDO): "sdo.ttl",
        # str(SH): "sh.ttl",
        # str(SKOS): "skos.ttl",
        # str(SOSA): "sosa.ttl",
        # str(SSN): "ssn.ttl",
        # str(TIME): "time.ttl",
        # str(VANN): "vann.ttl",
        # str(VOID): "void.ttl",
        # str(WGS): "wgs.ttl",
        # str(XSD): "xsd.ttl",
    }
)


class SpecificationCache:
    # cache_path: Path
    _specs: MutableMapping[str, ReadOnlyGraphAggregate]
    _vocabularies: MutableMapping[str, RDFVocabulary]

    def __init__(self, **more_specs: Graph):
        # self.cache_path = user_cache_path(
        #     "rdflib-reasoning",
        #     appauthor=False,
        #     ensure_exists=True,
        # )
        self._specs = {}
        self._vocabularies = {}
        for namespace, graph in more_specs.items():
            # We make a read-only copy of the graph to avoid external modifications
            g = Graph(identifier=graph.identifier)
            for prefix, uri in graph.namespace_manager.namespaces():
                g.namespace_manager.bind(prefix, uri)
            for triple in graph:
                g.add(triple)
            self._specs[namespace] = ReadOnlyGraphAggregate([g])

    def get_spec(self, namespace: URIRef | Namespace | str) -> Graph:
        key = str(namespace)
        if key in self._specs:
            return self._specs[key]

        if key not in BUNDLED_SPECS:
            raise ValueError(f"Namespace is not bundled or cached: {key}")

        filename = URIS_TO_FILENAME[key]
        match Path(filename).suffix:
            case ".jsonld":
                format = "json-ld"
            case ".n3":
                format = "n3"
            case ".nt":
                format = "n"
            case ".rdf":
                format = "rdf/xml"
            case ".ttl":
                format = "turtle"
            case _:
                raise ValueError(f"Unknown file extension: {filename}")

        with resources.path(__package__, filename) as bundled_path:
            graph = Graph()
            graph.parse(bundled_path, format=format)
            self._specs[key] = ReadOnlyGraphAggregate([graph])

        return self._specs[key]

    def list_indexed_vocabularies(self) -> Sequence[str]:
        return tuple(sorted(BUNDLED_SPECS | set(self._specs.keys())))

    def get_vocabulary(self, namespace: URIRef | Namespace | str) -> RDFVocabulary:
        key = str(namespace)
        if key in self._vocabularies:
            return self._vocabularies[key]

        vocabulary = RDFVocabulary.from_graph(namespace, self.get_spec(namespace))
        self._vocabularies[key] = vocabulary
        return vocabulary
