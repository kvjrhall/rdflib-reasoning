#!/usr/bin/env python3
"""
Generate INDEX.md from optimized.html for the RDF 1.1 Semantics spec.

Indexes the RDFS entailment section and RDFS entailment rules (rdfs1–rdfs13)
by name. Reads only optimized.html; emits links solely to optimized.html.
Re-run after re-normalizing the spec.

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

RDFS_ENTAILMENT_SECTION_ID = "rdfs-entailment"
RDFS_PATTERNS_ID = "rdfs_patterns"
NEXT_SECTION_AFTER_RDFS_ENTAILMENT_ID = "rdf-datasets"
# Rule ids: dfn-rdfs1, dfn-rdfs2, ..., dfn-rdfs4a, dfn-rdfs4b, ..., dfn-rdfs13
RULE_ID_RE = re.compile(r"^dfn-rdfs[0-9]+[ab]?$")


class IdCollector(HTMLParser):
    """Collect rule ids (dfn-rdfs*) in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.order = 0
        self.rules: list[tuple[int, str]] = []
        self._seen_rule: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrd = dict(attrs)
        id_val = attrd.get("id")
        if not id_val:
            return
        self.order += 1
        if RULE_ID_RE.match(id_val) and id_val not in self._seen_rule:
            self._seen_rule.add(id_val)
            self.rules.append((self.order, id_val))


def rule_id_to_label(anchor_id: str) -> str:
    """Turn dfn-rdfs1 -> rdfs1, dfn-rdfs4a -> rdfs4a."""
    if anchor_id.startswith("dfn-"):
        return anchor_id[4:]
    return anchor_id


def offset_for_id(html: str, id_val: str) -> int | None:
    """Return the character offset where id_val first appears as an id attribute, or None."""
    for pattern in (f'id="{id_val}"', f"id='{id_val}'"):
        idx = html.find(pattern)
        if idx != -1:
            return idx
    return None


def line_number_for_id(html: str, id_val: str) -> int | None:
    """Return the 1-based line number where id_val first appears as an id attribute, or None."""
    off = offset_for_id(html, id_val)
    return (1 + html[:off].count("\n")) if off is not None else None


def line_range_for_row(html: str, id_val: str) -> tuple[int, int] | None:
    """Return (start_line, end_line) for the table row containing the id, or None."""
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
        description="Generate INDEX.md from optimized.html (RDFS entailment rules)"
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

    target = "optimized.html"

    lines = [
        "# Index: RDF 1.1 Semantics — RDFS entailment rules (agent-oriented)",
        "",
        "This index supports assessing coverage and correctness of RDFS entailment. "
        "All links target `docs/specs/rdf11-semantics/optimized.html`. "
        "Rules rdfs1–rdfs13 are in the RDFS entailment section (Patterns of RDFS entailment).",
        "",
        "## RDFS entailment",
        "",
    ]

    # Section: RDFS entailment (with line range up to next section)
    start_line = line_number_for_id(html, RDFS_ENTAILMENT_SECTION_ID)
    end_line = line_number_for_id(html, NEXT_SECTION_AFTER_RDFS_ENTAILMENT_ID)
    if start_line is not None and end_line is not None:
        suffix = _range_suffix(start_line, end_line - 1)
    elif start_line is not None:
        suffix = _range_suffix(start_line, start_line)
    else:
        suffix = ""
    lines.append(f"- [RDFS entailment]({target}#{RDFS_ENTAILMENT_SECTION_ID}){suffix}")
    lines.append("")

    # Patterns subsection
    patterns_line = line_number_for_id(html, RDFS_PATTERNS_ID)
    if patterns_line is not None:
        suffix = _range_suffix(patterns_line, patterns_line)
        lines.append(
            f"- [Patterns of RDFS entailment]({target}#{RDFS_PATTERNS_ID}){suffix}"
        )
        lines.append("")

    lines.append("## Rules (by name)")
    lines.append("")

    rules_payload: list[dict[str, object]] = []
    for _order, rule_id in collector.rules:
        r = line_range_for_row(html, rule_id)
        suffix = _range_suffix(r[0], r[1]) if r is not None else ""
        label = rule_id_to_label(rule_id)
        lines.append(f"- [{label}]({target}#{rule_id}){suffix}")
        rules_payload.append(
            {
                "id": label,
                "anchor_id": rule_id,
                "href": f"{target}#{rule_id}",
                "line_range": _line_range_payload(r),
            }
        )

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.json_output.resolve().parent.mkdir(parents=True, exist_ok=True)

    rdfs_entailment_range = None
    if start_line is not None and end_line is not None:
        rdfs_entailment_range = (start_line, end_line - 1)
    elif start_line is not None:
        rdfs_entailment_range = (start_line, start_line)

    patterns_range = (
        (patterns_line, patterns_line) if patterns_line is not None else None
    )
    json_payload = {
        "spec": {
            "name": "rdf11-semantics",
            "title": "RDF 1.1 Semantics",
            "source_html": target,
            "generated_from": input_path.name,
        },
        "sections": [
            {
                "id": RDFS_ENTAILMENT_SECTION_ID,
                "label": "RDFS entailment",
                "href": f"{target}#{RDFS_ENTAILMENT_SECTION_ID}",
                "line_range": _line_range_payload(rdfs_entailment_range),
            },
            {
                "id": RDFS_PATTERNS_ID,
                "label": "Patterns of RDFS entailment",
                "href": f"{target}#{RDFS_PATTERNS_ID}",
                "line_range": _line_range_payload(patterns_range),
            },
        ],
        "rules": rules_payload,
    }
    args.json_output.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
