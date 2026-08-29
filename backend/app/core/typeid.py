import os
import re
import time
import uuid
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator


# Canonical prefixes for healthcare entities
class TypeIDPrefix(StrEnum):
    """Canonical prefixes for entities in the EHR Media Intelligence Platform."""

    RECORD = "rec"  # Ingested clean clinical records (CleanRecord)
    PATIENT = "pat"  # Canonical patient identifier (FHIR Patient)
    BUNDLE = "bundle"  # FHIR R4 Bundle container
    SUMMARY = "sum"  # AI-generated clinical summary (ClinicalSummaryTable)
    AUDIT = "audit"  # Ingestion cleaning audit trail entries (AuditLog)
    DOCUMENT = "doc"  # FHIR DocumentReference resources
    DIAGNOSTIC = "diag"  # FHIR DiagnosticReport resources


# Crockford's Base32 alphabet (excludes ambiguous I, L, O, U)
CROCKFORD_BASE32 = "0123456789abcdefghjkmnpqrstvwxyz"
CROCKFORD_BASE32_SET = set(CROCKFORD_BASE32)
CROCKFORD_BASE32_PATTERN = r"^[0-9a-z]{26}$"
FHIR_TYPEID_PATTERN = r"^([a-z]{1,63})[-_]([0-9a-z]{26})$"

# Custom UUIDv5 namespace for deterministic healthcare entity TypeIDs
EHR_TYPEID_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _encode_128bit_crockford(val: int) -> str:
    """Encodes a 128-bit integer into 26 Crockford Base32 characters."""
    chars = [CROCKFORD_BASE32[(val >> (5 * i)) & 0x1F] for i in reversed(range(26))]
    return "".join(chars)


def generate_id(prefix: str | TypeIDPrefix) -> str:
    """Generates a FHIR-compliant, K-sortable TypeID string (prefix-CrockfordBase32UUIDv7).

    Structure:
    1. 48-bit timestamp in milliseconds (monotonically increasing)
    2. 80 bits of cryptographic randomness
    3. 26 characters of Crockford Base32 encoding
    4. Hyphen separator for 100% FHIR R4 compliance

    Example:
        >>> generate_id(TypeIDPrefix.PATIENT)
        'pat-01h455vb4pex5v7bmfc56e0m8n'
    """
    p_str = str(prefix.value if isinstance(prefix, TypeIDPrefix) else prefix).lower()

    # 1. 48-bit Unix timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)
    # 2. 80 bits of cryptographic randomness
    rand_bytes = os.urandom(10)

    # 3. Combine into 128-bit integer (UUIDv7 structure)
    val = (timestamp_ms << 80) | int.from_bytes(rand_bytes, "big")

    encoded_suffix = _encode_128bit_crockford(val)
    return f"{p_str}-{encoded_suffix}"


def generate_deterministic_id(prefix: str | TypeIDPrefix, key: str) -> str:
    """Generates a deterministic, idempotent TypeID from a seed key (e.g. MRN or content hash).

    Useful for consistent patient and bundle identification across repeated ingestion cycles.
    """
    p_str = str(prefix.value if isinstance(prefix, TypeIDPrefix) else prefix).lower()
    deterministic_uuid = uuid.uuid5(EHR_TYPEID_NAMESPACE, key.strip().upper())
    encoded_suffix = _encode_128bit_crockford(
        int.from_bytes(deterministic_uuid.bytes, "big")
    )
    return f"{p_str}-{encoded_suffix}"


def parse_id(typeid_str: str) -> tuple[str, str]:
    """Parses a TypeID string into (prefix, suffix).

    Accepts both hyphen-separated ('pat-...') and underscore-separated ('pat_...').
    Raises ValueError if format or characters are invalid.
    """
    if not isinstance(typeid_str, str):
        raise ValueError(f"Expected string, got {type(typeid_str).__name__}")

    raw = typeid_str.strip()
    match = re.match(FHIR_TYPEID_PATTERN, raw)
    if not match:
        raise ValueError(f"Invalid TypeID format: '{typeid_str}'")

    prefix, suffix = match.group(1), match.group(2)
    if any(c not in CROCKFORD_BASE32_SET for c in suffix):
        raise ValueError(
            f"Invalid Crockford Base32 characters in TypeID suffix: '{suffix}'"
        )

    return prefix, suffix


def validate_id(
    typeid_str: str, expected_prefix: str | TypeIDPrefix | None = None
) -> bool:
    """Returns True if the string is a valid TypeID with optional prefix verification."""
    if not isinstance(typeid_str, str):
        return False

    try:
        prefix, suffix = parse_id(typeid_str)
        if expected_prefix:
            exp = str(
                expected_prefix.value
                if isinstance(expected_prefix, TypeIDPrefix)
                else expected_prefix
            ).lower()
            return prefix == exp
        return True
    except Exception:
        return False


def to_fhir_id(id_str: str) -> str:
    """Ensures the identifier uses the FHIR-compliant hyphen separator."""
    raw = str(id_str).strip()
    if "_" in raw:
        return raw.replace("_", "-", 1)
    return raw


def from_fhir_id(fhir_id: str) -> str:
    """Returns canonical identifier (normalized with hyphen separator)."""
    return to_fhir_id(fhir_id)


def _validate_typeid_pydantic(value: str) -> str:
    if not validate_id(value):
        raise ValueError(f"'{value}' is not a valid TypeID (Base32 + UUIDv7)")
    return value


TypeIDStr = Annotated[str, AfterValidator(_validate_typeid_pydantic)]

__all__ = [
    "TypeIDPrefix",
    "TypeIDStr",
    "CROCKFORD_BASE32",
    "generate_id",
    "generate_deterministic_id",
    "parse_id",
    "validate_id",
    "to_fhir_id",
    "from_fhir_id",
]
