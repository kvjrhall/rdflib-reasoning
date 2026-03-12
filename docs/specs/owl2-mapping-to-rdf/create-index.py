#!/usr/bin/env python3
"""
Generate INDEX.md from optimized.html for the OWL 2 Mapping to RDF spec.

Reads only optimized.html; emits a Development Agent- and script-oriented index with links solely to
optimized.html. Re-run after re-normalizing the spec (e.g. after w3c-normalize.py).

Usage:
  python create-index.py [--input PATH] [--output PATH] [--json-output PATH]

Defaults: input=optimized.html, output=INDEX.md, json-output=index-data.json,
all in the script's directory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Construct ids: a_ followed by alphanumeric (e.g. a_SubClassOf, a_DeclarationClass)
CONSTRUCT_ID_RE = re.compile(r"^a_[A-Za-z0-9]+$")


class IdCollector(HTMLParser):
    """Collect id and name attributes in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.order = 0
        self.constructs: list[tuple[int, str]] = []  # (order, id)
        self.sections: list[tuple[int, str]] = []  # (order, id)
        self._seen_construct: set[str] = set()
        self._seen_section: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrd = dict(attrs)
        id_val = attrd.get("id")
        if not id_val:
            return
        self.order += 1
        if CONSTRUCT_ID_RE.match(id_val):
            if id_val not in self._seen_construct:
                self._seen_construct.add(id_val)
                self.constructs.append((self.order, id_val))
        name_val = attrd.get("name")
        if (
            name_val is not None
            and name_val == id_val
            and id_val not in self._seen_section
        ):
            self._seen_section.add(id_val)
            self.sections.append((self.order, id_val))


def id_to_label(anchor_id: str) -> str:
    """Turn an anchor id into a human-readable label (e.g. Parsing_of_Axioms -> Parsing of Axioms)."""
    return anchor_id.replace("_", " ")


def offset_for_id(html: str, id_val: str) -> int | None:
    """Return the character offset where id_val first appears as an id attribute, or None."""
    for pattern in (f'id="{re.escape(id_val)}"', f"id='{re.escape(id_val)}'"):
        idx = html.find(pattern)
        if idx != -1:
            return idx
    return None


def line_number_for_id(html: str, id_val: str) -> int | None:
    """Return the 1-based line number where id_val first appears as an id attribute, or None."""
    off = offset_for_id(html, id_val)
    return (1 + html[:off].count("\n")) if off is not None else None


def line_range_for_construct(html: str, id_val: str) -> tuple[int, int] | None:
    """Return (start_line, end_line) for the table row containing the construct id, or None."""
    start_off = offset_for_id(html, id_val)
    if start_off is None:
        return None
    start_line = 1 + html[:start_off].count("\n")
    end_tr = html.find("</tr>", start_off)
    if end_tr == -1:
        return (start_line, start_line)
    end_off = end_tr + 5
    end_line = 1 + html[:end_off].count("\n")
    return (start_line, end_line)


def line_range_for_section(
    section_start_lines: list[tuple[str, int | None]],
    id_val: str,
    last_line: int,
) -> tuple[int, int] | None:
    """Return (start_line, end_line) for the section; end is next section start - 1 or last_line."""
    index_by_id = {sid: i for i, (sid, _) in enumerate(section_start_lines)}
    if id_val not in index_by_id:
        return None
    i = index_by_id[id_val]
    start_line = section_start_lines[i][1]
    if start_line is None:
        return None
    for j in range(i + 1, len(section_start_lines)):
        next_start = section_start_lines[j][1]
        if next_start is not None:
            return (start_line, next_start - 1)
    return (start_line, last_line)


def _range_suffix(start: int, end: int) -> str:
    """Format line range for index: ' — lines N–M' or ' — line N'."""
    if start == end:
        return f" — line {start}"
    return f" — lines {start}–{end}"


def _line_range_payload(line_range: tuple[int, int] | None) -> dict[str, int] | None:
    """Convert an optional line range tuple into a JSON-friendly object."""
    if line_range is None:
        return None
    return {"start": line_range[0], "end": line_range[1]}


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate INDEX.md from optimized.html"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "optimized.html",
        help="Path to optimized.html",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "INDEX.md",
        help="Path to write INDEX.md",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=script_dir / "index-data.json",
        help="Path to write index-data.json",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    if not input_path.is_file():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    html = input_path.read_text(encoding="utf-8", errors="replace")
    collector = IdCollector()
    collector.feed(html)

    last_line = len(html.splitlines())
    section_start_lines = [
        (sid, line_number_for_id(html, sid)) for _order, sid in collector.sections
    ]

    # Build markdown; all links point to optimized.html (basename for same-directory links)
    target = "optimized.html"

    lines = [
        "# Index: OWL 2 Mapping to RDF (Development Agent- and script-oriented)",
        "",
        "This index supports bidirectional navigation of the OWL 2 ↔ RDF mapping. "
        "All links target `docs/specs/owl2-mapping-to-rdf/optimized.html`. "
        "Section 2 = structural specification → RDF; Section 3 = RDF → structural specification.",
        "",
        "## OWL → RDF (Section 2) — by construct",
        "",
    ]
    constructs_payload: list[dict[str, object]] = []
    for _order, cid in collector.constructs:
        display = cid[2:] if cid.startswith("a_") else cid  # strip a_ prefix
        r = line_range_for_construct(html, cid)
        suffix = _range_suffix(r[0], r[1]) if r is not None else ""
        lines.append(f"- [{display}]({target}#{cid}){suffix}")
        constructs_payload.append(
            {
                "id": display,
                "anchor_id": cid,
                "href": f"{target}#{cid}",
                "line_range": _line_range_payload(r),
            }
        )
    lines.append("")
    lines.append("## Document sections")
    lines.append("")
    sections_payload: list[dict[str, object]] = []
    for _order, sid in collector.sections:
        label = id_to_label(sid)
        r = line_range_for_section(section_start_lines, sid, last_line)
        suffix = _range_suffix(r[0], r[1]) if r is not None else ""
        lines.append(f"- [{label}]({target}#{sid}){suffix}")
        sections_payload.append(
            {
                "id": sid,
                "label": label,
                "href": f"{target}#{sid}",
                "line_range": _line_range_payload(r),
            }
        )

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.json_output.resolve().parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "spec": {
            "name": "owl2-mapping-to-rdf",
            "title": "OWL 2 Mapping to RDF",
            "source_html": target,
            "generated_from": input_path.name,
        },
        "constructs": constructs_payload,
        "sections": sections_payload,
    }
    args.json_output.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
