"""Tests for patient data models."""

from datetime import date, datetime

import pytest

from app.models.patient import (
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
    ClinicalNote,
)


class TestPatientDemographics:
    def test_basic_creation(self):
        demo = PatientDemographics(
            patient_id="P001",
            name="Jane Doe",
            date_of_birth=date(1985, 6, 15),
            sex="Female",
        )
        assert demo.patient_id == "P001"
        assert demo.name == "Jane Doe"
        assert demo.blood_type is None
        assert demo.allergies == []

    def test_with_allergies(self):
        demo = PatientDemographics(
            patient_id="P002",
            name="John Smith",
            date_of_birth=date(1970, 1, 1),
            sex="Male",
            allergies=["Penicillin", "Aspirin"],
            blood_type="A+",
        )
        assert len(demo.allergies) == 2
        assert "Penicillin" in demo.allergies


class TestSymptom:
    def test_symptom_with_severity(self):
        s = Symptom(
            description="Shortness of breath",
            onset_date=date(2024, 1, 10),
            severity=Severity.MODERATE,
            duration="5 days",
        )
        assert s.severity == Severity.MODERATE
        assert s.duration == "5 days"

    def test_symptom_minimal(self):
        s = Symptom(description="Fatigue")
        assert s.description == "Fatigue"
        assert s.severity is None


class TestLabResult:
    def test_normal_result(self):
        lr = LabResult(
            test_name="Haemoglobin",
            value=13.5,
            unit="g/dL",
            reference_range_low=12.0,
            reference_range_high=16.0,
            status=LabStatus.NORMAL,
            performed_date=date(2024, 3, 1),
        )
        assert lr.status == LabStatus.NORMAL

    def test_compute_status_high(self):
        lr = LabResult(
            test_name="Glucose",
            value=200.0,
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=100.0,
            status=LabStatus.NORMAL,
            performed_date=date(2024, 3, 1),
        )
        assert lr.compute_status() == LabStatus.ABNORMAL_HIGH

    def test_compute_status_low(self):
        lr = LabResult(
            test_name="Potassium",
            value=2.8,
            unit="mmol/L",
            reference_range_low=3.5,
            reference_range_high=5.0,
            status=LabStatus.NORMAL,
            performed_date=date(2024, 3, 1),
        )
        assert lr.compute_status() == LabStatus.ABNORMAL_LOW

    def test_compute_status_normal(self):
        lr = LabResult(
            test_name="Sodium",
            value=140.0,
            unit="mmol/L",
            reference_range_low=135.0,
            reference_range_high=145.0,
            status=LabStatus.NORMAL,
            performed_date=date(2024, 3, 1),
        )
        assert lr.compute_status() == LabStatus.NORMAL

    def test_compute_status_no_range(self):
        lr = LabResult(
            test_name="Culture",
            value=0.0,
            unit="CFU/mL",
            status=LabStatus.NORMAL,
            performed_date=date(2024, 3, 1),
        )
        assert lr.compute_status() == LabStatus.NORMAL


class TestImagingReport:
    def test_abnormal_imaging(self):
        ir = ImagingReport(
            modality="Chest X-Ray",
            body_region="Thorax",
            performed_date=date(2024, 2, 20),
            findings="Bilateral infiltrates present",
            impression="Findings consistent with pneumonia",
            is_abnormal=True,
        )
        assert ir.is_abnormal is True
        assert "pneumonia" in ir.impression.lower()

    def test_normal_imaging(self):
        ir = ImagingReport(
            modality="Ultrasound",
            body_region="Abdomen",
            performed_date=date(2024, 1, 15),
            findings="No abnormalities detected",
            impression="Normal abdominal ultrasound",
            is_abnormal=False,
        )
        assert ir.is_abnormal is False


class TestMedication:
    def test_current_medication(self):
        med = Medication(
            name="Metformin",
            dose="500 mg twice daily",
            indication="Type 2 Diabetes Mellitus",
            is_current=True,
        )
        assert med.is_current is True

    def test_discontinued_medication(self):
        med = Medication(
            name="Amoxicillin",
            dose="500 mg three times daily",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            is_current=False,
        )
        assert med.is_current is False
        assert med.end_date == date(2024, 1, 10)


class TestPatientRecord:
    def _sample_record(self) -> PatientRecord:
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
            report_requested_at=datetime(2024, 3, 6, 9, 0, 0),
        )

    def test_patient_record_creation(self):
        record = self._sample_record()
        assert record.demographics.patient_id == "P100"
        assert len(record.symptoms) == 2
        assert len(record.lab_results) == 1
        assert len(record.imaging_reports) == 1
        assert len(record.medications) == 1
        assert len(record.visits) == 1

    def test_patient_record_defaults(self):
        demo = PatientDemographics(
            patient_id="P999",
            name="Test Patient",
            date_of_birth=date(2000, 1, 1),
            sex="Male",
        )
        record = PatientRecord(demographics=demo)
        assert record.symptoms == []
        assert record.lab_results == []
        assert record.imaging_reports == []
        assert record.clinical_notes == []
        assert record.medications == []
        assert record.visits == []


class TestReportSections:
    def test_report_sections_creation(self):
        sections = ReportSections(
            subjective="Patient reports cough and fever.",
            objective="WBC elevated at 14.5 x10^9/L. Chest X-ray shows consolidation.",
            assessment="Community-acquired pneumonia.",
            plan="Start Amoxicillin-Clavulanate 875/125 mg BD.",
            patient_timeline="• 2024-03-05: Outpatient visit – cough and fever",
            key_findings="• WBC 14.5 x10^9/L – ABNORMAL HIGH",
            differential_diagnosis="1. Community-acquired pneumonia\n2. Atypical pneumonia",
            treatment_history="• [Active] Amoxicillin-Clavulanate 875/125 mg twice daily",
            references=["Harrison's Principles of Internal Medicine, 21st ed."],
        )
        assert "pneumonia" in sections.assessment.lower()
        assert len(sections.references) == 1
