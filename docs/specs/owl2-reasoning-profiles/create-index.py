#!/usr/bin/env python3
"""
Generate INDEX.md from optimized.html for the OWL 2 Reasoning Profiles spec.

Indexes Section 4.3 "Reasoning in OWL 2 RL and RDF Graphs using Rules" and all
OWL 2 RL rules by name. Also adds cross-references into the OWL 2 RDF-Based
Semantics spec so a Development Agent can move from the operational rules to
their normative semantic foundation. Re-run after re-normalizing the spec.

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

SECTION_4_3_ID = "Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules"
SECTION_4_3_LABEL = "Reasoning in OWL 2 RL and RDF Graphs using Rules"
# Rule ids: eq-*, prp-*, cls-*, cax-*, dt-*, scm-* (OWL 2 RL rules in Section 4.3)
RULE_ID_RE = re.compile(r"^(eq|prp|cls|cax|dt|scm)-[a-z0-9-]+$")
RULE_FAMILY_ORDER = ("eq", "prp", "cls", "cax", "dt", "scm")
SEMANTICS_TARGET = "../owl2-semantics-rdf/optimized.html"
SEMANTIC_FOUNDATION_CROSS_REFERENCES = [
    {
        "label": "OWL 2 RDF-Based semantic conditions (Section 5)",
        "href": f"{SEMANTICS_TARGET}#Semantic_Conditions",
        "kind": "primary_foundation",
        "notes": "Primary normative foundation for the RL/RDF rules.",
    },
    {
        "label": "Axiomatic triples appendix",
        "href": f"{SEMANTICS_TARGET}#Appendix:_Axiomatic_Triples_.28Informative.29",
        "kind": "axiomatic_triples",
        "notes": (
            "Useful when a rule appears to rely on implicit vocabulary facts "
            "that are omitted from RL for implementation efficiency."
        ),
    },
]
RULE_FAMILY_SEMANTICS = {
    "eq": [
        {
            "label": "Semantic Conditions for Equivalence and Disjointness",
            "anchor": "Semantic_Conditions_for_Equivalence_and_Disjointness",
        }
    ],
    "prp": [
        {
            "label": "Semantic Conditions for the Vocabulary Properties",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Properties",
        },
        {
            "label": "Semantic Conditions for Sub Property Chains",
            "anchor": "Semantic_Conditions_for_Sub_Property_Chains",
        },
        {
            "label": "Semantic Conditions for Inverse Properties",
            "anchor": "Semantic_Conditions_for_Inverse_Properties",
        },
        {
            "label": "Semantic Conditions for Property Characteristics",
            "anchor": "Semantic_Conditions_for_Property_Characteristics",
        },
        {
            "label": "Semantic Conditions for Keys",
            "anchor": "Semantic_Conditions_for_Keys",
        },
        {
            "label": "Semantic Conditions for Negative Property Assertions",
            "anchor": "Semantic_Conditions_for_Negative_Property_Assertions",
        },
    ],
    "cls": [
        {
            "label": "Semantic Conditions for the Vocabulary Classes",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Classes",
        },
        {
            "label": "Semantic Conditions for Boolean Connectives",
            "anchor": "Semantic_Conditions_for_Boolean_Connectives",
        },
        {
            "label": "Semantic Conditions for Enumerations",
            "anchor": "Semantic_Conditions_for_Enumerations",
        },
        {
            "label": "Semantic Conditions for Property Restrictions",
            "anchor": "Semantic_Conditions_for_Property_Restrictions",
        },
    ],
    "cax": [
        {
            "label": "Semantic Conditions for the RDFS Vocabulary",
            "anchor": "Semantic_Conditions_for_the_RDFS_Vocabulary",
        },
        {
            "label": "Semantic Conditions for Equivalence and Disjointness",
            "anchor": "Semantic_Conditions_for_Equivalence_and_Disjointness",
        },
        {
            "label": "Semantic Conditions for N-ary Disjointness",
            "anchor": "Semantic_Conditions_for_N-ary_Disjointness",
        },
    ],
    "dt": [
        {
            "label": "Semantic Conditions for Datatype Restrictions",
            "anchor": "Semantic_Conditions_for_Datatype_Restrictions",
        },
        {
            "label": "Semantic Conditions for the Vocabulary Classes",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Classes",
        },
        {
            "label": "Semantic Conditions for the Vocabulary Properties",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Properties",
        },
    ],
    "scm": [
        {
            "label": "Semantic Conditions for the Vocabulary Classes",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Classes",
        },
        {
            "label": "Semantic Conditions for the Vocabulary Properties",
            "anchor": "Semantic_Conditions_for_the_Vocabulary_Properties",
        },
        {
            "label": "Semantic Conditions for the RDFS Vocabulary",
            "anchor": "Semantic_Conditions_for_the_RDFS_Vocabulary",
        },
        {
            "label": "Semantic Conditions for Sub Property Chains",
            "anchor": "Semantic_Conditions_for_Sub_Property_Chains",
        },
    ],
}


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


def _line_range_payload(line_range: tuple[int, int] | None) -> dict[str, int] | None:
    """Convert an optional line range tuple into a JSON-friendly object."""
    if line_range is None:
        return None
    return {"start": line_range[0], "end": line_range[1]}


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

    lines = [
        "# Index: OWL 2 RL Rules (Section 4.3) — Development Agent- and script-oriented",
        "",
        "This index supports assessing coverage and correctness of the OWL 2 RL profile. "
        "All links target `docs/specs/owl2-reasoning-profiles/optimized.html`. "
        'Rules are in Section 4.3 "Reasoning in OWL 2 RL and RDF Graphs using Rules". '
        "Fetch rules by name using the list below. Rule name prefixes: eq, prp, cls, cax, dt, scm.",
        "",
        "Use this index in two passes:",
        "",
        "1. Use the rule anchor in `owl2-reasoning-profiles` when you need the executable RL/RDF rule form used by the engine design.",
        "2. Follow the semantics cross-reference when you need the normative semantic condition or axiomatic-triple basis that motivates the rule.",
        "",
        "Section 4.3 explicitly presents the OWL 2 RL/RDF rules as a partial axiomatization of the OWL 2 RDF-Based Semantics, rather than as a self-justifying naming scheme for structural axioms.",
        "",
        "## Semantic Foundation Cross-Reference",
        "",
        f"- [OWL 2 RDF-Based semantic conditions (Section 5)]({SEMANTICS_TARGET}#Semantic_Conditions) — primary normative foundation for the RL/RDF rules.",
        f"- [Axiomatic triples appendix]({SEMANTICS_TARGET}#Appendix:_Axiomatic_Triples_.28Informative.29) — useful when a rule appears to rely on implicit vocabulary facts that are omitted from RL for implementation efficiency.",
        "",
        "Rule-family starting points in `owl2-semantics-rdf`:",
        "",
        f"- `eq-*` -> [Semantic Conditions for Equivalence and Disjointness]({SEMANTICS_TARGET}#Semantic_Conditions_for_Equivalence_and_Disjointness)",
        f"- `prp-*` -> [Semantic Conditions for the Vocabulary Properties]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Properties), [Semantic Conditions for Sub Property Chains]({SEMANTICS_TARGET}#Semantic_Conditions_for_Sub_Property_Chains), [Semantic Conditions for Inverse Properties]({SEMANTICS_TARGET}#Semantic_Conditions_for_Inverse_Properties), [Semantic Conditions for Property Characteristics]({SEMANTICS_TARGET}#Semantic_Conditions_for_Property_Characteristics), [Semantic Conditions for Keys]({SEMANTICS_TARGET}#Semantic_Conditions_for_Keys), [Semantic Conditions for Negative Property Assertions]({SEMANTICS_TARGET}#Semantic_Conditions_for_Negative_Property_Assertions)",
        f"- `cls-*` -> [Semantic Conditions for the Vocabulary Classes]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Classes), [Semantic Conditions for Boolean Connectives]({SEMANTICS_TARGET}#Semantic_Conditions_for_Boolean_Connectives), [Semantic Conditions for Enumerations]({SEMANTICS_TARGET}#Semantic_Conditions_for_Enumerations), [Semantic Conditions for Property Restrictions]({SEMANTICS_TARGET}#Semantic_Conditions_for_Property_Restrictions)",
        f"- `cax-*` -> [Semantic Conditions for the RDFS Vocabulary]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_RDFS_Vocabulary), [Semantic Conditions for Equivalence and Disjointness]({SEMANTICS_TARGET}#Semantic_Conditions_for_Equivalence_and_Disjointness), [Semantic Conditions for N-ary Disjointness]({SEMANTICS_TARGET}#Semantic_Conditions_for_N-ary_Disjointness)",
        f"- `dt-*` -> [Semantic Conditions for Datatype Restrictions]({SEMANTICS_TARGET}#Semantic_Conditions_for_Datatype_Restrictions), [Semantic Conditions for the Vocabulary Classes]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Classes), [Semantic Conditions for the Vocabulary Properties]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Properties)",
        f"- `scm-*` -> [Semantic Conditions for the Vocabulary Classes]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Classes), [Semantic Conditions for the Vocabulary Properties]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_Vocabulary_Properties), [Semantic Conditions for the RDFS Vocabulary]({SEMANTICS_TARGET}#Semantic_Conditions_for_the_RDFS_Vocabulary), [Semantic Conditions for Sub Property Chains]({SEMANTICS_TARGET}#Semantic_Conditions_for_Sub_Property_Chains)",
        "",
        "## Section 4.3",
        "",
    ]

    # Section 4.3 entry
    section_line_range = line_range_for_section(
        section_start_lines, SECTION_4_3_ID, last_line
    )
    label = SECTION_4_3_LABEL
    suffix = (
        _range_suffix(section_line_range[0], section_line_range[1])
        if section_line_range is not None
        else ""
    )
    lines.append(f"- [{label}]({target}#{SECTION_4_3_ID}){suffix}")
    lines.append("")
    lines.append("## Rules (by name)")
    lines.append("")

    rules_payload: list[dict[str, object]] = []
    for _order, rule_id in collector.rules:
        rule_line_range = line_range_for_row(html, rule_id)
        suffix = (
            _range_suffix(rule_line_range[0], rule_line_range[1])
            if rule_line_range is not None
            else ""
        )
        lines.append(f"- [{rule_id}]({target}#{rule_id}){suffix}")
        rules_payload.append(
            {
                "id": rule_id,
                "family": rule_id.split("-", 1)[0],
                "href": f"{target}#{rule_id}",
                "line_range": _line_range_payload(rule_line_range),
            }
        )

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.json_output.resolve().parent.mkdir(parents=True, exist_ok=True)

    family_cross_references = []
    for family in RULE_FAMILY_ORDER:
        semantic_sections = []
        for item in RULE_FAMILY_SEMANTICS[family]:
            semantic_sections.append(
                {
                    **item,
                    "href": f"{SEMANTICS_TARGET}#{item['anchor']}",
                }
            )
        family_cross_references.append(
            {
                "family": family,
                "semantic_sections": semantic_sections,
            }
        )

    json_payload = {
        "spec": {
            "name": "owl2-reasoning-profiles",
            "title": "OWL 2 RL Rules (Section 4.3)",
            "source_html": target,
            "generated_from": input_path.name,
        },
        "section": {
            "id": SECTION_4_3_ID,
            "label": SECTION_4_3_LABEL,
            "href": f"{target}#{SECTION_4_3_ID}",
            "line_range": _line_range_payload(section_line_range),
        },
        "rule_families": family_cross_references,
        "semantic_foundation_cross_references": SEMANTIC_FOUNDATION_CROSS_REFERENCES,
        "rules": rules_payload,
    }
    args.json_output.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
