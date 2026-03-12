# ClinicaDoc-AI

ClinicaDoc AI is an intelligent, secure, and conversational AI agent designed to act as a bridge between patient history and actionable clinical insights. It ingests scattered patient data—including clinical notes, lab results, imaging reports, and patient-reported symptoms—and produces a structured, concise, and academically referenced PDF report.

This tool helps doctors quickly grasp the full context of a disease, reducing the time spent on manual record review.

---

## Features

- **Comprehensive PDF Report Generation** — Produces a structured PDF in standard **SOAP format** (Subjective, Objective, Assessment, Plan)
- **Patient Timeline** — Chronological overview of visits and diagnoses
- **Key Findings** — Highlighted abnormal lab results and imaging findings
- **Differential Diagnosis Support** — Based on clinical evidence
- **Treatment History & Recommendations** — Summary of past therapies and current medications
- **AI-Powered Insights** — Uses OpenAI GPT-4o-mini when an API key is available, with intelligent rule-based fallback
- **Academic References** — Peer-reviewed references included in every report
- **REST API** — FastAPI application with interactive Swagger docs

---

## Project Structure

```
ClinicaDoc-AI/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── models/
│   │   └── patient.py           # Pydantic models (PatientRecord, ReportSections, …)
│   ├── services/
│   │   ├── ai_agent.py          # AI agent (LLM + rule-based fallback)
│   │   └── pdf_generator.py     # PDF report builder (ReportLab)
│   └── routers/
│       └── report.py            # API endpoints
├── tests/
│   ├── test_models.py           # Patient data model tests
│   ├── test_ai_agent.py         # AI agent / section generation tests
│   ├── test_pdf_generator.py    # PDF generation tests
│   └── test_api.py              # FastAPI endpoint tests
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Running the API server

```bash
uvicorn app.main:app --reload
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

### Optional: AI-enhanced reports

Set an OpenAI API key to enable GPT-4o-mini-powered report generation:

```bash
export OPENAI_API_KEY="sk-..."
uvicorn app.main:app --reload
```

Without the key the service falls back to deterministic rule-based extraction—no AI dependency required.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Detailed health status |
| `POST` | `/report/generate` | Generate and download a clinical PDF report |
| `POST` | `/report/sections` | Return structured SOAP sections as JSON |

### Example request

```bash
curl -X POST http://localhost:8000/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "demographics": {
      "patient_id": "P001",
      "name": "Jane Doe",
      "date_of_birth": "1985-06-15",
      "sex": "Female",
      "blood_type": "A+",
      "allergies": ["Penicillin"]
    },
    "chief_complaint": "Chest pain and shortness of breath",
    "symptoms": [
      {"description": "Chest pain", "onset_date": "2024-03-10", "severity": "severe"},
      {"description": "Dyspnoea", "severity": "moderate"}
    ],
    "lab_results": [
      {
        "test_name": "Troponin I",
        "value": 2.4,
        "unit": "ng/mL",
        "reference_range_low": 0.0,
        "reference_range_high": 0.04,
        "status": "abnormal_high",
        "performed_date": "2024-03-10"
      }
    ],
    "imaging_reports": [
      {
        "modality": "ECG",
        "body_region": "Heart",
        "performed_date": "2024-03-10",
        "findings": "ST-segment elevation in leads II, III, aVF",
        "impression": "Inferior STEMI",
        "is_abnormal": true
      }
    ],
    "medications": [
      {
        "name": "Aspirin",
        "dose": "300 mg loading dose",
        "indication": "ACS",
        "is_current": true
      }
    ],
    "visits": [
      {
        "visit_date": "2024-03-10",
        "visit_type": "Emergency",
        "provider": "Dr. Johnson",
        "chief_complaint": "Chest pain",
        "diagnoses": ["Inferior STEMI (I21.1)"]
      }
    ]
  }' \
  --output report.pdf
```

---

## PDF Report Structure

Each generated report contains:

1. **Patient Information** — Demographics, blood type, allergies, report date
2. **S – Subjective** — Patient-reported history, symptoms, chief complaint
3. **O – Objective** — Examination findings, laboratory results, imaging
4. **A – Assessment** — Clinical diagnoses and assessments
5. **P – Plan** — Treatment plan and follow-up instructions
6. **Patient Timeline** — Chronological event overview
7. **Key Findings** — Highlighted abnormal results (in red)
8. **Differential Diagnosis** — Evidence-based differential list
9. **Treatment History & Recommendations** — Medication and intervention history
10. **References** — Peer-reviewed academic citations

---

## Running Tests

```bash
pytest tests/ -v
```

All 51 tests cover models, AI agent, PDF generation, and API endpoints.

---

## Data Models

The application accepts a `PatientRecord` JSON object containing:

| Field | Description |
|-------|-------------|
| `demographics` | Patient ID, name, DOB, sex, blood type, allergies |
| `symptoms` | Patient-reported symptoms with onset, severity, and duration |
| `lab_results` | Lab tests with values, units, and reference ranges |
| `imaging_reports` | Radiology reports with findings, impression, and abnormality flag |
| `clinical_notes` | SOAP-structured clinical notes per visit |
| `medications` | Medication history with active/discontinued status |
| `visits` | Visit history with type, provider, diagnoses, and procedures |
| `chief_complaint` | Primary presenting concern |

---

## License

MIT

