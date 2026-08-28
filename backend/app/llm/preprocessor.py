import base64
import json
import re
from datetime import date, datetime


class ClinicalDeidentifier:
    @staticmethod
    def _calculate_age(birth_date_str: str | None) -> str:
        """Calculates age and enforces the HIPAA Age > 89 Safe Harbor rule."""
        if not birth_date_str:
            return "Adult"
        try:
            b_date = datetime.strptime(birth_date_str[:10], "%Y-%m-%d").date()
            today = date.today()
            age = (
                today.year
                - b_date.year
                - ((today.month, today.day) < (b_date.month, b_date.day))
            )
            if age >= 90:
                return "90+ years old"
            return f"{age} years old"
        except Exception:
            return "Adult"

    @staticmethod
    def scrub_text(text: str, patient_names: list[str] | None = None) -> str:
        """Removes PHI patterns and known patient names from free-text narratives."""
        # Scrub known patient names dynamically extracted from the Patient resource
        if patient_names:
            for name in patient_names:
                if len(name.strip()) >= 2:
                    pattern = re.compile(re.escape(name.strip()), re.IGNORECASE)
                    text = pattern.sub("[REDACTED_NAME]", text)

        text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[REDACTED_EMAIL]", text)
        text = re.sub(r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b", "[REDACTED_PHONE]", text)
        text = re.sub(r"MRN-?\d+", "[REDACTED_MRN]", text, flags=re.IGNORECASE)

        return text.strip()

    @classmethod
    def extract_deidentified_context(cls, bundle_json_str: str) -> str:
        """
        Parses a FHIR R4 Bundle, extracts demographics and patient names,
        scrubs PHI from all narrative text, and builds the de-identified clinical timeline.
        """
        bundle = json.loads(bundle_json_str)
        entries = bundle.get("entry", [])
        if not entries:
            return ""

        demographics_header = "PATIENT CONTEXT: "
        patient_names: list[str] = []
        narratives: list[str] = []

        # Extract Patient demographics and names for scrubbing
        for entry in entries:
            res = entry.get("resource", {})
            if res.get("resourceType") == "Patient":
                gender = res.get("gender", "unknown").capitalize()
                birth_date = res.get("birthDate")
                age_str = cls._calculate_age(birth_date)
                demographics_header += f"{age_str}, {gender}."

                names = res.get("name", [])
                for name_obj in names:
                    if name_obj.get("family"):
                        patient_names.append(name_obj["family"])
                    for given in name_obj.get("given", []):
                        if given:
                            patient_names.append(given)

        # Extract notes and reports, applying PHI scrubbing
        for entry in entries:
            res = entry.get("resource", {})
            res_type = res.get("resourceType")

            if res_type == "DocumentReference":
                doc_type = res.get("type", {}).get("text", "Clinical Note")
                doc_date = (res.get("date") or "")[:10]
                content_list = res.get("content", [])
                raw_text = ""
                if content_list:
                    b64_data = content_list[0].get("attachment", {}).get("data", "")
                    try:
                        raw_text = base64.b64decode(b64_data).decode("utf-8")
                    except Exception:
                        raw_text = b64_data

                clean_text = cls.scrub_text(raw_text, patient_names)
                if clean_text:
                    narratives.append(f"[{doc_date}] {doc_type}: {clean_text}")

            elif res_type == "DiagnosticReport":
                report_title = res.get("code", {}).get("text", "Diagnostic Report")
                rep_date = (res.get("effectiveDateTime") or "")[:10]
                raw_conclusion = res.get("conclusion") or ""
                conclusion = cls.scrub_text(raw_conclusion, patient_names)
                if conclusion:
                    narratives.append(f"[{rep_date}] {report_title}: {conclusion}")

        if not narratives:
            return ""

        return f"{demographics_header}\n\nCLINICAL TIMELINE & FINDINGS:\n" + "\n".join(
            narratives
        )
