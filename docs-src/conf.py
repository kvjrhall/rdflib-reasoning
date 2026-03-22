"""Sphinx configuration for rdflib-reasoning."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "rdflib-reasoning-axioms" / "src"))
sys.path.insert(0, str(ROOT / "rdflib-reasoning-engine" / "src"))
sys.path.insert(0, str(ROOT / "rdflib-reasoning-middleware" / "src"))

project = "rdflib-reasoning"
copyright = "2026, rdflib-reasoning contributors"
author = "rdflib-reasoning contributors"

extensions = [
    "autoapi.extension",
    "myst_parser",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
html_theme = "alabaster"
html_static_path = ["_static"]

napoleon_google_docstring = True
napoleon_numpy_docstring = True

autoapi_type = "python"
autoapi_dirs = [
    str(ROOT / "src"),
    str(ROOT / "rdflib-reasoning-axioms" / "src"),
    str(ROOT / "rdflib-reasoning-engine" / "src"),
    str(ROOT / "rdflib-reasoning-middleware" / "src"),
]
autoapi_root = "autoapi"
autoapi_keep_files = True
autoapi_add_toctree_entry = False
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
}

linkcheck_ignore = [
    r"https://github\.com/.*/blob/main/.*",
]
linkcheck_anchors = True
linkcheck_timeout = 10
linkcheck_retries = 2
linkcheck_workers = 5

myst_heading_anchors = 3

os.environ.setdefault("SPHINX_BUILD", "1")


def _rewrite_autoapi_namespace_refs(app, docname, source) -> None:
    """Normalize namespace-package references to AutoAPI's rendered module paths."""
    if not docname.startswith("autoapi/"):
        return

    source[0] = source[0].replace("rdflib_reasoning.", "")


def setup(app) -> None:
    app.connect("source-read", _rewrite_autoapi_namespace_refs)
