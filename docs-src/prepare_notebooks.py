"""Prepare selected notebooks for Sphinx rendering."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import nbformat

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "notebooks"
TARGET_DIR = ROOT / "docs-src" / "tutorials" / "notebooks"
GITHUB_BLOB_MAIN = "https://github.com/kvjrhall/rdflib-reasoning/blob/main"

NOTEBOOKS = (
    "demo-rdfs-inference.ipynb",
    "demo-owl2-rl-inference.ipynb",
    "demo-rdfs-retraction.ipynb",
    "demo-contradiction-rules.ipynb",
    "demo-proof-reconstructor.ipynb",
)

MARKDOWN_LINK_RE = re.compile(
    r"(?P<prefix>\[[^\]]+\]\()(?P<target>[^)#][^)#]*)(?P<suffix>(?:#[^)]*)?\))"
)


def _is_external_link(target: str) -> bool:
    parsed = urlsplit(target)
    return bool(parsed.scheme or parsed.netloc)


def _rewrite_markdown_links(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match.group("target")
        if _is_external_link(target):
            return match.group(0)

        if target in NOTEBOOKS:
            new_target = target
        elif target.startswith("./") and target[2:] in NOTEBOOKS:
            new_target = target[2:]
        elif target.endswith(".ipynb"):
            new_target = f"{GITHUB_BLOB_MAIN}/notebooks/{Path(target).name}"
        elif target.startswith(("./", "../")):
            repo_path = (SOURCE_DIR / target).resolve().relative_to(ROOT)
            new_target = f"{GITHUB_BLOB_MAIN}/{repo_path.as_posix()}"
        else:
            new_target = target

        return f"{match.group('prefix')}{new_target}{match.group('suffix')}"

    return MARKDOWN_LINK_RE.sub(replace, text)


def main() -> None:
    """Copy tutorial notebooks into ``docs-src/tutorials/notebooks`` with link rewrites."""
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for name in NOTEBOOKS:
        source = SOURCE_DIR / name
        target = TARGET_DIR / name
        notebook = nbformat.read(source, as_version=4)

        for cell in notebook.cells:
            if cell.cell_type == "markdown":
                cell.source = _rewrite_markdown_links(str(cell.source))

        nbformat.write(notebook, target)


if __name__ == "__main__":
    main()
