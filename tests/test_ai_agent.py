"""Tests for the AI agent / report section generation."""

from datetime import date, datetime
from unittest.mock import patch

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
from app.services.ai_agent import _rule_based_sections, generate_report_sections


def _full_record() -> PatientRecord:
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
            LabResult(
                test_name="Haemoglobin",
                value=13.0,
                unit="g/dL",
                reference_range_low=12.0,
                reference_range_high=16.0,
                status=LabStatus.NORMAL,
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
            ),
            Medication(
                name="Paracetamol",
                dose="1g four times daily",
                indication="Fever",
                start_date=date(2024, 3, 5),
                end_date=date(2024, 3, 8),
                is_current=False,
            ),
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


class TestRuleBasedSections:
    def test_returns_report_sections(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert isinstance(sections, ReportSections)

    def test_subjective_includes_chief_complaint(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "cough" in sections.subjective.lower() or "fever" in sections.subjective.lower()

    def test_subjective_includes_allergies(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "sulfa" in sections.subjective.lower()

    def test_objective_includes_abnormal_lab(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "WBC" in sections.objective or "wbc" in sections.objective.lower()

    def test_key_findings_contains_abnormal_lab(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "WBC" in sections.key_findings

    def test_key_findings_contains_abnormal_imaging(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "ABNORMAL" in sections.key_findings or "Chest X-Ray" in sections.key_findings

    def test_key_findings_no_abnormals(self):
        demo = PatientDemographics(
            patient_id="P_NORMAL",
            name="Normal Patient",
            date_of_birth=date(1990, 1, 1),
            sex="Male",
        )
        record = PatientRecord(
            demographics=demo,
            lab_results=[
                LabResult(
                    test_name="Sodium",
                    value=140.0,
                    unit="mmol/L",
                    reference_range_low=135.0,
                    reference_range_high=145.0,
                    status=LabStatus.NORMAL,
                    performed_date=date(2024, 3, 1),
                )
            ],
        )
        sections = _rule_based_sections(record)
        assert "No significant abnormal findings identified" in sections.key_findings

    def test_patient_timeline_sorted(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "2024-03-05" in sections.patient_timeline

    def test_treatment_history_includes_active_medication(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "Amoxicillin-Clavulanate" in sections.treatment_history

    def test_treatment_history_includes_discontinued(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "Paracetamol" in sections.treatment_history

    def test_differential_diagnosis_includes_recorded_dx(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert "J18.9" in sections.differential_diagnosis or "pneumonia" in sections.differential_diagnosis.lower()

    def test_references_populated(self):
        record = _full_record()
        sections = _rule_based_sections(record)
        assert len(sections.references) > 0

    def test_minimal_record(self):
        """Rule-based extraction should handle a record with no optional data."""
        demo = PatientDemographics(
            patient_id="P_MIN",
            name="Minimal Patient",
            date_of_birth=date(1980, 1, 1),
            sex="Male",
        )
        record = PatientRecord(demographics=demo)
        sections = _rule_based_sections(record)
        assert isinstance(sections, ReportSections)
        assert sections.subjective != ""
        assert sections.treatment_history == "No medication history recorded."

    def test_nkda_when_no_allergies(self):
        demo = PatientDemographics(
            patient_id="P_NO_ALLERGY",
            name="No Allergy Patient",
            date_of_birth=date(1975, 5, 5),
            sex="Female",
        )
        record = PatientRecord(demographics=demo)
        sections = _rule_based_sections(record)
        assert "NKDA" in sections.subjective


class TestGenerateReportSections:
    def test_uses_rule_based_without_api_key(self):
        """Without an API key, generate_report_sections should use rule-based extraction."""
        record = _full_record()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            sections = generate_report_sections(record)
        assert isinstance(sections, ReportSections)

    def test_falls_back_on_llm_error(self):
        """If LLM call raises an exception, falls back to rule-based extraction."""
        record = _full_record()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fake-key"}, clear=False):
            with patch("app.services.ai_agent._llm_sections", side_effect=Exception("LLM error")):
                sections = generate_report_sections(record)
        assert isinstance(sections, ReportSections)
        assert sections.subjective != ""
