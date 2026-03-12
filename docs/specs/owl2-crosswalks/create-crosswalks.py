#!/usr/bin/env python3
"""
Generate crosswalk artifacts from spec-local index-data.json files.

The initial implementation builds Table 1:
  OWL 2 RL Rule <-> RDF-Based Semantics Section

Usage:
  python create-crosswalks.py
    [--rl-index-data PATH]
    [--mapping-index-data PATH]
    [--semantics-index-data PATH]
    [--rdfs-index-data PATH]
    [--master-seed PATH]
    [--output PATH]
    [--json-output PATH]

Defaults place all outputs in this script's directory.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

OPTIONAL_RDFS_SUPPORT_RULES = {
    "rdfs1": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs2": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs3": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs4a": [
        "Semantic_Conditions_for_the_Parts_of_the_Universe",
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs4b": [
        "Semantic_Conditions_for_the_Parts_of_the_Universe",
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs5": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
        "Semantic_Conditions_for_Sub_Property_Chains",
    ],
    "rdfs6": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs7": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
        "Semantic_Conditions_for_Sub_Property_Chains",
    ],
    "rdfs8": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs9": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs10": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs11": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs12": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
    "rdfs13": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_Datatype_Restrictions",
        "Semantic_Conditions_for_the_RDFS_Vocabulary",
    ],
}

RDFS_AXIOMATIC_TRIPLE_SECTION_MAP = {
    "item-axiomatic-rdfs-class": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
    ],
    "item-axiomatic-rdfs-comment": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
    ],
    "item-axiomatic-rdfs-datatype": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_Datatype_Restrictions",
    ],
    "item-axiomatic-rdfs-isdefinedby": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
    ],
    "item-axiomatic-rdfs-label": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
    ],
    "item-axiomatic-rdfs-literal": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_Datatype_Restrictions",
    ],
    "item-axiomatic-rdfs-property": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_Vocabulary_Properties",
    ],
    "item-axiomatic-rdfs-resource": [
        "Semantic_Conditions_for_the_Vocabulary_Classes",
        "Semantic_Conditions_for_the_Parts_of_the_Universe",
    ],
    "item-axiomatic-rdfs-seealso": [
        "Semantic_Conditions_for_the_Vocabulary_Properties",
    ],
}

TABLE_DEFINITIONS = [
    {
        "key": "table_1",
        "title": "Table 1: OWL 2 RL Rule <-> RDF-Based Semantics Section",
        "data_heading": "Table 1: Data",
        "summary_lines": [
            "Use this table to move directly from an operational RL rule to the",
            "normative RDF-Based semantic-condition section that motivates it.",
            "The current join is family-level: every RL rule inherits the semantic",
            "sections associated with its rule family in",
            "`owl2-reasoning-profiles/index-data.json`.",
        ],
        "columns": [
            "RDF-Based Semantics Section",
            "Semantics HTML Anchor",
            "Semantics HTML Lines",
            "OWL 2 RL Rule",
            "OWL 2 RL HTML Anchor",
            "OWL 2 RL Lines",
            "Rule Family",
        ],
    },
    {
        "key": "table_2",
        "title": "Table 2: Optional RDFS Support Rule <-> RDF-Based Semantics Section",
        "data_heading": "Table 2: Data",
        "summary_lines": [
            "Use this table when an implementation needs background RDFS entailment",
            "support that the OWL 2 RL/RDF rules may omit. These rows are curated",
            "support relationships, not theorem-level equivalences.",
        ],
        "columns": [
            "RDF-Based Semantics Section",
            "Semantics HTML Anchor",
            "Semantics HTML Lines",
            "Optional RDFS Support Rule",
            "Optional RDFS Support HTML Anchor",
            "Optional RDFS Support Lines",
        ],
    },
    {
        "key": "table_3",
        "title": "Table 3: RDFS Axiomatic Triple <-> RDF-Based Semantics Section",
        "data_heading": "Table 3: Data",
        "summary_lines": [
            "Use this table to identify silent or background RDFS axiomatic triples",
            "that correspond to RDF-Based semantic-condition areas. These rows are",
            "curated retrieval guidance for implementation work.",
        ],
        "columns": [
            "RDF-Based Semantics Section",
            "Semantics HTML Anchor",
            "Semantics HTML Lines",
            "RDFS Axiomatic Triple",
            "RDFS Axiomatic Triple HTML Anchor",
            "RDFS Axiomatic Triple Lines",
        ],
    },
    {
        "key": "table_4",
        "title": "Table 4: StructuralElement-Oriented Master Crosswalk",
        "data_heading": "Table 4: Data",
        "summary_lines": [
            "Use this master table when moving from triple-oriented reasoner traces",
            "toward proof objects expressed as StructuralElement-compatible axioms.",
            "The row key is the OWL structural construct / StructuralElement target,",
            "so related mapping, semantics, and operational references stay co-located.",
        ],
        "columns": [
            "StructuralElement Subtype",
            "OWL Structural Construct",
            "Mapping To RDF Anchor",
            "RDF-Based Semantics",
            "Direct Semantics",
            "OWL 2 RL Rules",
            "Optional RDFS Support",
            "RDFS Axiomatic Triples",
            "Implementation Status",
            "Reconstruction Note",
        ],
    },
]


def load_json(path: Path) -> dict:
    """Load JSON data from a file path."""
    if not path.is_file():
        raise FileNotFoundError(f"input file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def line_range_text(line_range: dict[str, int] | None) -> str:
    """Format a JSON line range object as N-M text."""
    if line_range is None:
        return ""
    return f"{line_range['start']}-{line_range['end']}"


def md_escape(value: object) -> str:
    """Escape markdown table cell content."""
    return str(value).replace("|", "\\|")


def github_heading_slug(heading: str) -> str:
    """Approximate the GitHub markdown heading slug for a heading string."""
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def render_markdown_table(headers: list[str], rows: list[list[object]]) -> list[str]:
    """Render a markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["----"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(value) for value in row) + " |")
    return lines


def find_heading_line_numbers(lines: list[str], headings: list[str]) -> dict[str, int]:
    """Find 1-based line numbers for the given headings in the rendered markdown."""
    heading_lines = {f"### {heading}": heading for heading in headings}
    result: dict[str, int] = {}
    for index, line in enumerate(lines, start=1):
        heading = heading_lines.get(line)
        if heading is not None and heading not in result:
            result[heading] = index
    return result


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Generate crosswalk tables from spec-local index-data.json files"
    )
    parser.add_argument(
        "--rl-index-data",
        type=Path,
        default=script_dir.parent / "owl2-reasoning-profiles" / "index-data.json",
        help="Path to owl2-reasoning-profiles/index-data.json",
    )
    parser.add_argument(
        "--mapping-index-data",
        type=Path,
        default=script_dir.parent / "owl2-mapping-to-rdf" / "index-data.json",
        help="Path to owl2-mapping-to-rdf/index-data.json",
    )
    parser.add_argument(
        "--semantics-index-data",
        type=Path,
        default=script_dir.parent / "owl2-semantics-rdf" / "index-data.json",
        help="Path to owl2-semantics-rdf/index-data.json",
    )
    parser.add_argument(
        "--rdfs-index-data",
        type=Path,
        default=script_dir.parent / "rdf11-semantics" / "index-data.json",
        help="Path to rdf11-semantics/index-data.json",
    )
    parser.add_argument(
        "--master-seed",
        type=Path,
        default=script_dir / "master-table-seed.json",
        help="Path to the curated master-table seed JSON",
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
        default=script_dir / "crosswalk-data.json",
        help="Path to write machine-readable crosswalk data",
    )
    args = parser.parse_args()

    try:
        rl_data = load_json(args.rl_index_data.resolve())
        mapping_data = load_json(args.mapping_index_data.resolve())
        semantics_data = load_json(args.semantics_index_data.resolve())
        rdfs_data = load_json(args.rdfs_index_data.resolve())
        master_seed = load_json(args.master_seed.resolve())
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    mapping_constructs_by_id = {
        construct["id"]: construct for construct in mapping_data["constructs"]
    }
    semantics_by_id = {
        section["id"]: section
        for section in semantics_data["semantic_condition_sections"]
    }
    rdfs_rules_by_id = {rule["id"]: rule for rule in rdfs_data["rules"]}
    rl_rules_by_id = {rule["id"]: rule for rule in rl_data["rules"]}
    axiomatic_rdfs_items_by_id = {
        item["id"]: item for item in semantics_data.get("axiomatic_rdfs_items", [])
    }
    family_to_sections = {
        family["family"]: family["semantic_sections"]
        for family in rl_data["rule_families"]
    }

    table_1_rows: list[dict[str, object]] = []
    for rule in rl_data["rules"]:
        family = rule["family"]
        for semantic_ref in family_to_sections.get(family, []):
            semantic_section = semantics_by_id.get(semantic_ref["anchor"])
            if semantic_section is None:
                continue
            table_1_rows.append(
                {
                    "rdf_based_semantics_section": semantic_section["label"],
                    "semantics_html_anchor": (
                        f"docs/specs/owl2-semantics-rdf/{semantic_section['href']}"
                    ),
                    "semantics_html_lines": line_range_text(
                        semantic_section["line_range"]
                    ),
                    "owl_2_rl_rule": rule["id"],
                    "owl_2_rl_html_anchor": (
                        f"docs/specs/owl2-reasoning-profiles/{rule['href']}"
                    ),
                    "owl_2_rl_lines": line_range_text(rule["line_range"]),
                    "rule_family": family,
                }
            )

    table_1_rows.sort(
        key=lambda row: (
            row["rdf_based_semantics_section"],
            row["owl_2_rl_rule"],
            row["owl_2_rl_html_anchor"],
        )
    )

    table_2_rows: list[dict[str, object]] = []
    for rule_id, section_ids in OPTIONAL_RDFS_SUPPORT_RULES.items():
        rdfs_rule = rdfs_rules_by_id.get(rule_id)
        if rdfs_rule is None:
            continue
        for section_id in section_ids:
            semantic_section = semantics_by_id.get(section_id)
            if semantic_section is None:
                continue
            table_2_rows.append(
                {
                    "rdf_based_semantics_section": semantic_section["label"],
                    "semantics_html_anchor": (
                        f"docs/specs/owl2-semantics-rdf/{semantic_section['href']}"
                    ),
                    "semantics_html_lines": line_range_text(
                        semantic_section["line_range"]
                    ),
                    "optional_rdfs_support_rule": rdfs_rule["id"],
                    "optional_rdfs_support_html_anchor": (
                        f"docs/specs/rdf11-semantics/{rdfs_rule['href']}"
                    ),
                    "optional_rdfs_support_lines": line_range_text(
                        rdfs_rule["line_range"]
                    ),
                }
            )

    table_2_rows.sort(
        key=lambda row: (
            row["rdf_based_semantics_section"],
            row["optional_rdfs_support_rule"],
        )
    )

    table_3_rows: list[dict[str, object]] = []
    for item_id, section_ids in RDFS_AXIOMATIC_TRIPLE_SECTION_MAP.items():
        axiomatic_item = axiomatic_rdfs_items_by_id.get(item_id)
        if axiomatic_item is None:
            continue
        for section_id in section_ids:
            semantic_section = semantics_by_id.get(section_id)
            if semantic_section is None:
                continue
            table_3_rows.append(
                {
                    "rdf_based_semantics_section": semantic_section["label"],
                    "semantics_html_anchor": (
                        f"docs/specs/owl2-semantics-rdf/{semantic_section['href']}"
                    ),
                    "semantics_html_lines": line_range_text(
                        semantic_section["line_range"]
                    ),
                    "rdfs_axiomatic_triple": axiomatic_item["name"],
                    "rdfs_axiomatic_triple_html_anchor": (
                        f"docs/specs/owl2-semantics-rdf/{axiomatic_item['href']}"
                    ),
                    "rdfs_axiomatic_triple_lines": line_range_text(
                        axiomatic_item["line_range"]
                    ),
                }
            )

    table_3_rows.sort(
        key=lambda row: (
            row["rdf_based_semantics_section"],
            row["rdfs_axiomatic_triple"],
        )
    )

    table_4_rows: list[dict[str, object]] = []
    for seed_row in master_seed["rows"]:
        mapping_construct = mapping_constructs_by_id.get(
            seed_row["mapping_to_rdf_construct_id"]
        )

        semantics_refs = []
        for section_id in seed_row["rdf_based_semantics_section_ids"]:
            semantic_section = semantics_by_id.get(section_id)
            if semantic_section is not None:
                semantics_refs.append(
                    f"docs/specs/owl2-semantics-rdf/{semantic_section['href']}"
                )

        rl_rule_refs = []
        for rule_id in seed_row["owl_2_rl_rules"]:
            rule = rl_rules_by_id.get(rule_id)
            if rule is not None:
                rl_rule_refs.append(
                    f"{rule_id} (docs/specs/owl2-reasoning-profiles/{rule['href']})"
                )

        optional_rdfs_support_refs = []
        for rule_id in seed_row["optional_rdfs_support_rules"]:
            rule = rdfs_rules_by_id.get(rule_id)
            if rule is not None:
                optional_rdfs_support_refs.append(
                    f"{rule_id} (docs/specs/rdf11-semantics/{rule['href']})"
                )

        axiomatic_refs = []
        for item_id in seed_row["rdfs_axiomatic_triple_ids"]:
            axiomatic_item = axiomatic_rdfs_items_by_id.get(item_id)
            if axiomatic_item is not None:
                axiomatic_refs.append(
                    f"{axiomatic_item['name']} "
                    f"(docs/specs/owl2-semantics-rdf/{axiomatic_item['href']})"
                )

        table_4_rows.append(
            {
                "structural_element_subtype": seed_row["structural_element_subtype"],
                "owl_structural_construct": seed_row["owl_structural_construct"],
                "mapping_to_rdf_anchor": (
                    f"docs/specs/owl2-mapping-to-rdf/{mapping_construct['href']}"
                    if mapping_construct is not None
                    else ""
                ),
                "rdf_based_semantics": "; ".join(semantics_refs),
                "direct_semantics": seed_row["direct_semantics_anchor"],
                "owl_2_rl_rules": "; ".join(rl_rule_refs),
                "optional_rdfs_support": "; ".join(optional_rdfs_support_refs),
                "rdfs_axiomatic_triples": "; ".join(axiomatic_refs),
                "implementation_status": seed_row["implementation_status"],
                "reconstruction_note": seed_row["reconstruction_note"],
            }
        )

    json_payload = {
        "tables": {
            "table_1_rl_rule_to_rdf_based_semantics_section": table_1_rows,
            "table_2_optional_rdfs_support_rule_to_rdf_based_semantics_section": (
                table_2_rows
            ),
            "table_3_rdfs_axiomatic_triple_to_rdf_based_semantics_section": (
                table_3_rows
            ),
            "table_4_structuralelement_oriented_master_crosswalk": table_4_rows,
        }
    }
    args.json_output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(json_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    section_metadata_by_key = {
        "table_1": [
            f"- Rows: {len(table_1_rows)}",
            f"- Distinct OWL 2 RL rules: {len(rl_data['rules'])}",
            f"- Distinct RDF-Based semantic sections referenced: {len({row['rdf_based_semantics_section'] for row in table_1_rows})}",
        ],
        "table_2": [
            f"- Rows: {len(table_2_rows)}",
            f"- Distinct optional RDFS support rules: {len({row['optional_rdfs_support_rule'] for row in table_2_rows})}",
        ],
        "table_3": [
            f"- Rows: {len(table_3_rows)}",
            f"- Distinct RDFS axiomatic triple anchors: {len({row['rdfs_axiomatic_triple_html_anchor'] for row in table_3_rows})}",
        ],
        "table_4": [
            f"- Rows: {len(table_4_rows)}",
            f"- Distinct StructuralElement subtypes: {len({row['structural_element_subtype'] for row in table_4_rows})}",
        ],
    }
    table_render_rows = {
        "table_1": [
            [
                row["rdf_based_semantics_section"],
                row["semantics_html_anchor"],
                row["semantics_html_lines"],
                row["owl_2_rl_rule"],
                row["owl_2_rl_html_anchor"],
                row["owl_2_rl_lines"],
                row["rule_family"],
            ]
            for row in table_1_rows
        ],
        "table_2": [
            [
                row["rdf_based_semantics_section"],
                row["semantics_html_anchor"],
                row["semantics_html_lines"],
                row["optional_rdfs_support_rule"],
                row["optional_rdfs_support_html_anchor"],
                row["optional_rdfs_support_lines"],
            ]
            for row in table_2_rows
        ],
        "table_3": [
            [
                row["rdf_based_semantics_section"],
                row["semantics_html_anchor"],
                row["semantics_html_lines"],
                row["rdfs_axiomatic_triple"],
                row["rdfs_axiomatic_triple_html_anchor"],
                row["rdfs_axiomatic_triple_lines"],
            ]
            for row in table_3_rows
        ],
        "table_4": [
            [
                row["structural_element_subtype"],
                row["owl_structural_construct"],
                row["mapping_to_rdf_anchor"],
                row["rdf_based_semantics"],
                row["direct_semantics"],
                row["owl_2_rl_rules"],
                row["optional_rdfs_support"],
                row["rdfs_axiomatic_triples"],
                row["implementation_status"],
                row["reconstruction_note"],
            ]
            for row in table_4_rows
        ],
    }

    lines = [
        "# OWL 2 Crosswalks",
        "",
        "This directory contains repository-authored crosswalks built from",
        "spec-local `index-data.json` artifacts.",
        "",
        "## Lookup Tables",
        "",
        f"- [Machine-readable data]({args.json_output.name})",
        "",
        "__LOOKUP_TABLE_PLACEHOLDER__",
    ]

    for table_definition in TABLE_DEFINITIONS:
        lines.extend(
            [
                f"### {table_definition['title']}",
                "",
                *table_definition["summary_lines"],
                "",
                *section_metadata_by_key[table_definition["key"]],
                "",
                f"#### {table_definition['data_heading']}",
                "",
                *render_markdown_table(
                    table_definition["columns"],
                    table_render_rows[table_definition["key"]],
                ),
                "",
            ]
        )

    heading_line_numbers = find_heading_line_numbers(
        lines, [item["title"] for item in TABLE_DEFINITIONS]
    )
    lookup_rows = []
    for index, table_definition in enumerate(TABLE_DEFINITIONS):
        title = table_definition["title"]
        start_line = heading_line_numbers[title]
        if index + 1 < len(TABLE_DEFINITIONS):
            end_line = heading_line_numbers[TABLE_DEFINITIONS[index + 1]["title"]] - 1
        else:
            end_line = len(lines)
        lookup_rows.append(
            [
                f"[{title}](#{github_heading_slug(title)})",
                f"{start_line}-{end_line}",
            ]
        )

    lookup_table_lines = render_markdown_table(["Table", "Lines"], lookup_rows)
    placeholder_index = lines.index("__LOOKUP_TABLE_PLACEHOLDER__")
    lines[placeholder_index : placeholder_index + 1] = lookup_table_lines + [""]

    while lines and lines[-1] == "":
        lines.pop()

    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
