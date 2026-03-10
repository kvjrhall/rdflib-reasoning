#!/usr/bin/env python3
"""
Normalize W3C RDF/OWL specification raw HTML into a lightweight semantic form.

Behavior is defined by docs/specs/w3c-patterns.md. Run with the rdflib-reasoning
conda environment (see project AGENTS.md).

Pattern application order (w3c-patterns §5):
  1. Metadata: w3c-metadata-header
  2. Block: mapping-fss-rdf-example, example-block-owl-anexample, example-block-rdf11-primer,
     note-block, issue-block, illegal-example-block, grammar-bnf-table, structural-spec-td-to-pre,
     rdf-div-to-pre, normalize-br-inside-pre, conformance-rules, test-types-and-format,
     references-section, notation-list-to-dl, definition-dfn (block-level)
  3. Inline: rfc-keyword, definition-dfn cleanup (strip internalDFN/externalDFN classes)
  4. Strip presentational attributes (table border preserved for human readability)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

# --- Schema constants (w3c-patterns §1) ---
DATA_STRUCTURE_VALUES = frozenset(
    {
        "definition",
        "notation",
        "example",
        "illegal-example",
        "note",
        "issue",
        "rule",
        "test-type",
        "test-format",
        "grammar",
        "code",
        "mapping",
        "reference",
        "metadata",
    }
)
DATA_NORMATIVITY_VALUES = frozenset(
    {"normative", "informative", "mixed", "unspecified"}
)
DATA_ROLE_VALUES = frozenset(
    {
        "intro",
        "conformance",
        "semantics",
        "profiles",
        "examples",
        "appendix",
        "references-normative",
        "references-informative",
        "test-suite",
    }
)
CLASS_RFC_KEYWORD = "rfc-keyword"
CLASS_GRAMMAR_NONTERMINAL = "grammar-nonterminal"
CLASS_SYNTAX_TOKEN = "syntax-token"
CLASS_TERM_REF = "term-ref"

# Presentational attributes to strip in final pass (preserve id, data-*, class where semantic).
# Table border is kept for human readability (minimal byte cost).
STRIP_ATTRS = {"style", "onclick", "onload", "align"}


def spec_id_from_path(input_path: Path) -> str:
    """Derive spec identifier from input path (e.g. .../owl2-conformance/raw.html -> owl2-conformance)."""
    path = input_path.resolve()
    if path.name.lower() == "raw.html":
        return path.parent.name
    return path.stem


def get_enclosing_section_id(element: Tag) -> str | None:
    """Walk ancestors for nearest section, h2, or h3 with an id; return that id or None."""
    for parent in element.parents:
        if not isinstance(parent, Tag):
            continue
        aid = parent.get("id")
        if aid and parent.name in ("section", "h2", "h3", "h4"):
            return aid
    return None


def _origin(spec_id: str, element: Tag) -> str:
    section_id = get_enclosing_section_id(element)
    if section_id:
        return f"{spec_id}#{section_id}"
    return spec_id


# --- Pattern: w3c-metadata-header (2.11) ---
def apply_metadata_header(soup: BeautifulSoup, spec_id: str) -> None:
    head = soup.find("div", class_="head") or soup.find("div", id="respecHeader")
    if not head or not isinstance(head, Tag):
        return
    h1 = head.find("h1")
    h2 = head.find("h2")
    title_text = h1.get_text(strip=True) if h1 else ""
    status_text = h2.get_text(strip=True) if h2 else ""
    header = soup.new_tag("header")
    header["data-structure"] = "metadata"
    header["data-role"] = "intro"
    header["data-origin"] = f"{spec_id}#title"
    if title_text:
        h1_new = soup.new_tag("h1")
        h1_new["id"] = h1.get("id") if h1 else "title"
        h1_new.string = title_text
        header.append(h1_new)
    if status_text:
        p = soup.new_tag("p")
        p.string = status_text
        header.append(p)
    head.replace_with(header)


# --- Pattern: mapping-fss-rdf-example (2.7) — apply before generic example ---
def _text_from_cell(cell: Tag) -> str:
    html = cell.decode_contents()
    return re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE).strip()


def apply_mapping_fss_rdf(soup: BeautifulSoup, spec_id: str) -> None:
    # Find pairs: table.fss followed by table.rdf in same parent
    for fss in list(soup.find_all("table", class_="fss")):
        parent = fss.parent
        if not parent:
            continue
        rdf = None
        for sib in fss.next_siblings:
            if (
                isinstance(sib, Tag)
                and sib.name == "table"
                and "rdf" in (sib.get("class") or [])
            ):
                rdf = sib
                break
        if not rdf:
            continue
        # Extract text from first row first cell of each table
        fss_text = ""
        rdf_text = ""
        tr_f = fss.find("tr")
        if tr_f:
            tc = tr_f.find("td") or tr_f.find("th")
            if tc:
                fss_text = _text_from_cell(tc)
        tr_r = rdf.find("tr")
        if tr_r:
            tc = tr_r.find("td") or tr_r.find("th")
            if tc:
                rdf_text = _text_from_cell(tc)
        section = soup.new_tag("section")
        section["data-structure"] = "mapping"
        section["data-role"] = "semantics"
        section["data-origin"] = _origin(spec_id, fss)
        pre_fss = soup.new_tag("pre")
        pre_fss["data-source"] = "fss"
        pre_fss.string = fss_text
        section.append(pre_fss)
        pre_rdf = soup.new_tag("pre")
        pre_rdf["data-source"] = "rdf"
        pre_rdf.string = rdf_text
        section.append(pre_rdf)
        fss.replace_with(section)
        rdf.decompose()


# --- Pattern: example-block-owl-anexample (2.1) ---
def apply_example_owl_anexample(soup: BeautifulSoup, spec_id: str) -> None:
    for block in list(soup.find_all("div", class_="anexample")):
        aside = soup.new_tag("aside")
        aside["data-structure"] = "example"
        aside["data-normativity"] = "informative"
        aside["data-origin"] = _origin(spec_id, block)
        for c in list(block.children):
            aside.append(c)
        block.replace_with(aside)


# --- Pattern: example-block-rdf11-primer (2.2) ---
def apply_example_rdf11_primer(soup: BeautifulSoup, spec_id: str) -> None:
    for block in list(soup.find_all("div", class_="example")):
        if "anexample" in (block.get("class") or []):
            continue
        title_div = block.find("div", class_="example-title")
        label = ""
        title_text = ""
        if title_div:
            span = title_div.find("span")
            if span:
                label = span.get_text(strip=True)
            title_text = title_div.get_text(strip=True)
            if label and title_text.startswith(label):
                title_text = title_text[len(label) :].lstrip(": ").strip()
            title_div.decompose()
        aside = soup.new_tag("aside")
        aside["data-structure"] = "example"
        aside["data-normativity"] = "informative"
        aside["data-origin"] = _origin(spec_id, block)
        if label:
            aside["data-label"] = label
        if title_text:
            header = soup.new_tag("header")
            header.string = title_text
            aside.append(header)
        for c in list(block.children):
            aside.append(c)
        for pre in aside.find_all("pre", class_="example"):
            if pre.get("class") == ["example"]:
                del pre["class"]
        block.replace_with(aside)


# --- Pattern: note-block (2.3) ---
def apply_note_block(soup: BeautifulSoup, spec_id: str) -> None:
    for block in list(soup.find_all("div", class_="note")):
        for title in block.find_all("div", class_="note-title"):
            title.decompose()
        aside = soup.new_tag("aside")
        aside["data-structure"] = "note"
        aside["data-normativity"] = "informative"
        aside["data-origin"] = _origin(spec_id, block)
        for c in list(block.children):
            aside.append(c)
        block.replace_with(aside)


# --- Pattern: issue-block (optional, same shape as note) ---
def apply_issue_block(soup: BeautifulSoup, spec_id: str) -> None:
    for block in list(soup.find_all("div", class_="issue")):
        for title in block.find_all("div", class_="issue-title"):
            title.decompose()
        aside = soup.new_tag("aside")
        aside["data-structure"] = "issue"
        aside["data-normativity"] = "informative"
        aside["data-origin"] = _origin(spec_id, block)
        for c in list(block.children):
            aside.append(c)
        block.replace_with(aside)


# --- Pattern: illegal-example-block ---
def apply_illegal_example_block(soup: BeautifulSoup, spec_id: str) -> None:
    for block in list(soup.find_all("div", class_="illegal-example")):
        aside = soup.new_tag("aside")
        aside["data-structure"] = "illegal-example"
        aside["data-normativity"] = "informative"
        aside["data-origin"] = _origin(spec_id, block)
        for c in list(block.children):
            aside.append(c)
        block.replace_with(aside)


# --- Pattern: grammar-bnf-table (2.6) ---
def apply_grammar_bnf_table(soup: BeautifulSoup, spec_id: str) -> None:
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if not isinstance(heading, Tag):
            continue
        text = heading.get_text(strip=True)
        if "BNF" not in text and "grammar" not in text.lower():
            continue
        parent = heading.parent
        if not parent:
            continue
        table = None
        for sib in heading.next_siblings:
            if isinstance(sib, Tag):
                if sib.name == "table":
                    table = sib
                    break
                if sib.name in ("h2", "h3", "h4"):
                    break
        if not table:
            table = parent.find("table")
        if not table or table.parent != parent:
            continue
        section = soup.new_tag("section")
        section["data-structure"] = "grammar"
        section["data-role"] = "semantics"
        section["data-origin"] = _origin(spec_id, heading)
        new_table = soup.new_tag("table")
        rows = list(table.find_all("tr"))
        if rows and rows[0].find("th"):
            thead = soup.new_tag("thead")
            thead.append(rows[0])
            new_table.append(thead)
            rows = rows[1:]
        tbody = soup.new_tag("tbody")
        for tr in rows:
            tbody.append(tr)
        new_table.append(tbody)
        section.append(new_table)
        table.replace_with(section)


# --- Pattern: conformance-rules (2.8) ---
def apply_conformance_rules(soup: BeautifulSoup, spec_id: str) -> None:
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if not isinstance(heading, Tag):
            continue
        text = heading.get_text(strip=True)
        if "Conformance" not in text and "conformance" not in text.lower():
            continue
        section = heading.find_parent("section")
        if not section:
            # Wrap heading and following siblings into a section
            parent = heading.parent
            if not parent:
                continue
            section = soup.new_tag("section")
            section["data-structure"] = "rule"
            section["data-role"] = "conformance"
            section["data-normativity"] = "normative"
            section["data-origin"] = _origin(spec_id, heading)
            idx = list(parent.children).index(heading)
            after = list(parent.contents)[idx:]
            for node in after:
                section.append(node.extract() if hasattr(node, "extract") else node)
            parent.append(section)
        else:
            section["data-structure"] = "rule"
            section["data-role"] = "conformance"
            section["data-normativity"] = "normative"
            if "data-origin" not in section.attrs:
                section["data-origin"] = _origin(spec_id, section)


# --- Pattern: test-types-and-format (2.9) ---
def apply_test_types_and_format(soup: BeautifulSoup, spec_id: str) -> None:
    for heading in soup.find_all(["h3", "h4", "h5"]):
        if not isinstance(heading, Tag):
            continue
        text = heading.get_text(strip=True)
        if "Test Types" in text:
            section = heading.find_parent("section") or heading.parent
            if isinstance(section, Tag):
                section["data-structure"] = "test-type"
                section["data-role"] = "test-suite"
                if "data-origin" not in section.attrs:
                    section["data-origin"] = _origin(spec_id, heading)
        elif (
            "Test Case Format" in text
            or "Input Ontologies" in text
            or "Normative Syntax" in text
        ):
            section = heading.find_parent("section") or heading.parent
            if isinstance(section, Tag):
                section["data-structure"] = "test-format"
                section["data-role"] = "test-suite"
                if "data-origin" not in section.attrs:
                    section["data-origin"] = _origin(spec_id, heading)


# --- Pattern: references-section (2.10) ---
def apply_references_section(soup: BeautifulSoup, spec_id: str) -> None:
    for section in soup.find_all("section"):
        if not isinstance(section, Tag):
            continue
        h = section.find(["h2", "h3", "h4"])
        if not h:
            continue
        text = h.get_text(strip=True).lower()
        if "reference" not in text:
            continue
        section["data-structure"] = "reference"
        if "normative" in text:
            section["data-role"] = "references-normative"
        elif "informative" in text:
            section["data-role"] = "references-informative"
        if "data-origin" not in section.attrs:
            section["data-origin"] = _origin(spec_id, section)


# --- Pattern: notation list -> definition list (ul with "TERM denotes ..." -> dl/dt/dd) ---
# Rest of li text after term (rest is stripped), so separators have no leading space.
_NOTATION_SEPARATORS = ("denotes ", "is an ", "is a ", "is ", "indicates ")


def _parse_notation_li(li: Tag) -> tuple[str, str] | None:
    """If li has form <span class=\"name\">TERM</span> SEP definition, return (term, definition)."""
    span = li.find(
        "span", class_=lambda c: c and "name" in (c if isinstance(c, list) else [c])
    )
    if not span or not isinstance(span, Tag):
        return None
    term = span.get_text(strip=True)
    full = li.get_text()
    full_stripped = full.strip()
    if not term or not full_stripped.startswith(term):
        return None
    rest = full_stripped[len(term) :].strip()
    for sep in _NOTATION_SEPARATORS:
        if rest.startswith(sep):
            definition = rest[len(sep) :].strip()
            return (term, definition)
    return None


def apply_notation_list_to_dl(soup: BeautifulSoup, spec_id: str) -> None:
    """Convert ul lists of 'TERM denotes definition' items into semantic dl/dt/dd."""
    for ul in list(soup.find_all("ul")):
        if not isinstance(ul, Tag):
            continue
        lis = ul.find_all("li", recursive=False)
        if not lis:
            continue
        pairs: list[tuple[str, str]] = []
        for li in lis:
            parsed = _parse_notation_li(li)
            if parsed is None:
                break
            pairs.append(parsed)
        if len(pairs) != len(lis):
            continue
        dl = soup.new_tag("dl")
        dl["data-structure"] = "notation"
        dl["data-origin"] = _origin(spec_id, ul)
        for term, definition in pairs:
            dt = soup.new_tag("dt")
            dt["class"] = [CLASS_TERM_REF]
            dt.string = term
            dd = soup.new_tag("dd")
            dd.string = definition
            dl.append(dt)
            dl.append(dd)
        ul.replace_with(dl)


# --- Pattern: structural-spec td -> pre (table cells with br/nbsp as code listing) ---
def _td_looks_like_structural_spec(td: Tag) -> bool:
    """True if td looks like structural spec (functional or RDF-mapping style). <br> not required when anchor or RDF cues present."""
    text = td.get_text()
    # Functional-style with anchor (e.g. SubClassOf( CE₁ CE₂ )): no <br> required
    if td.find("span", id=re.compile(r"^a_")) is not None:
        return True
    # RDF-mapping style (e.g. T(CE₁) rdfs:subClassOf T(CE₂) .): statement-ending " ." or " . " and T( / vocab
    has_turtle_end = " . " in text or " ." in text
    if has_turtle_end and (
        "T(" in text
        or "TANN(" in text
        or "owl:Ontology" in text
        or "rdf:type" in text
        or "rdfs:subClassOf" in text
    ):
        return True
    # Remaining functional-style (Ontology( / Import() requires <br>
    if not td.find("br"):
        return False
    return "Ontology(" in text or "Import(" in text


def apply_structural_spec_td_to_pre(soup: BeautifulSoup, spec_id: str) -> None:
    """Wrap contents of td cells that are structural-spec listings in <pre> for semantics."""
    for td in list(soup.find_all("td")):
        if not isinstance(td, Tag) or not _td_looks_like_structural_spec(td):
            continue
        pre = soup.new_tag("pre")
        for child in list(td.children):
            pre.append(child)
        td.clear()
        td.append(pre)


# --- Pattern: rdf-div-to-pre — block-level div.rdf with <p> containing turtle -> <pre> ---
def _div_rdf_looks_like_turtle_listing(div: Tag) -> bool:
    """True if div has class rdf, contains a <p>, and text looks like RDF/turtle (not inline phrase)."""
    if not isinstance(div, Tag) or div.name != "div":
        return False
    cls = div.get("class") or []
    if "rdf" not in cls:
        return False
    if not div.find("p"):
        return False  # inline div.rdf has no <p>, e.g. "triple of the form <div class="rdf">z ...</div>"
    text = div.get_text()
    has_turtle_end = " . " in text or " ." in text
    has_vocab = (
        "rdf:type" in text or "owl:" in text or "TANN(" in text or "rdfs:" in text
    )
    return bool(has_turtle_end and has_vocab)


def apply_rdf_div_to_pre(soup: BeautifulSoup, spec_id: str) -> None:
    """Wrap block-level div.rdf <p> content in <pre data-source="rdf"> for Development Agent and tool interpretability."""
    for div in list(soup.find_all("div", class_="rdf")):
        if not _div_rdf_looks_like_turtle_listing(div):
            continue
        for p in list(div.find_all("p", recursive=False)):
            pre = soup.new_tag("pre")
            pre["data-source"] = "rdf"
            for child in list(p.children):
                pre.append(child)
            p.replace_with(pre)


def normalize_br_inside_pre(soup: BeautifulSoup) -> None:
    """Replace <br> inside <pre> with newlines to avoid double-spacing.

    - <br> followed by a newline: replace <br> with \\n and strip one leading \\n from
      the following text (so <br>\\nsomething -> \\nsomething; avoids double line break).
    - <br> followed by non-newline: replace <br> with \\n (so <br>something -> \\nsomething).
    Preserves intended \\n\\n in listings.
    """
    for pre in soup.find_all("pre"):
        if not isinstance(pre, Tag):
            continue
        for br in list(pre.find_all("br")):
            next_node = br.next_sibling
            if (
                next_node is not None
                and getattr(next_node, "startswith", None)
                and next_node.startswith("\n")
            ):
                br.replace_with(soup.new_string("\n"))
                next_node.replace_with(soup.new_string(next_node[1:]))
            else:
                br.replace_with(soup.new_string("\n"))


# --- Pattern: definition-dfn block-level (2.5) — tag sections/paragraphs with dfn ---
def apply_definition_dfn_blocks(soup: BeautifulSoup, spec_id: str) -> None:
    for p in soup.find_all("p"):
        if not isinstance(p, Tag) or not p.find("dfn"):
            continue
        text = p.get_text(strip=True).lower()
        if not any(
            phrase in text for phrase in ("is called", "is a ", "means ", " is the ")
        ):
            continue
        section = p.find_parent("section")
        if section and section.get("data-structure"):
            continue
        if section:
            if not section.get("data-structure"):
                section["data-structure"] = "definition"
                section["data-role"] = "semantics"
                section["data-origin"] = _origin(spec_id, p)
        else:
            wrap = soup.new_tag("section")
            wrap["data-structure"] = "definition"
            wrap["data-role"] = "semantics"
            wrap["data-origin"] = _origin(spec_id, p)
            p.wrap(wrap)


# --- Inline: rfc-keyword (2.4) ---
def apply_rfc_keyword(soup: BeautifulSoup, spec_id: str) -> None:
    for em in list(soup.find_all("em")):
        if not isinstance(em, Tag):
            continue
        cls = em.get("class") or []
        if "RFC2119" not in cls and "rfc2119" not in cls:
            continue
        text = em.get_text(strip=True)
        span = soup.new_tag("span")
        span["class"] = [CLASS_RFC_KEYWORD]
        span.string = text
        em.replace_with(span)


# --- Inline: strip internalDFN / externalDFN from <a> ---
def apply_definition_dfn_cleanup(soup: BeautifulSoup, spec_id: str) -> None:
    for a in soup.find_all("a", class_=True):
        if not isinstance(a, Tag):
            continue
        cls = a.get("class") or []
        new_cls = [c for c in cls if c not in ("internalDFN", "externalDFN")]
        if not new_cls:
            del a["class"]
        else:
            a["class"] = new_cls


# --- Strip presentational attributes (w3c-patterns §5) ---
def strip_presentational_attributes(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        for attr in list(tag.attrs):
            if attr in STRIP_ATTRS:
                del tag[attr]
        if tag.get("class") == []:
            del tag["class"]


def normalize(soup: BeautifulSoup, spec_id: str) -> None:
    """Apply full normalization pipeline (metadata -> block -> inline -> strip)."""
    apply_metadata_header(soup, spec_id)
    apply_mapping_fss_rdf(soup, spec_id)
    apply_example_owl_anexample(soup, spec_id)
    apply_example_rdf11_primer(soup, spec_id)
    apply_note_block(soup, spec_id)
    apply_issue_block(soup, spec_id)
    apply_illegal_example_block(soup, spec_id)
    apply_grammar_bnf_table(soup, spec_id)
    apply_structural_spec_td_to_pre(soup, spec_id)
    apply_rdf_div_to_pre(soup, spec_id)
    normalize_br_inside_pre(soup)
    apply_conformance_rules(soup, spec_id)
    apply_test_types_and_format(soup, spec_id)
    apply_references_section(soup, spec_id)
    apply_notation_list_to_dl(soup, spec_id)
    apply_definition_dfn_blocks(soup, spec_id)
    apply_rfc_keyword(soup, spec_id)
    apply_definition_dfn_cleanup(soup, spec_id)
    strip_presentational_attributes(soup)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize W3C spec raw HTML per docs/specs/w3c-patterns.md."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to raw HTML file (e.g. docs/specs/owl2-conformance/raw.html)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path; if omitted, print to stdout",
    )
    parser.add_argument(
        "--spec-id",
        type=str,
        default=None,
        help="Override spec identifier for data-origin (default: derived from input path)",
    )
    args = parser.parse_args()
    if not args.input.is_file():
        print(f"Error: not a file: {args.input}", file=sys.stderr)
        return 1
    spec_id = args.spec_id or spec_id_from_path(args.input)
    raw = args.input.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    normalize(soup, spec_id)
    out = soup.prettify()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
