"""Small shared helpers for middleware implementations."""

from rdflib import Dataset, Graph, IdentifiedNode, Node
from rdflib.plugins.stores.memory import Memory


def copy_graph(source_graph: Graph) -> Graph:
    """Return an new copy of a graph in ``O(triples)`` time.

    The new graph is backed by a :class:`rdflib.plugins.stores.memory.Memory`
    store. Be aware of the size of your ``source_graph`` before invoking this
    function. Aside from the store, the returned graph replicates all of the
    source graph's properties:
    namespace bindings, base URI, identifier, and triples.
    """
    # Rather than use the default store parameter (literal "default")
    # we create a new memory store explicitly. This gives us a stable interface
    # even if RDFLib changes what the default implementation is.
    graph_copy = Graph(
        identifier=source_graph.identifier,
        base=source_graph.base,
        store=Memory(),
    )
    for prefix, uri in source_graph.namespace_manager.namespaces():
        graph_copy.namespace_manager.bind(prefix, uri)
    for triple in source_graph:
        graph_copy.add(triple)
    return graph_copy


def copy_dataset(source_dataset: Dataset) -> Dataset:
    """Return an new copy of a dataset in ``O(quads)`` time.

    The new dataset is backed by a :class:`rdflib.plugins.stores.memory.Memory`
    store. Be aware of the size of your ``source_dataset`` before invoking this
    function. Aside from the store, the returned dataset replicates all of the
    source dataset's properties:
    namespace bindings, default graph base URI, and quads.
    """
    dataset_copy = Dataset(
        default_graph_base=source_dataset.default_graph.base,
        default_union=source_dataset.default_union,
        store=Memory(),
    )
    for prefix, uri in source_dataset.namespace_manager.namespaces():
        dataset_copy.namespace_manager.bind(prefix, uri)

    def _set_quad_context(
        quad: tuple[Node, Node, Node, IdentifiedNode | None],
    ) -> tuple[Node, Node, Node, Graph]:
        """Normalize a quad to always have a non-None graph identifier.

        As the backing store determines iff there is an identifier for the
        default graph, we have to use the dataset_copy's default graph for the
        context of the quad. Otherwise, we use the source dataset's graph for
        the quad's context.
        """
        s, p, o, g_id = quad
        g = (
            source_dataset.get_graph(g_id)
            if g_id is not None
            else dataset_copy.default_graph
        )
        assert isinstance(g, Graph), f"Graph {g_id} is not a in the dataset"
        return (s, p, o, g)

    dataset_copy.addN(iter(map(_set_quad_context, source_dataset.quads())))
    return dataset_copy


def not_none[T](value: T | None, message: str = "Value cannot be None") -> T:
    """Return ``value`` or raise ``ValueError`` when it is ``None``."""
    if value is None:
        raise ValueError(message)
    return value
