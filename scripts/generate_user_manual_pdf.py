from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = BASE_DIR / "docs" / "USER_MANUAL_CRM_TOWER.md"
OUTPUT_PATH = BASE_DIR / "docs" / "User_Manual_CRM_Tower.pdf"


def parse_markdown_lines(raw_text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            items.append(("spacer", ""))
            continue
        if line.startswith("# "):
            items.append(("title", line[2:].strip()))
            continue
        if line.startswith("## "):
            items.append(("heading", line[3:].strip()))
            continue
        if line.startswith("- "):
            items.append(("bullet", line[2:].strip()))
            continue
        if line.startswith("`") and line.endswith("`"):
            items.append(("code", line[1:-1].strip()))
            continue
        if line[0].isdigit() and ". " in line:
            prefix, content = line.split(". ", 1)
            if prefix.isdigit():
                items.append(("numbered", f"{prefix}. {content.strip()}"))
                continue
        items.append(("paragraph", line))
    return items


def build_pdf() -> Path:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ManualTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0b1f33"),
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ManualHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0a4b78"),
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ManualBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#223548"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "ManualBullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-8,
    )
    code_style = ParagraphStyle(
        "ManualCode",
        parent=body_style,
        fontName="Courier",
        backColor=colors.HexColor("#f2f5f8"),
        borderColor=colors.HexColor("#d9dfe5"),
        borderWidth=0.5,
        borderPadding=6,
        leading=14,
        spaceBefore=4,
        spaceAfter=6,
    )

    story = []
    parsed = parse_markdown_lines(SOURCE_PATH.read_text(encoding="utf-8"))
    for item_type, text in parsed:
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if item_type == "title":
            story.append(Paragraph(safe_text, title_style))
        elif item_type == "heading":
            story.append(Paragraph(safe_text, heading_style))
        elif item_type == "bullet":
            story.append(Paragraph(f"• {safe_text}", bullet_style))
        elif item_type == "numbered":
            story.append(Paragraph(safe_text, bullet_style))
        elif item_type == "code":
            story.append(Paragraph(safe_text, code_style))
        elif item_type == "paragraph":
            story.append(Paragraph(safe_text, body_style))
        else:
            story.append(Spacer(1, 6))

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=2.1 * cm,
        rightMargin=2.1 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title="User Manual CRM Tower",
        author="OpenAI Codex",
    )
    doc.build(story)
    return OUTPUT_PATH


if __name__ == "__main__":
    path = build_pdf()
    print(path)
