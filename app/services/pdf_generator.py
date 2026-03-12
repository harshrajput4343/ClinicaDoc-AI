"""PDF report generator for ClinicaDoc AI.

Produces a structured clinical PDF report in SOAP format containing:
- Patient demographics and report metadata
- SOAP sections (Subjective, Objective, Assessment, Plan)
- Patient timeline (chronological overview)
- Key findings (abnormal lab results and imaging)
- Differential diagnosis with clinical evidence
- Treatment history and recommendations
- Academic references
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.patient import PatientRecord, ReportSections

# ── Colour palette ────────────────────────────────────────────────────────────
BRAND_BLUE = colors.HexColor("#1A4E8F")
BRAND_LIGHT_BLUE = colors.HexColor("#D6E4F7")
ACCENT_RED = colors.HexColor("#C0392B")
ACCENT_ORANGE = colors.HexColor("#E67E22")
ACCENT_GREEN = colors.HexColor("#27AE60")
LIGHT_GREY = colors.HexColor("#F5F5F5")
MID_GREY = colors.HexColor("#CCCCCC")
TEXT_DARK = colors.HexColor("#2C2C2C")


def _build_styles() -> dict[str, ParagraphStyle]:
    """Return a mapping of named paragraph styles."""
    base = getSampleStyleSheet()

    styles: dict[str, ParagraphStyle] = {}

    styles["title"] = ParagraphStyle(
        "title",
        parent=base["Title"],
        fontSize=22,
        textColor=BRAND_BLUE,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle",
        parent=base["Normal"],
        fontSize=11,
        textColor=colors.white,
        fontName="Helvetica",
        alignment=TA_CENTER,
    )
    styles["patient_info"] = ParagraphStyle(
        "patient_info",
        parent=base["Normal"],
        fontSize=10,
        textColor=TEXT_DARK,
        fontName="Helvetica",
        spaceAfter=2,
    )
    styles["section_heading"] = ParagraphStyle(
        "section_heading",
        parent=base["Heading1"],
        fontSize=13,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        spaceBefore=8,
        spaceAfter=4,
        leftIndent=8,
    )
    styles["subsection_heading"] = ParagraphStyle(
        "subsection_heading",
        parent=base["Heading2"],
        fontSize=11,
        textColor=BRAND_BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=2,
        leftIndent=4,
    )
    styles["body"] = ParagraphStyle(
        "body",
        parent=base["Normal"],
        fontSize=9.5,
        textColor=TEXT_DARK,
        fontName="Helvetica",
        leading=14,
        spaceAfter=4,
        leftIndent=4,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet",
        parent=base["Normal"],
        fontSize=9.5,
        textColor=TEXT_DARK,
        fontName="Helvetica",
        leading=13,
        spaceAfter=2,
        leftIndent=16,
        bulletIndent=4,
    )
    styles["abnormal"] = ParagraphStyle(
        "abnormal",
        parent=base["Normal"],
        fontSize=9.5,
        textColor=ACCENT_RED,
        fontName="Helvetica-Bold",
        leading=13,
        spaceAfter=2,
        leftIndent=16,
    )
    styles["reference"] = ParagraphStyle(
        "reference",
        parent=base["Normal"],
        fontSize=8.5,
        textColor=TEXT_DARK,
        fontName="Helvetica",
        leading=12,
        spaceAfter=2,
        leftIndent=16,
    )
    styles["footer"] = ParagraphStyle(
        "footer",
        parent=base["Normal"],
        fontSize=7.5,
        textColor=colors.grey,
        fontName="Helvetica",
        alignment=TA_CENTER,
    )
    styles["confidential"] = ParagraphStyle(
        "confidential",
        parent=base["Normal"],
        fontSize=8,
        textColor=ACCENT_RED,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    return styles


def _section_header(title: str, styles: dict[str, ParagraphStyle]) -> list:
    """Return flowables for a coloured section header bar."""
    para = Paragraph(title, styles["section_heading"])
    table = Table([[para]], colWidths=["100%"])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    return [Spacer(1, 0.3 * cm), table, Spacer(1, 0.2 * cm)]


def _bullet_lines(text: str, styles: dict[str, ParagraphStyle], abnormal_keyword: Optional[str] = None) -> list:
    """Convert newline-separated bullet text into Paragraph flowables."""
    flowables = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        is_abnormal = abnormal_keyword and abnormal_keyword.lower() in line.lower()
        style = styles["abnormal"] if is_abnormal else styles["bullet"]
        # Replace bullet character with ReportLab bullet marker
        display = line.lstrip("•").strip()
        flowables.append(Paragraph(f"• {display}", style))
    return flowables


def _demographics_table(record: PatientRecord, styles: dict[str, ParagraphStyle]) -> Table:
    """Build a two-column patient demographics info table."""
    demo = record.demographics
    age = (datetime.now(timezone.utc).date() - demo.date_of_birth).days // 365

    data = [
        [
            Paragraph("<b>Patient ID:</b>", styles["patient_info"]),
            Paragraph(demo.patient_id, styles["patient_info"]),
            Paragraph("<b>Report Date:</b>", styles["patient_info"]),
            Paragraph(record.report_requested_at.strftime("%d %B %Y, %H:%M UTC"), styles["patient_info"]),
        ],
        [
            Paragraph("<b>Name:</b>", styles["patient_info"]),
            Paragraph(demo.name, styles["patient_info"]),
            Paragraph("<b>Age / Sex:</b>", styles["patient_info"]),
            Paragraph(f"{age} years / {demo.sex}", styles["patient_info"]),
        ],
        [
            Paragraph("<b>Blood Type:</b>", styles["patient_info"]),
            Paragraph(demo.blood_type or "Unknown", styles["patient_info"]),
            Paragraph("<b>Allergies:</b>", styles["patient_info"]),
            Paragraph(", ".join(demo.allergies) if demo.allergies else "NKDA", styles["patient_info"]),
        ],
    ]

    table = Table(data, colWidths=[3 * cm, 6.5 * cm, 3 * cm, 6.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT_BLUE),
                ("BACKGROUND", (2, 0), (2, -1), BRAND_LIGHT_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.5, MID_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, MID_GREY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def generate_pdf_report(record: PatientRecord, sections: ReportSections) -> bytes:
    """Generate a structured clinical PDF report.

    Args:
        record:   Complete patient clinical record.
        sections: AI-generated or rule-based SOAP report sections.

    Returns:
        Raw PDF bytes ready to be written to a file or HTTP response.
    """
    buffer = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="ClinicaDoc AI – Clinical Report",
        author="ClinicaDoc AI",
        subject=f"Clinical Report: {record.demographics.name}",
    )

    story = []

    # ── Cover / Header ─────────────────────────────────────────────────────────
    # Blue banner
    banner_text = Paragraph("ClinicaDoc AI", styles["title"])
    banner_sub = Paragraph("Intelligent Clinical Documentation System", styles["subtitle"])
    banner_table = Table(
        [[banner_text], [banner_sub]],
        colWidths=["100%"],
    )
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
                ("BACKGROUND", (0, 1), (-1, 1), BRAND_BLUE),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    # Re-style title for white text on blue background
    title_white = ParagraphStyle(
        "title_white",
        parent=styles["title"],
        textColor=colors.white,
    )
    banner_table = Table(
        [
            [Paragraph("ClinicaDoc AI", title_white)],
            [Paragraph("Intelligent Clinical Documentation System", styles["subtitle"])],
        ],
        colWidths=["100%"],
    )
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLUE),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(banner_table)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("⚠ CONFIDENTIAL MEDICAL RECORD – FOR AUTHORISED CLINICAL USE ONLY", styles["confidential"]))

    # ── Patient Demographics ───────────────────────────────────────────────────
    story.extend(_section_header("PATIENT INFORMATION", styles))
    story.append(_demographics_table(record, styles))
    story.append(Spacer(1, 0.3 * cm))

    if record.chief_complaint:
        story.append(Paragraph(f"<b>Chief Complaint:</b> {record.chief_complaint}", styles["body"]))

    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 0.3 * cm))

    # ── SOAP: Subjective ───────────────────────────────────────────────────────
    story.extend(_section_header("S – SUBJECTIVE", styles))
    story.append(Paragraph(sections.subjective, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    # ── SOAP: Objective ────────────────────────────────────────────────────────
    story.extend(_section_header("O – OBJECTIVE", styles))
    story.append(Paragraph(sections.objective, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    # ── SOAP: Assessment ───────────────────────────────────────────────────────
    story.extend(_section_header("A – ASSESSMENT", styles))
    story.append(Paragraph(sections.assessment, styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    # ── SOAP: Plan ─────────────────────────────────────────────────────────────
    story.extend(_section_header("P – PLAN", styles))
    story.append(Paragraph(sections.plan, styles["body"]))
    story.append(Spacer(1, 0.3 * cm))

    # ── Patient Timeline ───────────────────────────────────────────────────────
    story.extend(_section_header("PATIENT TIMELINE", styles))
    story.append(
        Paragraph(
            "Chronological overview of clinical visits, diagnoses, and key events.",
            styles["body"],
        )
    )
    story.extend(_bullet_lines(sections.patient_timeline, styles))
    story.append(Spacer(1, 0.3 * cm))

    # ── Key Findings ───────────────────────────────────────────────────────────
    story.extend(_section_header("KEY FINDINGS", styles))
    story.append(
        Paragraph(
            "Highlighted abnormal laboratory results and imaging findings.",
            styles["body"],
        )
    )
    story.extend(_bullet_lines(sections.key_findings, styles, abnormal_keyword="ABNORMAL"))
    story.append(Spacer(1, 0.3 * cm))

    # ── Differential Diagnosis ─────────────────────────────────────────────────
    story.extend(_section_header("DIFFERENTIAL DIAGNOSIS", styles))
    story.append(
        Paragraph(
            "Differential diagnoses considered based on clinical evidence and diagnostic workup.",
            styles["body"],
        )
    )
    story.extend(_bullet_lines(sections.differential_diagnosis, styles))
    story.append(Spacer(1, 0.3 * cm))

    # ── Treatment History ──────────────────────────────────────────────────────
    story.extend(_section_header("TREATMENT HISTORY & RECOMMENDATIONS", styles))
    story.append(
        Paragraph(
            "Summary of past therapies and current treatment recommendations.",
            styles["body"],
        )
    )
    story.extend(_bullet_lines(sections.treatment_history, styles))
    story.append(Spacer(1, 0.3 * cm))

    # ── References ─────────────────────────────────────────────────────────────
    if sections.references:
        story.extend(_section_header("REFERENCES", styles))
        for i, ref in enumerate(sections.references, 1):
            story.append(Paragraph(f"{i}. {ref}", styles["reference"]))
        story.append(Spacer(1, 0.3 * cm))

    # ── Footer note ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            "This report was generated by ClinicaDoc AI and is intended to assist clinicians. "
            "It does not replace professional medical judgement. Generated on "
            f"{record.report_requested_at.strftime('%d %B %Y at %H:%M UTC')}.",
            styles["footer"],
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
