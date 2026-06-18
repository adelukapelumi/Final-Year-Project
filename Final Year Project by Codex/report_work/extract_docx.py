from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def qn(name: str) -> str:
    return f"{{{W}}}{name}"


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == qn("t"):
            parts.append(node.text or "")
        elif node.tag == qn("tab"):
            parts.append("\t")
        elif node.tag == qn("br"):
            parts.append("\n")
    return "".join(parts)


def paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("./w:pPr/w:pStyle", NS)
    return style.get(qn("val"), "") if style is not None else ""


def extract_document(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        entries = archive.namelist()
        document = ET.fromstring(archive.read("word/document.xml"))
        styles = ET.fromstring(archive.read("word/styles.xml"))

        style_names: dict[str, str] = {}
        for style in styles.findall(".//w:style", NS):
            style_id = style.get(qn("styleId"), "")
            name = style.find("./w:name", NS)
            if name is not None:
                style_names[style_id] = name.get(qn("val"), style_id)

        paragraphs: list[dict[str, object]] = []
        for index, paragraph in enumerate(document.findall(".//w:p", NS), start=1):
            text = paragraph_text(paragraph)
            style_id = paragraph_style(paragraph)
            paragraphs.append(
                {
                    "index": index,
                    "style_id": style_id,
                    "style_name": style_names.get(style_id, style_id),
                    "text": text,
                }
            )

        tables: list[list[list[str]]] = []
        for table in document.findall(".//w:tbl", NS):
            rows: list[list[str]] = []
            for row in table.findall("./w:tr", NS):
                cells = [
                    " ".join(
                        filter(
                            None,
                            (
                                paragraph_text(p).strip()
                                for p in cell.findall(".//w:p", NS)
                            ),
                        )
                    )
                    for cell in row.findall("./w:tc", NS)
                ]
                rows.append(cells)
            tables.append(rows)

        field_codes = [
            "".join(node.itertext())
            for node in document.findall(".//w:instrText", NS)
        ]
        simple_fields = [
            node.get(qn("instr"), "")
            for node in document.findall(".//w:fldSimple", NS)
        ]
        relationships = ET.fromstring(
            archive.read("word/_rels/document.xml.rels")
        )
        media = [name for name in entries if name.startswith("word/media/")]

        all_text = "\n".join(item["text"] for item in paragraphs)
        citation_codes = [
            code
            for code in field_codes + simple_fields
            if "CITATION" in code.upper() or "MENDELEY" in code.upper()
        ]
        dangerous = [
            phrase
            for phrase in (
                "proposed system",
                "blockchain",
                "live INEC",
                "live NIMC",
                "BVAS integration",
                "presidential election",
                "multi-candidate election",
                "political parties",
                "state collation",
                "ward collation",
                "polling unit collation",
                "tamper-proof",
                "complete anonymity",
                "fully anonymous",
                "independent verification",
                "real facial recognition",
                "real biometric matching",
                "production-ready national voting system",
            )
            if re.search(re.escape(phrase), all_text, flags=re.IGNORECASE)
        ]

        return {
            "path": str(path),
            "entry_count": len(entries),
            "paragraph_count": len(paragraphs),
            "table_count": len(tables),
            "field_code_count": len(field_codes) + len(simple_fields),
            "citation_field_count": len(citation_codes),
            "media_count": len(media),
            "relationship_count": len(list(relationships)),
            "dangerous_phrases_found": dangerous,
            "paragraphs": paragraphs,
            "tables": tables,
            "field_codes": field_codes,
            "simple_fields": simple_fields,
            "media": media,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    result = extract_document(args.document)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
