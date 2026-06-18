from __future__ import annotations

import argparse
import json
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


def table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", NS):
        cells = [
            " ".join(
                filter(
                    None,
                    (paragraph_text(p).strip() for p in cell.findall(".//w:p", NS)),
                )
            )
            for cell in row.findall("./w:tc", NS)
        ]
        rows.append(cells)
    return rows


def extract_ordered(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        styles = ET.fromstring(archive.read("word/styles.xml"))

    style_names: dict[str, str] = {}
    for style in styles.findall(".//w:style", NS):
        style_id = style.get(qn("styleId"), "")
        name = style.find("./w:name", NS)
        if name is not None:
            style_names[style_id] = name.get(qn("val"), style_id)

    body = document.find("./w:body", NS)
    if body is None:
        raise RuntimeError("word/document.xml is missing the document body")

    elements: list[dict[str, object]] = []
    start_found = False

    for child in body:
        if child.tag == qn("p"):
            text = paragraph_text(child)
            stripped = text.strip()
            if not start_found and stripped == "CHAPTER ONE":
                start_found = True
            if not start_found:
                continue

            style_id = paragraph_style(child)
            elements.append(
                {
                    "type": "paragraph",
                    "text": text,
                    "style_id": style_id,
                    "style_name": style_names.get(style_id, style_id),
                }
            )
        elif child.tag == qn("tbl"):
            if not start_found:
                continue
            elements.append({"type": "table", "rows": table_rows(child)})

    return {"path": str(path), "element_count": len(elements), "elements": elements}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    result = extract_ordered(args.document)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
