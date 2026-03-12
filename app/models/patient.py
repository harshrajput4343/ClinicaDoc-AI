"""Pydantic models for patient clinical data."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class LabStatus(str, Enum):
    NORMAL = "normal"
    ABNORMAL_LOW = "abnormal_low"
    ABNORMAL_HIGH = "abnormal_high"
    CRITICAL = "critical"


class PatientDemographics(BaseModel):
    """Basic patient identifying information."""

    patient_id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Full name of the patient")
    date_of_birth: date = Field(..., description="Patient date of birth")
    sex: str = Field(..., description="Patient sex (Male/Female/Other)")
    blood_type: Optional[str] = Field(None, description="ABO/Rh blood type")
    allergies: list[str] = Field(default_factory=list, description="Known allergies")
    contact_number: Optional[str] = Field(None, description="Contact phone number")


class Symptom(BaseModel):
    """A patient-reported symptom."""

    description: str = Field(..., description="Symptom description")
    onset_date: Optional[date] = Field(None, description="Date symptom began")
    severity: Optional[Severity] = Field(None, description="Symptom severity")
    duration: Optional[str] = Field(None, description="Duration of symptom (e.g., '3 days')")
    notes: Optional[str] = Field(None, description="Additional notes about the symptom")


class LabResult(BaseModel):
    """A single laboratory test result."""

    test_name: str = Field(..., description="Name of the laboratory test")
    value: float = Field(..., description="Numeric result value")
    unit: str = Field(..., description="Unit of measurement")
    reference_range_low: Optional[float] = Field(None, description="Lower bound of normal range")
    reference_range_high: Optional[float] = Field(None, description="Upper bound of normal range")
    status: LabStatus = Field(LabStatus.NORMAL, description="Result status relative to reference range")
    performed_date: date = Field(..., description="Date the test was performed")
    notes: Optional[str] = Field(None, description="Clinician notes on the result")

    def compute_status(self) -> LabStatus:
        """Determine status based on value and reference range."""
        if self.reference_range_low is None and self.reference_range_high is None:
            return LabStatus.NORMAL
        if self.reference_range_low is not None and self.value < self.reference_range_low:
            return LabStatus.ABNORMAL_LOW
        if self.reference_range_high is not None and self.value > self.reference_range_high:
            return LabStatus.ABNORMAL_HIGH
        return LabStatus.NORMAL


class ImagingReport(BaseModel):
    """An imaging study report."""

    modality: str = Field(..., description="Imaging modality (X-Ray, CT, MRI, Ultrasound, etc.)")
    body_region: str = Field(..., description="Body region imaged")
    performed_date: date = Field(..., description="Date imaging was performed")
    findings: str = Field(..., description="Radiologist findings")
    impression: str = Field(..., description="Radiologist impression / conclusion")
    radiologist: Optional[str] = Field(None, description="Name of the reporting radiologist")
    is_abnormal: bool = Field(False, description="Whether the study shows abnormal findings")


class ClinicalNote(BaseModel):
    """A clinical note from a healthcare provider."""

    note_date: date = Field(..., description="Date the note was written")
    provider: str = Field(..., description="Name of the healthcare provider")
    specialty: Optional[str] = Field(None, description="Provider specialty")
    subjective: str = Field(..., description="Patient-reported history and complaints")
    objective: str = Field(..., description="Physical examination findings and vital signs")
    assessment: str = Field(..., description="Clinical assessment and diagnoses")
    plan: str = Field(..., description="Treatment plan and follow-up instructions")
    diagnosis_codes: list[str] = Field(default_factory=list, description="ICD-10 diagnosis codes")


class Medication(BaseModel):
    """A medication in the patient's treatment history."""

    name: str = Field(..., description="Medication name (generic or brand)")
    dose: str = Field(..., description="Dose and frequency (e.g., '500 mg twice daily')")
    route: Optional[str] = Field(None, description="Route of administration (oral, IV, etc.)")
    start_date: Optional[date] = Field(None, description="Date medication was started")
    end_date: Optional[date] = Field(None, description="Date medication was stopped (if applicable)")
    indication: Optional[str] = Field(None, description="Medical indication for the medication")
    is_current: bool = Field(True, description="Whether medication is currently active")


class Visit(BaseModel):
    """A clinical visit record."""

    visit_date: date = Field(..., description="Date of the visit")
    visit_type: str = Field(..., description="Type of visit (e.g., Outpatient, Emergency, Inpatient)")
    provider: str = Field(..., description="Attending provider")
    facility: Optional[str] = Field(None, description="Healthcare facility name")
    chief_complaint: str = Field(..., description="Primary reason for the visit")
    diagnoses: list[str] = Field(default_factory=list, description="Diagnoses recorded at this visit")
    procedures: list[str] = Field(default_factory=list, description="Procedures performed")
    disposition: Optional[str] = Field(None, description="Patient disposition after visit")


class PatientRecord(BaseModel):
    """Complete patient clinical record used as input for report generation."""

    demographics: PatientDemographics
    symptoms: list[Symptom] = Field(default_factory=list)
    lab_results: list[LabResult] = Field(default_factory=list)
    imaging_reports: list[ImagingReport] = Field(default_factory=list)
    clinical_notes: list[ClinicalNote] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    visits: list[Visit] = Field(default_factory=list)
    chief_complaint: Optional[str] = Field(None, description="Primary presenting concern")
    report_requested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the report was requested",
    )


class ReportSections(BaseModel):
    """Structured sections of the clinical PDF report."""

    subjective: str = Field(..., description="Patient-reported history and symptoms (SOAP S)")
    objective: str = Field(..., description="Examination findings, labs, and imaging (SOAP O)")
    assessment: str = Field(..., description="Clinical assessment and diagnoses (SOAP A)")
    plan: str = Field(..., description="Treatment plan and recommendations (SOAP P)")
    patient_timeline: str = Field(..., description="Chronological visit and diagnosis timeline")
    key_findings: str = Field(..., description="Highlighted abnormal lab results and imaging")
    differential_diagnosis: str = Field(..., description="Differential diagnosis list with rationale")
    treatment_history: str = Field(..., description="Summary of past and current therapies")
    references: list[str] = Field(default_factory=list, description="Academic references cited")
