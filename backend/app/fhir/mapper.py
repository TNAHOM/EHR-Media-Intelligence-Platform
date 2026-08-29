import base64
import re
from datetime import timezone

from app.core.typeid import TypeIDPrefix, generate_deterministic_id, to_fhir_id
from app.ingestion.models import CleanRecord
from fhir.resources.attachment import Attachment
from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.documentreference import DocumentReference, DocumentReferenceContent
from fhir.resources.patient import Patient
from fhir.resources.reference import Reference


class FHIRMapper:
    @staticmethod
    def _sanitize_id(raw_id: str) -> str:
        r"""Sanitizes strings to comply with FHIR ID regex [A-Za-z0-9\-\.]{1,64}"""
        return re.sub(r"[^A-Za-z0-9\-\.]", "-", raw_id.strip()).strip("-")

    @classmethod
    def get_patient_id(cls, patient_mrn: str) -> str:
        """Standardized patient TypeID generator (FHIR R4 compliant pat-<base32_uuid>)."""
        tid = generate_deterministic_id(TypeIDPrefix.PATIENT, patient_mrn)
        return to_fhir_id(tid)

    @classmethod
    def build_patient_resource(cls, record: CleanRecord) -> Patient:
        """Constructs a valid HL7 FHIR R4 Patient resource."""
        patient_id = cls.get_patient_id(record.patient_mrn)

        name_parts = record.patient_name.split()
        family_name = name_parts[-1] if len(name_parts) > 1 else record.patient_name
        given_names = name_parts[:-1] if len(name_parts) > 1 else [record.patient_name]

        birth_date_str = (
            record.dob.isoformat()
            if hasattr(record.dob, "isoformat")
            else str(record.dob)
        )

        return Patient.model_validate(
            {
                "id": patient_id,
                "identifier": [
                    {
                        "system": "http://hospital.smarthealth.org/mrn",
                        "value": record.patient_mrn,
                    }
                ],
                "name": [
                    {
                        "family": family_name,
                        "given": given_names,
                    }
                ],
                "gender": record.gender,
                "birthDate": birth_date_str,
            }
        )

    @classmethod
    def build_document_reference(
        cls, record: CleanRecord, patient_id: str
    ) -> DocumentReference:
        """Constructs a valid HL7 FHIR R4 DocumentReference for unstructured notes/summaries."""
        doc_id = to_fhir_id(generate_deterministic_id(TypeIDPrefix.DOCUMENT, record.id))

        encoded_payload = base64.b64encode(record.content_text.encode("utf-8")).decode(
            "utf-8"
        )

        type_code = (
            "18842-5" if record.record_type == "discharge_summary" else "11488-4"
        )
        type_display = (
            "Discharge Summary"
            if record.record_type == "discharge_summary"
            else "Consultation Note"
        )

        enc_date = record.encounter_date
        if enc_date.tzinfo is None:
            enc_date = enc_date.replace(tzinfo=timezone.utc)

        return DocumentReference(
            id=doc_id,
            status="current",
            docStatus="final",
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="http://loinc.org",
                        code=type_code,
                        display=type_display,
                    )
                ],
                text=type_display,
            ),
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category",
                            code="clinical-note",
                            display="Clinical Note",
                        )
                    ]
                )
            ],
            subject=Reference(reference=f"Patient/{patient_id}"),
            date=enc_date,
            content=[
                DocumentReferenceContent(
                    attachment=Attachment.model_validate(
                        {
                            "contentType": "text/plain",
                            "data": encoded_payload,
                            "title": f"{type_display} - {enc_date.date()}",
                        }
                    )
                )
            ],
        )

    @classmethod
    def build_diagnostic_report(
        cls, record: CleanRecord, patient_id: str
    ) -> DiagnosticReport:
        """Constructs a valid HL7 FHIR R4 DiagnosticReport for imaging scans and lab panels."""
        report_id = to_fhir_id(
            generate_deterministic_id(TypeIDPrefix.DIAGNOSTIC, record.id)
        )

        is_imaging = record.record_type == "imaging"
        category_code = "RAD" if is_imaging else "LAB"
        category_display = "Radiology" if is_imaging else "Laboratory"

        enc_date = record.encounter_date
        if enc_date.tzinfo is None:
            enc_date = enc_date.replace(tzinfo=timezone.utc)

        return DiagnosticReport(
            id=report_id,
            status="final",
            category=[
                CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v2-0074",
                            code=category_code,
                            display=category_display,
                        )
                    ]
                )
            ],
            code=CodeableConcept(text=f"{category_display} Findings - {record.id}"),
            subject=Reference(reference=f"Patient/{patient_id}"),
            effectiveDateTime=enc_date,
            conclusion=record.content_text,
        )

    @classmethod
    def assemble_patient_bundle(
        cls, patient_mrn: str, records: list[CleanRecord]
    ) -> tuple[Bundle | None, list[str]]:
        """
        Takes all clean records for a single patient, constructs resources,
        and packages them into a validated FHIR Bundle of type 'collection'.
        """
        errors: list[str] = []
        if not records:
            return None, ["No records provided to construct bundle"]

        # 1. Build Base Patient Resource
        try:
            patient_resource = cls.build_patient_resource(records[0])
            patient_id = str(patient_resource.id or cls.get_patient_id(patient_mrn))
        except Exception as e:
            return None, [f"Failed to create Patient for {patient_mrn}: {str(e)}"]

        entries: list[BundleEntry] = [
            BundleEntry(
                fullUrl=f"urn:uuid:{patient_id}",
                resource=patient_resource,
            )
        ]

        # 2. Build associated DocumentReferences and DiagnosticReports
        for rec in records:
            try:
                if rec.record_type in ["clinical_note", "discharge_summary"]:
                    doc_res = cls.build_document_reference(rec, patient_id)
                    entries.append(
                        BundleEntry(
                            fullUrl=f"urn:uuid:{doc_res.id}",
                            resource=doc_res,
                        )
                    )
                elif rec.record_type in ["lab", "imaging"]:
                    diag_res = cls.build_diagnostic_report(rec, patient_id)
                    entries.append(
                        BundleEntry(
                            fullUrl=f"urn:uuid:{diag_res.id}",
                            resource=diag_res,
                        )
                    )
            except Exception as ex:
                errors.append(
                    f"Error mapping record {rec.id} ({rec.record_type}): {str(ex)}"
                )

        bundle_id = to_fhir_id(
            generate_deterministic_id(TypeIDPrefix.BUNDLE, patient_mrn)
        )
        bundle = Bundle(
            id=bundle_id,
            type="collection",
            entry=entries,
        )

        return bundle, errors
