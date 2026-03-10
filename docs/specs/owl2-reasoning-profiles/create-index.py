#!/usr/bin/env python3
"""
Generate INDEX.md from optimized.html for the OWL 2 Reasoning Profiles spec.

Indexes Section 4.3 "Reasoning in OWL 2 RL and RDF Graphs using Rules" and all
OWL 2 RL rules by name. Reads only optimized.html; emits links solely to
optimized.html. Re-run after re-normalizing the spec.

Usage:
  python create-index.py [--input PATH] [--output PATH]

Defaults: input=optimized.html, output=INDEX.md, both in the script's directory.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SECTION_4_3_ID = "Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules"
# Rule ids: eq-*, prp-*, cls-*, cax-*, dt-*, scm-* (OWL 2 RL rules in Section 4.3)
RULE_ID_RE = re.compile(r"^(eq|prp|cls|cax|dt|scm)-[a-z0-9-]+$")


class IdCollector(HTMLParser):
    """Collect section anchors (id= name=) and rule ids in document order."""

    def __init__(self) -> None:
        super().__init__()
        self.order = 0
        self.sections: list[tuple[int, str]] = []
        self.rules: list[tuple[int, str]] = []
        self._seen_section: set[str] = set()
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
        name_val = attrd.get("name")
        if (
            name_val is not None
            and name_val == id_val
            and id_val not in self._seen_section
        ):
            self._seen_section.add(id_val)
            self.sections.append((self.order, id_val))


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


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate INDEX.md from optimized.html (Section 4.3 and OWL 2 RL rules)"
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

    lines = [
        "# Index: OWL 2 RL Rules (Section 4.3) — Development Agent- and script-oriented",
        "",
        "This index supports assessing coverage and correctness of the OWL 2 RL profile. "
        "All links target `optimized.html`. "
        'Rules are in Section 4.3 "Reasoning in OWL 2 RL and RDF Graphs using Rules". '
        "Fetch rules by name using the list below. Rule name prefixes: eq, prp, cls, cax, dt, scm.",
        "",
        "## Section 4.3",
        "",
    ]

    # Section 4.3 entry
    r = line_range_for_section(section_start_lines, SECTION_4_3_ID, last_line)
    label = "Reasoning in OWL 2 RL and RDF Graphs using Rules"
    suffix = _range_suffix(r[0], r[1]) if r is not None else ""
    lines.append(f"- [{label}]({target}#{SECTION_4_3_ID}){suffix}")
    lines.append("")
    lines.append("## Rules (by name)")
    lines.append("")

    for _order, rule_id in collector.rules:
        r = line_range_for_row(html, rule_id)
        suffix = _range_suffix(r[0], r[1]) if r is not None else ""
        lines.append(f"- [{rule_id}]({target}#{rule_id}){suffix}")

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
