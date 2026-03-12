"""Tests for the PDF report generator."""

from datetime import date, datetime

import pytest

from app.models.patient import (
    ClinicalNote,
    ImagingReport,
    LabResult,
    LabStatus,
    Medication,
    PatientDemographics,
    PatientRecord,
    ReportSections,
    Severity,
    Symptom,
    Visit,
)
from app.services.pdf_generator import generate_pdf_report


def _sample_sections() -> ReportSections:
    return ReportSections(
        subjective="Patient Alice Nguyen presents with persistent cough and fever for 5 days.",
        objective="WBC 14.5 x10^9/L (elevated). Chest X-Ray shows right lower lobe consolidation.",
        assessment="Community-acquired pneumonia (CAP). WBC leucocytosis consistent with bacterial infection.",
        plan="Amoxicillin-Clavulanate 875/125 mg BD for 7 days. Follow-up in 1 week.",
        patient_timeline=(
            "• 2024-03-05: Outpatient visit with Dr. Smith – Cough and fever | "
            "Dx: Community-acquired pneumonia (J18.9)"
        ),
        key_findings=(
            "• [2024-03-05] WBC: 14.5 x10^9/L – ABNORMAL_HIGH (ref: 4.0–11.0 x10^9/L)\n"
            "• [2024-03-05] Chest X-Ray Thorax ABNORMAL: Right lower lobe pneumonia"
        ),
        differential_diagnosis=(
            "1. Community-acquired pneumonia (J18.9) – based on clinical presentation and diagnostic workup.\n"
            "2. Atypical pneumonia – consider if no improvement on empirical therapy."
        ),
        treatment_history=(
            "• [Active] Amoxicillin-Clavulanate 875/125 mg twice daily (started 2024-03-05) | "
            "Indication: Community-acquired pneumonia"
        ),
        references=[
            "Mandell LA, et al. Infectious Diseases Society of America/American Thoracic Society "
            "Consensus Guidelines on CAP in Adults. Clin Infect Dis. 2007;44(Suppl 2):S27-72.",
            "Kasper DL, et al. Harrison's Principles of Internal Medicine. 21st ed. McGraw-Hill, 2022.",
        ],
    )


def _sample_record() -> PatientRecord:
    demo = PatientDemographics(
        patient_id="P100",
        name="Alice Nguyen",
        date_of_birth=date(1990, 4, 25),
        sex="Female",
        blood_type="O+",
        allergies=["Sulfa drugs"],
    )
    return PatientRecord(
        demographics=demo,
        chief_complaint="Persistent cough and fever",
        symptoms=[
            Symptom(description="Cough", onset_date=date(2024, 3, 1), severity=Severity.MODERATE),
            Symptom(description="Fever", severity=Severity.MILD),
        ],
        lab_results=[
            LabResult(
                test_name="WBC",
                value=14.5,
                unit="x10^9/L",
                reference_range_low=4.0,
                reference_range_high=11.0,
                status=LabStatus.ABNORMAL_HIGH,
                performed_date=date(2024, 3, 5),
            ),
        ],
        imaging_reports=[
            ImagingReport(
                modality="Chest X-Ray",
                body_region="Thorax",
                performed_date=date(2024, 3, 5),
                findings="Right lower lobe consolidation",
                impression="Findings consistent with right lower lobe pneumonia",
                is_abnormal=True,
            )
        ],
        medications=[
            Medication(
                name="Amoxicillin-Clavulanate",
                dose="875/125 mg twice daily",
                indication="Community-acquired pneumonia",
                start_date=date(2024, 3, 5),
                is_current=True,
            )
        ],
        visits=[
            Visit(
                visit_date=date(2024, 3, 5),
                visit_type="Outpatient",
                provider="Dr. Smith",
                chief_complaint="Cough and fever",
                diagnoses=["Community-acquired pneumonia (J18.9)"],
            )
        ],
        clinical_notes=[
            ClinicalNote(
                note_date=date(2024, 3, 5),
                provider="Dr. Smith",
                specialty="General Practice",
                subjective="5-day history of productive cough and fever.",
                objective="Temp 38.6°C, HR 98 bpm. Decreased breath sounds right base.",
                assessment="Community-acquired pneumonia.",
                plan="Empirical antibiotics, chest X-ray, full blood count.",
                diagnosis_codes=["J18.9"],
            )
        ],
        report_requested_at=datetime(2024, 3, 6, 9, 0, 0),
    )


class TestGeneratePdfReport:
    def test_returns_bytes(self):
        record = _sample_record()
        sections = _sample_sections()
        pdf_bytes = generate_pdf_report(record, sections)
        assert isinstance(pdf_bytes, bytes)

    def test_pdf_starts_with_header(self):
        record = _sample_record()
        sections = _sample_sections()
        pdf_bytes = generate_pdf_report(record, sections)
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b"%PDF"

    def test_pdf_non_empty(self):
        record = _sample_record()
        sections = _sample_sections()
        pdf_bytes = generate_pdf_report(record, sections)
        assert len(pdf_bytes) > 1024  # At least 1 KB

    def test_minimal_patient_record(self):
        """PDF generation should succeed with a minimal patient record (no optional fields)."""
        demo = PatientDemographics(
            patient_id="P_MIN",
            name="Minimal Patient",
            date_of_birth=date(1980, 1, 1),
            sex="Male",
        )
        record = PatientRecord(
            demographics=demo,
            report_requested_at=datetime(2024, 1, 1, 0, 0, 0),
        )
        sections = ReportSections(
            subjective="No complaints.",
            objective="No objective data.",
            assessment="Assessment pending.",
            plan="Further evaluation required.",
            patient_timeline="No visit history recorded.",
            key_findings="No significant abnormal findings identified.",
            differential_diagnosis="Insufficient data for differential diagnosis.",
            treatment_history="No medication history recorded.",
        )
        pdf_bytes = generate_pdf_report(record, sections)
        assert pdf_bytes[:4] == b"%PDF"

    def test_report_with_multiple_lab_results(self):
        """PDF generation handles multiple lab results including abnormal ones."""
        demo = PatientDemographics(
            patient_id="P200",
            name="Bob Lee",
            date_of_birth=date(1965, 8, 10),
            sex="Male",
        )
        record = PatientRecord(
            demographics=demo,
            lab_results=[
                LabResult(
                    test_name="HbA1c",
                    value=9.2,
                    unit="%",
                    reference_range_low=4.0,
                    reference_range_high=5.7,
                    status=LabStatus.ABNORMAL_HIGH,
                    performed_date=date(2024, 2, 1),
                ),
                LabResult(
                    test_name="Creatinine",
                    value=1.0,
                    unit="mg/dL",
                    reference_range_low=0.7,
                    reference_range_high=1.2,
                    status=LabStatus.NORMAL,
                    performed_date=date(2024, 2, 1),
                ),
            ],
            report_requested_at=datetime(2024, 2, 2, 8, 0, 0),
        )
        sections = ReportSections(
            subjective="Routine diabetes review.",
            objective="HbA1c 9.2% – elevated.",
            assessment="Poorly controlled Type 2 Diabetes Mellitus.",
            plan="Intensify glucose-lowering therapy.",
            patient_timeline="No visit history recorded.",
            key_findings="• HbA1c 9.2% – ABNORMAL HIGH",
            differential_diagnosis="1. Type 2 Diabetes Mellitus – uncontrolled",
            treatment_history="• No current medications",
        )
        pdf_bytes = generate_pdf_report(record, sections)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 1024
