#!/usr/bin/env python3
"""
Generate INDEX.md and index-data.json from optimized.html for the OWL 2
RDF-Based Semantics spec.

This index focuses on the semantic-condition sections, their item-level anchors,
and the appendix/theorem anchors that are useful for cross-referencing OWL 2 RL
rules, optional RDFS support, and axiomatic triples.

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

SEMANTIC_CONDITIONS_ROOT_ID = "Semantic_Conditions"
SEMANTIC_SECTION_ID_RE = re.compile(r"^Semantic_Conditions_for_.+$")
SEMANTIC_ITEM_ID_RE = re.compile(r"^item-semcond-[a-z0-9-]+$")
TABLE_ID_RE = re.compile(r"^table-semcond-[a-z0-9-]+$")
AXIOMATIC_RDFS_ITEM_ID_RE = re.compile(r"^item-axiomatic-rdfs-[a-z0-9-]+$")

SPECIAL_SECTION_IDS = (
    "Appendix:_Axiomatic_Triples_.28Informative.29",
    "Axiomatic_Triples_in_RDF",
    "Axiomatic_Triples_for_the_Vocabulary_Classes",
    "Axiomatic_Triples_for_the_Vocabulary_Properties",
    "A_Set_of_Axiomatic_Triples",
    "Correspondence_Theorem",
    "Proof_for_the_Correspondence_Theorem",
)


class IdCollector(HTMLParser):
    """Collect relevant ids and section anchors in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.order = 0
        self.sections: list[tuple[int, str]] = []
        self.semantic_items: list[tuple[int, str]] = []
        self.axiomatic_rdfs_items: list[tuple[int, str]] = []
        self.tables: list[tuple[int, str]] = []
        self._seen_section: set[str] = set()
        self._seen_item: set[str] = set()
        self._seen_axiomatic_rdfs_item: set[str] = set()
        self._seen_table: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrd = dict(attrs)
        id_val = attrd.get("id")
        if not id_val:
            return
        self.order += 1

        if TABLE_ID_RE.match(id_val) and id_val not in self._seen_table:
            self._seen_table.add(id_val)
            self.tables.append((self.order, id_val))

        if SEMANTIC_ITEM_ID_RE.match(id_val) and id_val not in self._seen_item:
            self._seen_item.add(id_val)
            self.semantic_items.append((self.order, id_val))

        if (
            AXIOMATIC_RDFS_ITEM_ID_RE.match(id_val)
            and id_val not in self._seen_axiomatic_rdfs_item
        ):
            self._seen_axiomatic_rdfs_item.add(id_val)
            self.axiomatic_rdfs_items.append((self.order, id_val))

        name_val = attrd.get("name")
        if (
            name_val is not None
            and name_val == id_val
            and id_val not in self._seen_section
        ):
            self._seen_section.add(id_val)
            self.sections.append((self.order, id_val))


def offset_for_id(html: str, id_val: str) -> int | None:
    """Return the character offset where id_val first appears as an id attribute."""
    for pattern in (f'id="{id_val}"', f"id='{id_val}'"):
        idx = html.find(pattern)
        if idx != -1:
            return idx
    return None


def line_number_for_id(html: str, id_val: str) -> int | None:
    """Return the 1-based line number where id_val first appears as an id attribute."""
    off = offset_for_id(html, id_val)
    return (1 + html[:off].count("\n")) if off is not None else None


def line_range_for_row(html: str, id_val: str) -> tuple[int, int] | None:
    """Return the table-row span containing the given id, or None."""
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
    """Return the section span from its start until the next section anchor."""
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
    """Format line range for markdown index."""
    if start == end:
        return f" — line {start}"
    return f" — lines {start}–{end}"


def _line_range_payload(line_range: tuple[int, int] | None) -> dict[str, int] | None:
    """Convert an optional line range tuple into a JSON-friendly object."""
    if line_range is None:
        return None
    return {"start": line_range[0], "end": line_range[1]}


def _humanize_id(anchor_id: str) -> str:
    """Turn an anchor id into a readable label."""
    label = anchor_id.replace("_", " ")
    label = label.replace(".28", "(").replace(".29", ")")
    return label


def _semantic_item_group(item_id: str) -> str:
    """Extract the semantic-item group from item-semcond-<group>-... ids."""
    remainder = item_id.removeprefix("item-semcond-")
    return remainder.split("-", 1)[0]


def _axiomatic_rdfs_item_name(item_id: str) -> str:
    """Extract the short name from item-axiomatic-rdfs-<name> ids."""
    return item_id.removeprefix("item-axiomatic-rdfs-")


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate INDEX.md and index-data.json from optimized.html"
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

    target = "optimized.html"

    semantic_section_ids = [
        sid
        for _order, sid in collector.sections
        if sid == SEMANTIC_CONDITIONS_ROOT_ID or SEMANTIC_SECTION_ID_RE.match(sid)
    ]
    appendix_and_theorem_ids = [
        sid for _order, sid in collector.sections if sid in SPECIAL_SECTION_IDS
    ]

    semantic_sections_payload = []
    for sid in semantic_section_ids:
        section_line_range = line_range_for_section(section_start_lines, sid, last_line)
        semantic_sections_payload.append(
            {
                "id": sid,
                "label": _humanize_id(sid),
                "href": f"{target}#{sid}",
                "line_range": _line_range_payload(section_line_range),
            }
        )

    appendix_payload = []
    for sid in appendix_and_theorem_ids:
        section_line_range = line_range_for_section(section_start_lines, sid, last_line)
        appendix_payload.append(
            {
                "id": sid,
                "label": _humanize_id(sid),
                "href": f"{target}#{sid}",
                "line_range": _line_range_payload(section_line_range),
            }
        )

    semantic_items_payload = []
    for _order, item_id in collector.semantic_items:
        item_line_range = line_range_for_row(html, item_id)
        semantic_items_payload.append(
            {
                "id": item_id,
                "group": _semantic_item_group(item_id),
                "href": f"{target}#{item_id}",
                "line_range": _line_range_payload(item_line_range),
            }
        )

    axiomatic_rdfs_items_payload = []
    for _order, item_id in collector.axiomatic_rdfs_items:
        item_line_range = line_range_for_row(html, item_id)
        axiomatic_rdfs_items_payload.append(
            {
                "id": item_id,
                "name": _axiomatic_rdfs_item_name(item_id),
                "href": f"{target}#{item_id}",
                "line_range": _line_range_payload(item_line_range),
            }
        )

    table_payload = []
    for _order, table_id in collector.tables:
        table_line_range = line_range_for_row(html, table_id)
        table_payload.append(
            {
                "id": table_id,
                "label": _humanize_id(table_id),
                "href": f"{target}#{table_id}",
                "line_range": _line_range_payload(table_line_range),
            }
        )

    lines = [
        "# Index: OWL 2 RDF-Based Semantics (Development Agent- and script-oriented)",
        "",
        "This index supports navigation of the OWL 2 RDF-Based semantic-condition sections,",
        "item-level semantic condition anchors, and the appendix/theorem areas used by",
        "cross-reference tooling.",
        "",
        "## Semantic Condition Sections",
        "",
    ]

    for section in semantic_sections_payload:
        line_range = section["line_range"]
        suffix = (
            _range_suffix(line_range["start"], line_range["end"])
            if line_range is not None
            else ""
        )
        lines.append(f"- [{section['label']}]({section['href']}){suffix}")

    lines.extend(
        [
            "",
            "## Appendix And Theorem Sections",
            "",
        ]
    )
    for section in appendix_payload:
        line_range = section["line_range"]
        suffix = (
            _range_suffix(line_range["start"], line_range["end"])
            if line_range is not None
            else ""
        )
        lines.append(f"- [{section['label']}]({section['href']}){suffix}")

    lines.extend(
        [
            "",
            "## Semantic Condition Items",
            "",
        ]
    )
    for item in semantic_items_payload:
        line_range = item["line_range"]
        suffix = (
            _range_suffix(line_range["start"], line_range["end"])
            if line_range is not None
            else ""
        )
        lines.append(f"- [{item['id']}]({item['href']}){suffix}")

    lines.extend(
        [
            "",
            "## RDFS Axiomatic Triple Items",
            "",
        ]
    )
    for item in axiomatic_rdfs_items_payload:
        line_range = item["line_range"]
        suffix = (
            _range_suffix(line_range["start"], line_range["end"])
            if line_range is not None
            else ""
        )
        lines.append(f"- [{item['id']}]({item['href']}){suffix}")

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    args.json_output.resolve().parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "spec": {
            "name": "owl2-semantics-rdf",
            "title": "OWL 2 RDF-Based Semantics",
            "source_html": target,
            "generated_from": input_path.name,
        },
        "semantic_condition_sections": semantic_sections_payload,
        "appendix_and_theorem_sections": appendix_payload,
        "semantic_condition_items": semantic_items_payload,
        "semantic_condition_tables": table_payload,
        "axiomatic_rdfs_items": axiomatic_rdfs_items_payload,
    }
    args.json_output.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
