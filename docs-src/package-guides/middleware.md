# Middleware Package

The `rdflib-reasoning-middleware` package provides runtime integration surfaces
for RDF dataset state, vocabulary access, tracing, continuation control, and
Research Agent-facing tool workflows.

Use this package when you need:

- dataset-backed state primitives for agent workflows;
- thin tool adapters over RDFLib-backed dataset operations;
- vocabulary search and namespace constraints for RDF term selection;
- tracing helpers for inspectable notebook and evaluation runs;
- boundary models that keep runtime schemas separate from engine internals.

`DatasetRuntime` is the developer-facing coordination boundary for live RDFLib
datasets shared by middleware components. It can be configured with a reasoner
specification when you want the runtime dataset to use the same RDFLib-backed
materialization behavior exposed by `rdflib-reasoning-engine`:

```python
from rdflib_reasoning.engine import RDFS_RETE_MATERIALIZED
from rdflib_reasoning.middleware import (
    DatasetMiddleware,
    DatasetMiddlewareConfig,
    DatasetRuntime,
)

runtime = DatasetRuntime(specification=RDFS_RETE_MATERIALIZED)

dataset_middleware = DatasetMiddleware(
    DatasetMiddlewareConfig(
        runtime=runtime,
        vocabulary_context=vocabulary_context,
    )
)
```

This keeps the Research Agent-facing `DatasetMiddleware` tool surface focused on
the default graph while allowing the runtime dataset itself to be backed by a
configured reasoner. Separate inference and proof tools remain part of the
planned inference middleware surface.

For generated API docs, see {doc}`../autoapi/middleware/index`.
