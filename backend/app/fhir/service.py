from collections import defaultdict
from datetime import datetime, timezone

from app.fhir.mapper import FHIRMapper
from app.fhir.models import FHIRBundle, FHIRValidationReport
from app.ingestion.models import CleanRecord
from sqlmodel import Session, col, select


class FHIRService:
    @classmethod
    def normalize_and_store_all(cls, session: Session) -> FHIRValidationReport:
        """
        Reads all clean records from the database, groups by patient,
        maps to validated FHIR R4 Bundles, and persists them into the database.
        """
        statement = select(CleanRecord).order_by(col(CleanRecord.encounter_date).asc())
        all_records = session.exec(statement).all()

        if not all_records:
            return FHIRValidationReport(
                total_patients=0,
                total_bundles_created=0,
                total_resources_mapped=0,
                errors=["No clean records available in database to normalize"],
            )

        grouped_records: dict[str, list[CleanRecord]] = defaultdict(list)
        for rec in all_records:
            grouped_records[rec.patient_mrn].append(rec)

        all_errors: list[str] = []
        bundles_created = 0
        total_resources = 0

        for mrn, patient_records in grouped_records.items():
            bundle, errors = FHIRMapper.assemble_patient_bundle(mrn, patient_records)
            all_errors.extend(errors)

            if bundle and bundle.entry:
                patient_name = patient_records[0].patient_name
                first_entry_resource = bundle.entry[0].resource
                patient_id = (
                    str(first_entry_resource.id)
                    if first_entry_resource and first_entry_resource.id
                    else f"pat-{mrn}"
                )
                if not bundle.id:
                    raise ValueError(
                        f"FHIR Bundle for patient {mrn} was generated without an ID."
                    )

                bundle_id: str = str(bundle.id)
                resource_count = len(bundle.entry)
                bundle_json = bundle.model_dump_json()

                existing = session.get(FHIRBundle, bundle_id)
                if existing:
                    existing.patient_mrn = mrn
                    existing.patient_name = patient_name
                    existing.patient_id = patient_id
                    existing.resource_count = resource_count
                    existing.bundle_json = bundle_json
                    existing.updated_at = datetime.now(timezone.utc)
                    session.add(existing)
                else:
                    db_bundle = FHIRBundle(
                        id=bundle_id,
                        patient_mrn=mrn,
                        patient_id=patient_id,
                        patient_name=patient_name,
                        resource_count=resource_count,
                        validation_status="VALID",
                        bundle_json=bundle_json,
                    )
                    session.add(db_bundle)

                bundles_created += 1
                total_resources += resource_count

        session.commit()

        return FHIRValidationReport(
            total_patients=len(grouped_records),
            total_bundles_created=bundles_created,
            total_resources_mapped=total_resources,
            errors=all_errors,
        )

    @classmethod
    def get_bundle_by_mrn(cls, session: Session, mrn: str) -> FHIRBundle | None:
        statement = select(FHIRBundle).where(
            col(FHIRBundle.patient_mrn) == mrn.strip().upper()
        )
        return session.exec(statement).first()
