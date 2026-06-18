from __future__ import annotations

import copy
import os
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML = "http://www.w3.org/XML/1998/namespace"

ET.register_namespace("w", W)
ET.register_namespace("r", R)


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == qn(W, "t"):
            parts.append(node.text or "")
        elif node.tag == qn(W, "tab"):
            parts.append("\t")
        elif node.tag == qn(W, "br"):
            parts.append("\n")
    return "".join(parts)


def clear_runs(paragraph: ET.Element) -> None:
    for child in list(paragraph):
        if child.tag != qn(W, "pPr"):
            paragraph.remove(child)


def make_run(text: str) -> ET.Element:
    run = ET.Element(qn(W, "r"))
    text_node = ET.SubElement(run, qn(W, "t"))
    if text.startswith(" ") or text.endswith(" "):
        text_node.set(qn(XML, "space"), "preserve")
    text_node.text = text
    return run


def make_paragraph(
    text: str = "",
    style_id: str | None = None,
    centered: bool = False,
    bold: bool = False,
    italic: bool = False,
) -> ET.Element:
    paragraph = ET.Element(qn(W, "p"))
    if style_id or centered:
        ppr = ET.SubElement(paragraph, qn(W, "pPr"))
        if style_id:
            pstyle = ET.SubElement(ppr, qn(W, "pStyle"))
            pstyle.set(qn(W, "val"), style_id)
        if centered:
            jc = ET.SubElement(ppr, qn(W, "jc"))
            jc.set(qn(W, "val"), "center")
    if text:
        run = ET.Element(qn(W, "r"))
        if bold or italic:
            rpr = ET.SubElement(run, qn(W, "rPr"))
            if bold:
                ET.SubElement(rpr, qn(W, "b"))
            if italic:
                ET.SubElement(rpr, qn(W, "i"))
        text_node = ET.SubElement(run, qn(W, "t"))
        if text.startswith(" ") or text.endswith(" "):
            text_node.set(qn(XML, "space"), "preserve")
        text_node.text = text
        paragraph.append(run)
    return paragraph


def make_page_break_paragraph() -> ET.Element:
    paragraph = ET.Element(qn(W, "p"))
    run = ET.SubElement(paragraph, qn(W, "r"))
    br = ET.SubElement(run, qn(W, "br"))
    br.set(qn(W, "type"), "page")
    return paragraph


def make_field_paragraph(instr: str, placeholder: str) -> ET.Element:
    paragraph = ET.Element(qn(W, "p"))
    fld = ET.SubElement(paragraph, qn(W, "fldSimple"))
    fld.set(qn(W, "instr"), instr)
    run = ET.SubElement(fld, qn(W, "r"))
    text_node = ET.SubElement(run, qn(W, "t"))
    text_node.set(qn(XML, "space"), "preserve")
    text_node.text = placeholder
    return paragraph


def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    clear_runs(paragraph)
    paragraph.append(make_run(text))


def insert_before(parent: ET.Element, target: ET.Element, node: ET.Element) -> None:
    children = list(parent)
    index = children.index(target)
    parent.insert(index, node)


def append_before_sectpr(body: ET.Element, node: ET.Element) -> None:
    sectpr = body.find(qn(W, "sectPr"))
    if sectpr is None:
        body.append(node)
        return
    children = list(body)
    index = children.index(sectpr)
    body.insert(index, node)


def find_paragraphs(root: ET.Element, target_text: str) -> list[ET.Element]:
    matches: list[ET.Element] = []
    for paragraph in root.findall(".//w:p", {"w": W}):
        if paragraph_text(paragraph).strip() == target_text:
            matches.append(paragraph)
    return matches


def find_first_paragraph(root: ET.Element, snippet: str) -> ET.Element | None:
    for paragraph in root.findall(".//w:p", {"w": W}):
        if snippet in paragraph_text(paragraph):
            return paragraph
    return None


def replace_all_text(root: ET.Element, old: str, new: str) -> int:
    count = 0
    for paragraph in root.findall(".//w:p", {"w": W}):
        text = paragraph_text(paragraph)
        if old in text:
            set_paragraph_text(paragraph, text.replace(old, new))
            count += 1
    return count


def insert_after(body: ET.Element, target: ET.Element, node: ET.Element) -> None:
    children = list(body)
    index = children.index(target)
    body.insert(index + 1, node)


def clone_paragraph_with_text(template: ET.Element, text: str) -> ET.Element:
    cloned = copy.deepcopy(template)
    set_paragraph_text(cloned, text)
    return cloned


def main() -> None:
    root = Path(r"c:\Users\LENOVO\Desktop\Diaspora E-voting with ZK-Starks prototype")
    project_dir = root / "Final Year Project by Codex"
    draft_path = project_dir / "Draft of Final Year Project with Mendeley cite.docx"
    output_path = project_dir / "Defense Ready Final Year Project Report.docx"
    temp_dir = project_dir / "report_work" / "_docx_temp"
    screenshots_dir = project_dir / "report_assets" / "screenshots"
    diagrams_dir = project_dir / "report_assets" / "diagrams"

    temp_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(draft_path, "r") as zin:
        zin.extractall(temp_dir)

    document_xml = temp_dir / "word" / "document.xml"
    tree = ET.parse(document_xml)
    document = tree.getroot()
    body = document.find(qn(W, "body"))
    if body is None:
        raise RuntimeError("word/document.xml is missing the document body")

    # Fix dangerous phrases and wording.
    replacements = {
        "PROTOYPE": "PROTOTYPE",
        "proposed system": "implemented prototype",
        "blockchain-centred": "privacy-preserving cryptography-focused",
        "blockchain": "privacy-preserving cryptography",
        "complete anonymity": "privacy-preserving public verification metadata",
        "fully anonymous": "privacy-preserving public verification metadata",
        "independent verification": "server-mediated verification",
        "real facial recognition": "camera-based prototype verification",
        "real biometric matching": "camera-based prototype verification",
        "tamper-proof": "tamper-evident",
        "live INEC": "official electoral infrastructure",
        "live NIMC": "national identity",
        "state collation": "regional results aggregation",
        "presidential election": "national election",
    }
    for old, new in replacements.items():
        replace_all_text(document, old, new)

    # Replace headline chapters with the requested chapter labels.
    replace_all_text(document, "CHAPTER ONE", "CHAPTER ONE: INTRODUCTION")
    replace_all_text(document, "CHAPTER TWO", "CHAPTER TWO: LITERATURE REVIEW")
    replace_all_text(document, "CHAPTER THREE", "CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN")
    replace_all_text(document, "CHAPTER FOUR", "CHAPTER FOUR: IMPLEMENTATION, EVALUATION, AND INTERFACES")

    # Insert front matter before the first chapter paragraph.
    first_chapter = find_first_paragraph(document, "CHAPTER ONE: INTRODUCTION")
    if first_chapter is None:
        raise RuntimeError("Could not locate Chapter One in the draft document.")

    front_matter: list[ET.Element] = [
        make_paragraph("COVER PAGE", centered=True, bold=True),
        make_paragraph("DESIGN AND IMPLEMENTATION OF A SECURE DIASPORA E-VOTING PROTOTYPE USING zk-STARK PROTOCOLS", centered=True, bold=True),
        make_paragraph("BY", centered=True, bold=True),
        make_paragraph("ADELUKA OLUWAMBEPELUMI EMMANUEL", centered=True, bold=True),
        make_paragraph("A PROJECT SUBMITTED TO THE DEPARTMENT OF COMPUTER AND INFORMATION SCIENCES, COLLEGE OF SCIENCE AND TECHNOLOGY, COVENANT UNIVERSITY, OTA, OGUN STATE.", centered=True),
        make_paragraph("IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE BACHELOR OF SCIENCE (HONOURS) DEGREE IN COMPUTER SCIENCE.", centered=True),
        make_paragraph("JUNE, 2026", centered=True, bold=True),
        make_page_break_paragraph(),
        make_paragraph("CERTIFICATION", centered=True, bold=True),
        make_paragraph("I hereby certify that this project was carried out by Adeluka Oluwambepelumi Emmanuel in the Department of Computer and Information Sciences, College of Science and Technology, Covenant University, Ota, Ogun State, Nigeria, under appropriate academic supervision."),
        make_paragraph("______________________________      ______________________________"),
        make_paragraph("Supervisor                               Signature and Date"),
        make_paragraph("______________________________      ______________________________"),
        make_paragraph("Head of Department                       Signature and Date"),
        make_page_break_paragraph(),
        make_paragraph("DEDICATION", centered=True, bold=True),
        make_paragraph("This work is dedicated to God and to everyone whose support, discipline, and encouragement made the successful completion of this project possible.", centered=True),
        make_page_break_paragraph(),
        make_paragraph("ACKNOWLEDGEMENTS", centered=True, bold=True),
        make_paragraph("My sincere gratitude goes to God for His grace, strength, and guidance throughout the course of this project. I am also grateful to my family and loved ones for their patience, encouragement, and support during the research, implementation, and documentation stages of this work."),
        make_paragraph("I further appreciate the academic guidance, technical feedback, and institutional support received from the Department of Computer and Information Sciences, Covenant University. The comments and reviews provided during the development of the DiasporaVote prototype contributed significantly to the clarity, scope control, and final presentation of this study."),
        make_page_break_paragraph(),
        make_paragraph("TABLE OF CONTENTS", centered=True, bold=True),
        make_field_paragraph(r' TOC \\o "1-3" \\h \\z \\u ', "[Update TOC in Word]"),
        make_paragraph("MANUAL WORD UPDATE REQUIRED: Select all in Word and press F9 to update fields.", italic=True),
        make_page_break_paragraph(),
        make_paragraph("LIST OF FIGURES", centered=True, bold=True),
        make_paragraph("Figure 3.1   DiasporaVote system architecture"),
        make_paragraph("Figure 3.2   Voting workflow for the controlled referendum prototype"),
        make_paragraph("Figure 3.3   Use-case diagram for DiasporaVote actors"),
        make_paragraph("Figure 3.4   Database and entity-relationship design"),
        make_paragraph("Figure 3.5   zk-STARK proof verification flow"),
        make_paragraph("Figure 4.1   Landing page of the DiasporaVote prototype"),
        make_paragraph("Figure 4.2   Mock NIN accreditation page"),
        make_paragraph("Figure 4.3   Camera-based prototype verification page"),
        make_paragraph("Figure 4.4   Event dashboard showing the active referendum"),
        make_paragraph("Figure 4.5   Active referendum ballot page"),
        make_paragraph("Figure 4.6   Vote review page"),
        make_paragraph("Figure 4.7   Receipt page showing the Ballot ID and Proof Hash"),
        make_paragraph("Figure 4.8   Public verification board"),
        make_paragraph("Figure 4.9   Proof verification result"),
        make_paragraph("Figure 4.10  Tally dashboard"),
        make_paragraph("Figure 4.11  Admin login page"),
        make_paragraph("Figure 4.12  Admin mock voter registry page"),
        make_paragraph("Figure 4.13  Admin create-voter confirmation page"),
        make_page_break_paragraph(),
        make_paragraph("LIST OF TABLES", centered=True, bold=True),
        make_paragraph("Table 1.1   Objectives-Methodology mapping"),
        make_paragraph("Table 3.1   Functional requirements"),
        make_paragraph("Table 3.2   Non-functional requirements"),
        make_paragraph("Table 3.3   Threat model and mitigations"),
        make_paragraph("Table 3.4   Database design summary"),
        make_paragraph("Table 4.1   Hardware requirements"),
        make_paragraph("Table 4.2   Software requirements"),
        make_paragraph("Table 4.3   Evaluation criteria"),
        make_paragraph("Table 4.4   Functional evaluation results"),
        make_paragraph("Table 4.5   Winterfell benchmark results"),
        make_paragraph("Table 4.6   Program interfaces"),
        make_page_break_paragraph(),
        make_paragraph("ABBREVIATIONS", centered=True, bold=True),
        make_paragraph("API    Application Programming Interface"),
        make_paragraph("BVAS   Bimodal Voter Accreditation System"),
        make_paragraph("CIS    Computer and Information Sciences"),
        make_paragraph("CSS    Cascading Style Sheets"),
        make_paragraph("FYP    Final Year Project"),
        make_paragraph("HTML   HyperText Markup Language"),
        make_paragraph("INEC   Independent National Electoral Commission"),
        make_paragraph("NIMC   National Identity Management Commission"),
        make_paragraph("NIN    National Identification Number"),
        make_paragraph("RAM    Random Access Memory"),
        make_paragraph("SQLite Structured Query Language Lite"),
        make_paragraph("STARK  Scalable Transparent Argument of Knowledge"),
        make_paragraph("UI     User Interface"),
        make_paragraph("URL    Uniform Resource Locator"),
        make_paragraph("ZKP    Zero-Knowledge Proof"),
        make_page_break_paragraph(),
        make_paragraph("ABSTRACT", centered=True, bold=True),
        make_paragraph(
            "This study addressed the challenge of how secure diaspora voting could be demonstrated in a controlled Nigerian context without overclaiming institutional integration or national-election readiness. The project designed and implemented DiasporaVote, a secure binary referendum prototype that combined a React frontend, a Flask backend, SQLite persistence, a mock National Identification Number registry, and a Winterfell-based zk-STARK proof engine. The implemented workflow covered mock voter accreditation, camera-based prototype verification, event-aware ballot access, controlled Yes/No vote submission, proof generation and verification, encrypted ballot storage, receipt issuance, public-board publication of privacy-preserving verification metadata, and tally display for the active referendum event. System evaluation was evidence-based and included registered-voter login, rejection of unregistered users, verification-state enforcement, valid and invalid ballot handling, duplicate-vote rejection, proof-engine health checking, proof verification, tally behaviour, admin registry operations, deployment smoke testing, and persistence checks. Direct proof-engine benchmarks were executed against synthetic Yes and No ballots with three warm-up runs excluded and thirty measured runs retained for each case. The results showed average proof-generation times below one millisecond, average proof-verification times below one millisecond, and proof sizes of approximately 4.5 KB, indicating that the controlled binary referendum workflow was feasible within the scope of the prototype. The main contribution of the study was the implementation of a technically defensible diaspora voting prototype that demonstrated proof-backed ballot acceptance and server-mediated public verification while clearly stating its limitations, including mock identity assurance, binary-ballot scope, and non-production deployment status."
        ),
        make_paragraph("Keywords: diaspora voting, e-voting, zk-STARK, zero-knowledge proof, public verification, referendum prototype", italic=True),
        make_page_break_paragraph(),
    ]

    for node in front_matter:
        insert_before(body, first_chapter, node)

    # Insert benchmark evidence near the evaluation results section.
    eval_heading = find_first_paragraph(document, "4.5.2 Evaluation Results")
    if eval_heading is not None:
        anchor = eval_heading
        bench_paras = [
            make_paragraph("The benchmark was run directly against the proof engine to avoid frontend delay, user interaction delay, and network latency."),
            make_paragraph("Table 4.5: Winterfell proof-engine benchmark results", bold=True),
            make_paragraph("Vote Type   Runs   Avg. Generation Time   Min. Generation Time   Max. Generation Time   Avg. Verification Time   Min. Verification Time   Max. Verification Time   Avg. Proof Size   Min. Proof Size   Max. Proof Size"),
            make_paragraph("Yes   30   0.8141 ms   0.4601 ms   3.9797 ms   0.5196 ms   0.3506 ms   1.3268 ms   4523 bytes   4523 bytes   4523 bytes"),
            make_paragraph("No    30   0.7186 ms   0.4566 ms   2.4700 ms   0.4011 ms   0.3227 ms   0.7621 ms   4521 bytes   4521 bytes   4521 bytes"),
        ]
        for node in bench_paras:
            insert_after(body, anchor, node)
            anchor = node

    # Insert figures after the relevant headings.
    figure_specs = [
        ("3.3 System Architecture", [
            ("Figure 3.1: DiasporaVote system architecture", diagrams_dir / "system_architecture.png"),
        ]),
        ("3.5 Voting Protocol Design", [
            ("Figure 3.2: Voting workflow for the controlled referendum prototype", diagrams_dir / "voting_workflow.png"),
        ]),
        ("3.2 Requirement Analysis", [
            ("Figure 3.3: Use-case diagram for DiasporaVote actors", diagrams_dir / "use_case_diagram.png"),
        ]),
        ("3.7 Database Design", [
            ("Figure 3.4: Database and entity-relationship design", diagrams_dir / "database_er_diagram.png"),
        ]),
        ("3.6 zk-STARK Constraint System Design", [
            ("Figure 3.5: zk-STARK proof verification flow", diagrams_dir / "zk_stark_verification_flow.png"),
        ]),
    ]

    for heading, items in figure_specs:
        head_para = find_first_paragraph(document, heading)
        if head_para is None:
            continue
        anchor = head_para
        for caption, image_path in items:
            intro = make_paragraph(f"{caption} is shown below.")
            field = make_field_paragraph(f' INCLUDEPICTURE "{image_path}" \\d ', f"[Linked image: {image_path.name}]")
            cap = make_paragraph(caption, centered=True, italic=True)
            for node in (intro, field, cap):
                insert_after(body, anchor, node)
                anchor = node

    # Insert screenshots after the program interfaces heading.
    interfaces_heading = find_first_paragraph(document, "4.6 Program Modules and Interfaces")
    if interfaces_heading is not None:
        screenshot_items = [
            ("Figure 4.1: Landing page of the DiasporaVote prototype", screenshots_dir / "figure_4_1_landing_page.png"),
            ("Figure 4.2: Mock NIN accreditation page", screenshots_dir / "figure_4_2_accreditation_page.png"),
            ("Figure 4.3: Camera-based prototype verification page", screenshots_dir / "figure_4_3_camera_verification_page.png"),
            ("Figure 4.4: Event dashboard showing the active referendum", screenshots_dir / "figure_4_4_event_dashboard.png"),
            ("Figure 4.5: Active referendum ballot page", screenshots_dir / "figure_4_5_ballot_page.png"),
            ("Figure 4.6: Vote review page", screenshots_dir / "figure_4_6_vote_review_page.png"),
            ("Figure 4.7: Receipt page showing the Ballot ID and Proof Hash", screenshots_dir / "figure_4_7_receipt_page.png"),
            ("Figure 4.8: Public verification board", screenshots_dir / "figure_4_8_public_verification_board.png"),
            ("Figure 4.9: Proof verification result", screenshots_dir / "figure_4_9_proof_verification_result.png"),
            ("Figure 4.10: Tally dashboard", screenshots_dir / "figure_4_10_tally_dashboard.png"),
            ("Figure 4.11: Admin login page", screenshots_dir / "figure_4_11_admin_login.png"),
            ("Figure 4.12: Admin mock voter registry page", screenshots_dir / "figure_4_12_admin_registry.png"),
            ("Figure 4.13: Admin create-voter confirmation page", screenshots_dir / "figure_4_13_admin_create_voter.png"),
        ]
        anchor = interfaces_heading
        for caption, image_path in screenshot_items:
            intro = make_paragraph(f"{caption} is shown below.")
            field = make_field_paragraph(f' INCLUDEPICTURE "{image_path}" \\d ', f"[Linked image: {image_path.name}]")
            cap = make_paragraph(caption, centered=True, italic=True)
            for node in (intro, field, cap):
                insert_after(body, anchor, node)
                anchor = node

    # Append Chapter Five and References.
    chapter4_end = find_first_paragraph(document, "4.6 Program Modules and Interfaces")
    if chapter4_end is not None:
        # locate the last paragraph of the existing document body so Chapter Five goes at the end.
        last_real = None
        for child in list(body):
            if child.tag == qn(W, "p") or child.tag == qn(W, "tbl"):
                last_real = child
        if last_real is not None:
            anchor = last_real
            chapter5_nodes = [
                make_page_break_paragraph(),
                make_paragraph("CHAPTER FIVE: SUMMARY, RECOMMENDATIONS, LIMITATIONS, AND CONCLUSION", centered=True, bold=True),
                make_paragraph("5.1 Summary", bold=True),
                make_paragraph("This study implemented a secure diaspora e-voting prototype for a controlled binary referendum using zk-STARK protocols. The completed system brought together mock voter accreditation, camera-based prototype verification, event-aware ballot handling, proof-backed vote acceptance, encrypted storage, public receipt publication, server-mediated proof verification, and tally display within a single workflow designed for academic demonstration."),
        make_paragraph("The project also demonstrated that the trust problem in remote voting is broader than interface design alone. The implemented prototype showed how registry checks, duplicate-vote control, proof generation, proof hashing, privacy-preserving public verification metadata, and aggregate tally logic can work together as layers in a defensible technical design. By narrowing the scope to a referendum rather than a full national election, the study kept the cryptographic design testable and the implementation claims academically honest."),
                make_paragraph("5.2 Recommendations", bold=True),
                make_paragraph("The following recommendations arise from the implementation and evaluation outcomes of the study:"),
                make_paragraph("1. Independent client-side or auditor-side proof verification should be added so that verification does not depend entirely on the election server."),
                make_paragraph("2. Stronger identity assurance should be explored only under proper institutional, legal, and privacy approval."),
                make_paragraph("3. The proof workflow and surrounding backend logic should undergo a formal cryptographic and security audit."),
                make_paragraph("4. Larger-scale performance testing should be carried out with higher ballot volumes and concurrent users."),
                make_paragraph("5. Additional research should address coercion resistance, usability evaluation, and broader public-audit models."),
                make_paragraph("6. Deployment hardening should be improved before any real-world pilot use is considered."),
                make_paragraph("5.3 Limitations of the Study", bold=True),
                make_paragraph("The implemented prototype was intentionally limited so that its claims remained technically accurate and defensible. The main limitations are stated clearly as follows:"),
                make_paragraph("1. The identity layer used a mock NIN registry and did not connect to national identity infrastructure."),
                make_paragraph("2. The system did not integrate with official electoral infrastructure or any official national election backend."),
                make_paragraph("3. The camera-based verification step was a prototype presence check and not certified biometric identity matching."),
                make_paragraph("4. Public verification was server-mediated and did not yet provide fully independent local verification."),
                make_paragraph("5. The ballot model was restricted to a controlled binary referendum."),
                make_paragraph("6. The system did not implement national collation, multi-level aggregation, or polling-unit-to-state result flow."),
                make_paragraph("7. The backend still participated in tallying and proof access, which means the architecture was not trust-minimised to production standards."),
                make_paragraph("8. The prototype was not production-ready for national elections."),
                make_paragraph("5.4 Conclusion", bold=True),
                make_paragraph("The study achieved its main aim of designing and implementing a secure diaspora e-voting prototype using zk-STARK protocols. Within the limits of a final year technical project, the implemented system demonstrated that proof-backed ballot acceptance, controlled accreditation, privacy-preserving public verification metadata, and event-aware tallying can be combined into a coherent remote-voting workflow. The strongest conclusion of the work is therefore not that national diaspora voting has been solved, but that a careful, scope-controlled prototype can make the security and verification problem more concrete, measurable, and academically defensible for future research and development."),
                make_paragraph("REFERENCES", centered=True, bold=True),
                make_paragraph("Ali, S. T., & Murray, J. (2016). An overview of end-to-end verifiable voting systems. arXiv. https://arxiv.org/abs/1605.08554"),
                make_paragraph("Alsadi, M., Casey, M., Dragan, C. C., Dupressoir, F., Riley, L., Sallal, M., Schneider, S., Treharne, H., Wadsworth, J., & Wright, P. (2019). Towards end-to-end verifiable online voting: Adding verifiability to established voting systems. arXiv. https://arxiv.org/abs/1912.00288"),
                make_paragraph("Ben-Sasson, E., Bentov, I., Horesh, Y., & Riabzev, M. (2018). Scalable, transparent, and post-quantum secure computational integrity. IACR ePrint Archive, 2018/046. https://eprint.iacr.org/2018/046"),
                make_paragraph("Federal Republic of Nigeria. (2022). Electoral Act, 2022. Government of the Federal Republic of Nigeria."),
                make_paragraph("Goldwasser, S., Micali, S., & Rackoff, C. (1989). The knowledge complexity of interactive proof systems. SIAM Journal on Computing, 18(1), 186-208."),
                make_paragraph("International IDEA. (2007). Voting from abroad: The International IDEA handbook. International Institute for Democracy and Electoral Assistance."),
                make_paragraph("Quaglia, E. A., & Smyth, B. (2017). A short introduction to secrecy and verifiability for elections. arXiv. https://arxiv.org/abs/1702.03168"),
            ]
            for node in chapter5_nodes:
                append_before_sectpr(body, node)

    # The front-matter block was assembled in reverse order by the document tree operations
    # above. Reorder the full pre-Chapter-One block so the report opens with the cover page
    # followed by certification, dedication, acknowledgements, TOC, lists, abbreviations,
    # and abstract.
    children = list(body)
    chapter_one = find_first_paragraph(document, "CHAPTER ONE: INTRODUCTION")
    if chapter_one is not None:
        chapter_index = children.index(chapter_one)
        leading_nodes = children[:chapter_index]
        for node in leading_nodes:
            body.remove(node)
        for node in leading_nodes:
            body.insert(0, node)

    # Clean up page break / spacing around the first inserted section if needed.
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

    if output_path.exists():
        output_path.unlink()
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for path in temp_dir.rglob("*"):
            if path.is_file():
                arcname = path.relative_to(temp_dir).as_posix()
                zout.write(path, arcname)

    shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
