"""AI agent for generating clinical insights from patient data.

Uses LangChain with OpenAI to produce structured SOAP-format content,
differential diagnosis, key findings, and treatment recommendations.
Falls back to rule-based extraction when no API key is available.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.models.patient import LabStatus, PatientRecord, ReportSections

if TYPE_CHECKING:
    pass


def _build_patient_summary(record: PatientRecord) -> str:
    """Build a plain-text summary of the patient record for the LLM prompt."""
    demo = record.demographics
    lines: list[str] = [
        f"Patient: {demo.name}, DOB: {demo.date_of_birth}, Sex: {demo.sex}",
        f"Blood type: {demo.blood_type or 'Unknown'}",
        f"Allergies: {', '.join(demo.allergies) if demo.allergies else 'NKDA'}",
    ]

    if record.chief_complaint:
        lines.append(f"Chief complaint: {record.chief_complaint}")

    if record.symptoms:
        lines.append("\nSymptoms:")
        for s in record.symptoms:
            onset = f" (onset {s.onset_date})" if s.onset_date else ""
            sev = f", severity: {s.severity.value}" if s.severity else ""
            lines.append(f"  - {s.description}{onset}{sev}")

    if record.visits:
        lines.append("\nVisit history:")
        for v in sorted(record.visits, key=lambda x: x.visit_date):
            dx = ", ".join(v.diagnoses) if v.diagnoses else "None recorded"
            lines.append(f"  [{v.visit_date}] {v.visit_type} – {v.chief_complaint} | Dx: {dx}")

    if record.lab_results:
        lines.append("\nLaboratory results:")
        for lr in sorted(record.lab_results, key=lambda x: x.performed_date):
            flag = "" if lr.status == LabStatus.NORMAL else f" *** {lr.status.value.upper()} ***"
            lines.append(
                f"  [{lr.performed_date}] {lr.test_name}: {lr.value} {lr.unit}"
                f" (ref: {lr.reference_range_low}–{lr.reference_range_high}){flag}"
            )

    if record.imaging_reports:
        lines.append("\nImaging reports:")
        for ir in sorted(record.imaging_reports, key=lambda x: x.performed_date):
            flag = " [ABNORMAL]" if ir.is_abnormal else ""
            lines.append(
                f"  [{ir.performed_date}] {ir.modality} {ir.body_region}{flag}: {ir.impression}"
            )

    if record.clinical_notes:
        lines.append("\nClinical notes:")
        for cn in sorted(record.clinical_notes, key=lambda x: x.note_date):
            lines.append(
                f"  [{cn.note_date}] {cn.provider} ({cn.specialty or 'General'})\n"
                f"    Subjective: {cn.subjective}\n"
                f"    Objective:  {cn.objective}\n"
                f"    Assessment: {cn.assessment}\n"
                f"    Plan:       {cn.plan}"
            )

    if record.medications:
        lines.append("\nMedications:")
        for med in record.medications:
            status = "Current" if med.is_current else "Discontinued"
            lines.append(f"  - [{status}] {med.name} {med.dose} | Indication: {med.indication or 'N/A'}")

    return "\n".join(lines)


def _rule_based_sections(record: PatientRecord) -> ReportSections:
    """Generate report sections using rule-based extraction (no LLM required)."""
    demo = record.demographics

    # ── Subjective ─────────────────────────────────────────────────────────────
    subjective_parts = [f"Patient {demo.name} presents"]
    if record.chief_complaint:
        subjective_parts[0] += f" with {record.chief_complaint}."
    else:
        subjective_parts[0] += "."

    if record.symptoms:
        symptom_list = "; ".join(
            f"{s.description} (onset {s.onset_date})" if s.onset_date else s.description
            for s in record.symptoms
        )
        subjective_parts.append(f"Reported symptoms include: {symptom_list}.")

    if demo.allergies:
        subjective_parts.append(f"Known allergies: {', '.join(demo.allergies)}.")
    else:
        subjective_parts.append("No known drug allergies (NKDA).")

    # ── Objective ──────────────────────────────────────────────────────────────
    objective_parts: list[str] = []
    if record.lab_results:
        abnormal = [lr for lr in record.lab_results if lr.status != LabStatus.NORMAL]
        normal = [lr for lr in record.lab_results if lr.status == LabStatus.NORMAL]
        if abnormal:
            ab_str = "; ".join(
                f"{lr.test_name} {lr.value} {lr.unit} ({lr.status.value})" for lr in abnormal
            )
            objective_parts.append(f"Notable laboratory abnormalities: {ab_str}.")
        if normal:
            nm_str = ", ".join(f"{lr.test_name}" for lr in normal)
            objective_parts.append(f"Laboratory results within normal limits: {nm_str}.")

    if record.imaging_reports:
        for ir in record.imaging_reports:
            flag = "Abnormal" if ir.is_abnormal else "Normal"
            objective_parts.append(
                f"[{ir.modality} – {ir.body_region}] {flag}: {ir.findings}"
            )

    if record.clinical_notes:
        latest_note = max(record.clinical_notes, key=lambda n: n.note_date)
        objective_parts.append(f"Examination per {latest_note.provider}: {latest_note.objective}")

    # ── Assessment ─────────────────────────────────────────────────────────────
    all_diagnoses: list[str] = []
    for v in record.visits:
        all_diagnoses.extend(v.diagnoses)
    for cn in record.clinical_notes:
        all_diagnoses.extend(cn.diagnosis_codes)

    unique_dx = list(dict.fromkeys(all_diagnoses))
    assessment_parts: list[str] = []
    if unique_dx:
        assessment_parts.append(f"Active diagnoses: {'; '.join(unique_dx)}.")
    if record.clinical_notes:
        latest_note = max(record.clinical_notes, key=lambda n: n.note_date)
        assessment_parts.append(f"Clinical assessment: {latest_note.assessment}")

    # ── Plan ───────────────────────────────────────────────────────────────────
    plan_parts: list[str] = []
    if record.medications:
        current_meds = [m for m in record.medications if m.is_current]
        if current_meds:
            med_str = "; ".join(f"{m.name} {m.dose}" for m in current_meds)
            plan_parts.append(f"Current medications: {med_str}.")
    if record.clinical_notes:
        latest_note = max(record.clinical_notes, key=lambda n: n.note_date)
        plan_parts.append(f"Plan: {latest_note.plan}")

    # ── Patient Timeline ───────────────────────────────────────────────────────
    timeline_events: list[tuple] = []
    for v in record.visits:
        dx = ", ".join(v.diagnoses) if v.diagnoses else "No diagnoses recorded"
        timeline_events.append((v.visit_date, f"{v.visit_type} visit with {v.provider}: {v.chief_complaint} | Dx: {dx}"))
    for cn in record.clinical_notes:
        timeline_events.append((cn.note_date, f"Clinical note by {cn.provider}: {cn.assessment}"))

    timeline_events.sort(key=lambda x: x[0])
    timeline_lines = [f"• {e[0]}: {e[1]}" for e in timeline_events] if timeline_events else ["No visit history recorded."]

    # ── Key Findings ───────────────────────────────────────────────────────────
    findings_lines: list[str] = []
    abnormal_labs = [lr for lr in record.lab_results if lr.status != LabStatus.NORMAL]
    for lr in abnormal_labs:
        ref = f"(ref: {lr.reference_range_low}–{lr.reference_range_high} {lr.unit})"
        findings_lines.append(
            f"• [{lr.performed_date}] {lr.test_name}: {lr.value} {lr.unit} – {lr.status.value.upper()} {ref}"
        )
    for ir in record.imaging_reports:
        if ir.is_abnormal:
            findings_lines.append(
                f"• [{ir.performed_date}] {ir.modality} {ir.body_region} ABNORMAL: {ir.impression}"
            )
    if not findings_lines:
        findings_lines.append("No significant abnormal findings identified.")

    # ── Differential Diagnosis ─────────────────────────────────────────────────
    diff_dx_lines: list[str] = []
    if unique_dx:
        for i, dx in enumerate(unique_dx[:5], 1):
            diff_dx_lines.append(f"{i}. {dx} – based on clinical presentation and diagnostic workup.")
    else:
        diff_dx_lines.append(
            "Differential diagnosis requires additional clinical data. "
            "Consider further workup based on presenting symptoms."
        )

    # ── Treatment History ──────────────────────────────────────────────────────
    treatment_lines: list[str] = []
    for med in record.medications:
        status = "Active" if med.is_current else "Discontinued"
        dates = ""
        if med.start_date:
            dates = f" (started {med.start_date}"
            if med.end_date:
                dates += f", stopped {med.end_date}"
            dates += ")"
        treatment_lines.append(
            f"• [{status}] {med.name} {med.dose}{dates} | Indication: {med.indication or 'N/A'}"
        )
    if not treatment_lines:
        treatment_lines.append("No medication history recorded.")

    # ── References ─────────────────────────────────────────────────────────────
    references = [
        "Weed LL. Medical records that guide and teach. N Engl J Med. 1968;278(11):593-600.",
        "Dolin RH, et al. HL7 Clinical Document Architecture. J Am Med Inform Assoc. 2006;13(1):30-39.",
        "WHO ICD-10: International Statistical Classification of Diseases (10th Revision). Geneva: WHO, 2016.",
        "Kasper DL, et al. Harrison's Principles of Internal Medicine. 21st ed. McGraw-Hill, 2022.",
    ]

    return ReportSections(
        subjective=" ".join(subjective_parts),
        objective=" ".join(objective_parts) if objective_parts else "No objective data provided.",
        assessment=" ".join(assessment_parts) if assessment_parts else "Assessment pending further evaluation.",
        plan=" ".join(plan_parts) if plan_parts else "Plan to be determined following further assessment.",
        patient_timeline="\n".join(timeline_lines),
        key_findings="\n".join(findings_lines),
        differential_diagnosis="\n".join(diff_dx_lines),
        treatment_history="\n".join(treatment_lines),
        references=references,
    )


def _llm_sections(record: PatientRecord, api_key: str) -> ReportSections:
    """Generate report sections using an OpenAI LLM via LangChain."""
    from langchain.output_parsers import PydanticOutputParser
    from langchain.prompts import PromptTemplate
    from langchain_openai import ChatOpenAI

    parser = PydanticOutputParser(pydantic_object=ReportSections)
    format_instructions = parser.get_format_instructions()

    template = """You are an expert clinical documentation AI assistant.
Given the following patient clinical record, generate a comprehensive, structured clinical report.

Patient Record:
{patient_summary}

Generate the report in the following JSON format:
{format_instructions}

Guidelines:
- subjective: Summarise patient-reported history, symptoms, and chief complaint (SOAP S).
- objective: Summarise examination findings, laboratory results, and imaging (SOAP O).
- assessment: Provide clinical assessment and primary diagnoses (SOAP A).
- plan: Outline the treatment plan and follow-up recommendations (SOAP P).
- patient_timeline: List chronological events as bullet points (• date: event).
- key_findings: List abnormal lab values and imaging findings as bullet points.
- differential_diagnosis: List up to 5 differential diagnoses with brief rationale.
- treatment_history: Summarise past and current medications and interventions.
- references: Include 3-5 relevant peer-reviewed references supporting the assessment.

Respond ONLY with valid JSON. Do not include markdown code fences.
"""

    prompt = PromptTemplate(
        template=template,
        input_variables=["patient_summary"],
        partial_variables={"format_instructions": format_instructions},
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, openai_api_key=api_key)
    chain = prompt | llm | parser

    patient_summary = _build_patient_summary(record)
    return chain.invoke({"patient_summary": patient_summary})


def generate_report_sections(record: PatientRecord) -> ReportSections:
    """Generate structured SOAP report sections from a patient record.

    Uses the OpenAI LLM when ``OPENAI_API_KEY`` is set in the environment,
    otherwise falls back to deterministic rule-based extraction.

    Args:
        record: Complete patient clinical record.

    Returns:
        Structured ``ReportSections`` object ready for PDF rendering.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if api_key:
        try:
            return _llm_sections(record, api_key)
        except Exception:
            # Fall back to rule-based extraction on any LLM error
            pass
    return _rule_based_sections(record)
