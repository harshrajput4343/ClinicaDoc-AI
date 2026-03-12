"""API router for clinical report generation."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.patient import PatientRecord
from app.services.ai_agent import generate_report_sections
from app.services.pdf_generator import generate_pdf_report

router = APIRouter(prefix="/report", tags=["Report"])


@router.post(
    "/generate",
    summary="Generate a structured clinical PDF report",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Structured clinical PDF report in SOAP format",
        },
        422: {"description": "Validation error in patient data"},
        500: {"description": "Internal server error during report generation"},
    },
)
async def generate_report(patient_record: PatientRecord) -> Response:
    """Accept a complete patient record and return a structured clinical PDF.

    The report follows SOAP format and includes:
    - Patient timeline (chronological overview)
    - Key findings (abnormal lab results and imaging)
    - Differential diagnosis support
    - Treatment history and recommendations
    - Academically referenced clinical insights
    """
    try:
        sections = generate_report_sections(patient_record)
        pdf_bytes = generate_pdf_report(patient_record, sections)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc

    filename = f"clinicadoc_{patient_record.demographics.patient_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/sections",
    summary="Generate structured SOAP report sections as JSON",
    response_model=None,
)
async def get_report_sections(patient_record: PatientRecord) -> dict:
    """Return the structured SOAP report sections as JSON without generating a PDF.

    Useful for previewing or integrating report content into other systems.
    """
    try:
        sections = generate_report_sections(patient_record)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Section generation failed: {exc}") from exc
    return sections.model_dump()
