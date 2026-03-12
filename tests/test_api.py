"""Tests for the FastAPI report generation endpoints."""

from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


SAMPLE_PATIENT_PAYLOAD = {
    "demographics": {
        "patient_id": "P100",
        "name": "Alice Nguyen",
        "date_of_birth": "1990-04-25",
        "sex": "Female",
        "blood_type": "O+",
        "allergies": ["Sulfa drugs"],
    },
    "chief_complaint": "Persistent cough and fever",
    "symptoms": [
        {
            "description": "Cough",
            "onset_date": "2024-03-01",
            "severity": "moderate",
        },
        {
            "description": "Fever",
            "severity": "mild",
        },
    ],
    "lab_results": [
        {
            "test_name": "WBC",
            "value": 14.5,
            "unit": "x10^9/L",
            "reference_range_low": 4.0,
            "reference_range_high": 11.0,
            "status": "abnormal_high",
            "performed_date": "2024-03-05",
        }
    ],
    "imaging_reports": [
        {
            "modality": "Chest X-Ray",
            "body_region": "Thorax",
            "performed_date": "2024-03-05",
            "findings": "Right lower lobe consolidation",
            "impression": "Findings consistent with right lower lobe pneumonia",
            "is_abnormal": True,
        }
    ],
    "medications": [
        {
            "name": "Amoxicillin-Clavulanate",
            "dose": "875/125 mg twice daily",
            "indication": "Community-acquired pneumonia",
            "start_date": "2024-03-05",
            "is_current": True,
        }
    ],
    "visits": [
        {
            "visit_date": "2024-03-05",
            "visit_type": "Outpatient",
            "provider": "Dr. Smith",
            "chief_complaint": "Cough and fever",
            "diagnoses": ["Community-acquired pneumonia (J18.9)"],
        }
    ],
    "report_requested_at": "2024-03-06T09:00:00",
}


class TestHealthEndpoints:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ClinicaDoc AI"
        assert data["status"] == "running"

    def test_health_endpoint(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestReportSectionsEndpoint:
    def test_sections_returns_200(self):
        response = client.post("/report/sections", json=SAMPLE_PATIENT_PAYLOAD)
        assert response.status_code == 200

    def test_sections_returns_soap_fields(self):
        response = client.post("/report/sections", json=SAMPLE_PATIENT_PAYLOAD)
        data = response.json()
        assert "subjective" in data
        assert "objective" in data
        assert "assessment" in data
        assert "plan" in data

    def test_sections_returns_extended_fields(self):
        response = client.post("/report/sections", json=SAMPLE_PATIENT_PAYLOAD)
        data = response.json()
        assert "patient_timeline" in data
        assert "key_findings" in data
        assert "differential_diagnosis" in data
        assert "treatment_history" in data
        assert "references" in data

    def test_sections_key_findings_not_empty(self):
        response = client.post("/report/sections", json=SAMPLE_PATIENT_PAYLOAD)
        data = response.json()
        assert data["key_findings"] != ""

    def test_sections_references_list(self):
        response = client.post("/report/sections", json=SAMPLE_PATIENT_PAYLOAD)
        data = response.json()
        assert isinstance(data["references"], list)
        assert len(data["references"]) > 0

    def test_sections_invalid_payload(self):
        response = client.post("/report/sections", json={"invalid": "data"})
        assert response.status_code == 422


class TestGenerateReportEndpoint:
    def test_generate_returns_pdf(self):
        response = client.post("/report/generate", json=SAMPLE_PATIENT_PAYLOAD)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_generate_pdf_starts_with_header(self):
        response = client.post("/report/generate", json=SAMPLE_PATIENT_PAYLOAD)
        assert response.content[:4] == b"%PDF"

    def test_generate_pdf_non_empty(self):
        response = client.post("/report/generate", json=SAMPLE_PATIENT_PAYLOAD)
        assert len(response.content) > 1024

    def test_generate_content_disposition(self):
        response = client.post("/report/generate", json=SAMPLE_PATIENT_PAYLOAD)
        assert "content-disposition" in response.headers
        assert "P100" in response.headers["content-disposition"]

    def test_generate_invalid_payload(self):
        response = client.post("/report/generate", json={"bad": "data"})
        assert response.status_code == 422

    def test_generate_minimal_patient(self):
        """PDF generation works with only required fields."""
        minimal_payload = {
            "demographics": {
                "patient_id": "P_MIN",
                "name": "Minimal Patient",
                "date_of_birth": "1980-01-01",
                "sex": "Male",
            },
            "report_requested_at": "2024-01-01T00:00:00",
        }
        response = client.post("/report/generate", json=minimal_payload)
        assert response.status_code == 200
        assert response.content[:4] == b"%PDF"
