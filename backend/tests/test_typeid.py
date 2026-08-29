"""Unit tests for FHIR-compliant TypeID (Base32 Crockford + UUIDv7) standardization.

Validates:
- Type-safe prefix formatting with hyphen separator ('pat-01h...', 'rec-01h...')
- Crockford Base32 26-character suffix encoding (excludes i, l, o, u)
- Monotonic K-sortability (chronological ordering)
- Deterministic TypeID generation for idempotent mapping
- HL7 FHIR R4 Section 2.1 ID compliance (regex ^[A-Za-z0-9\\-\\.]{1,64}$)
"""

import re
import time

import pytest
from app.core.typeid import (
    CROCKFORD_BASE32_PATTERN,
    TypeIDPrefix,
    TypeIDStr,
    from_fhir_id,
    generate_deterministic_id,
    generate_id,
    parse_id,
    to_fhir_id,
    validate_id,
)
from fhir.resources.patient import Patient
from pydantic import BaseModel, ValidationError


def test_typeid_generation_format_and_prefix():
    """Validates that generate_id produces valid <prefix>-<suffix> TypeIDs with Crockford Base32."""
    for prefix in TypeIDPrefix:
        tid_str = generate_id(prefix)
        p, s = parse_id(tid_str)

        assert p == prefix.value
        assert len(s) == 26
        assert re.match(CROCKFORD_BASE32_PATTERN, s) is not None
        assert validate_id(tid_str) is True
        assert validate_id(tid_str, expected_prefix=prefix) is True
        assert validate_id(tid_str, expected_prefix="wrong_prefix") is False
        assert tid_str.startswith(f"{prefix.value}-")


def test_typeid_monotonic_k_sortability():
    """Validates that TypeIDs generated over time sort chronologically (K-sortable UUIDv7 property)."""
    ids = []
    for _ in range(5):
        ids.append(generate_id(TypeIDPrefix.RECORD))
        time.sleep(0.005)  # 5ms delay to advance UUIDv7 millisecond timestamp

    sorted_ids = sorted(ids)
    assert ids == sorted_ids, f"TypeIDs are not monotonically ordered: {ids}"


def test_crockford_base32_character_restrictions():
    """Validates that ambiguous letters (i, l, o, u) and malformed strings are rejected."""
    # Suffixes with invalid Crockford characters (i, l, o, u)
    invalid_chars_id = "rec-01h455vb4pex5v7bmfcmgrhsiu"
    assert validate_id(invalid_chars_id) is False

    with pytest.raises(ValueError, match="Invalid Crockford Base32"):
        parse_id(invalid_chars_id)

    # Malformed length (25 instead of 26)
    too_short_id = "rec-01h455vb4pex5v7bmfcmgrhs"
    assert validate_id(too_short_id) is False

    # Invalid uppercase prefix
    assert validate_id("REC-01m17dxzwwft0rxrt6e8036kcv") is False


def test_deterministic_id_generation():
    """Validates that generate_deterministic_id produces idempotent TypeIDs from seed keys."""
    mrn = "MRN-88401"
    id1 = generate_deterministic_id(TypeIDPrefix.PATIENT, mrn)
    id2 = generate_deterministic_id(TypeIDPrefix.PATIENT, mrn)
    id_whitespace = generate_deterministic_id(TypeIDPrefix.PATIENT, "  mrn-88401  ")

    assert id1 == id2
    assert id1 == id_whitespace
    assert id1.startswith("pat-")
    assert len(id1.split("-")[1]) == 26

    # Different seeds produce different IDs
    id_different = generate_deterministic_id(TypeIDPrefix.PATIENT, "MRN-99302")
    assert id1 != id_different


def test_fhir_id_compliance():
    """Validates that generated TypeIDs comply 100% with HL7 FHIR R4 ID specification."""
    pat_id = generate_id(TypeIDPrefix.PATIENT)

    # FHIR ID must use hyphens instead of underscores
    assert "_" not in pat_id
    assert "-" in pat_id
    assert pat_id.startswith("pat-")

    # Complies with HL7 FHIR R4 id regex: ^[A-Za-z0-9\-\.]+$
    assert re.match(r"^[A-Za-z0-9\-.]+$", pat_id) is not None

    # Validates natively inside a fhir.resources.patient.Patient resource
    patient = Patient.model_validate(
        {"id": pat_id, "gender": "male", "birthDate": "1980-01-01"}
    )
    assert patient.id == pat_id

    # Bidirectional helpers preserve FHIR ID
    assert to_fhir_id(pat_id) == pat_id
    assert from_fhir_id(pat_id) == pat_id
    assert validate_id(pat_id, TypeIDPrefix.PATIENT) is True


def test_pydantic_typeid_annotation():
    """Validates that TypeIDStr works as a strict Pydantic field validator."""

    class TestPayload(BaseModel):
        record_id: TypeIDStr

    valid_id = generate_id(TypeIDPrefix.RECORD)
    m = TestPayload(record_id=valid_id)
    assert m.record_id == valid_id

    with pytest.raises(ValidationError):
        TestPayload(record_id="not_a_valid_typeid")
