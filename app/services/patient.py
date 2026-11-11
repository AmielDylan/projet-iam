"""Patient module: each prescriber's own patients.

A patient has a stable id. Identity and clinical data form one record, sealed
by the vault: the database holds no name, birthdate or clinical data in clear.
Search uses blind tokens (name prefixes, birthdate). A prescriber only ever
reaches their own patients; anything else behaves as if it did not exist.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from mysql.connector import Error

from app.services.database import DatabasePool
from app.services.vault import vault


SEXES = {"F", "M"}
PREGNANCY = {"none", "pregnant", "breastfeeding"}
TEXT_FIELDS = ("title", "first_name", "last_name", "address", "clinical_notes")


class PatientError(ValueError):
    """Raised when patient data cannot be accepted; the message is shown to the prescriber."""


class PatientService:
    """Create, update, find and read the patients of one prescriber."""

    @staticmethod
    def create(owner_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        record = normalize_patient(payload)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO patients (owner_id, record, birthdate_token) VALUES (%s, %s, %s)",
                (owner_id, vault().seal_json(record), _birthdate_token(record)),
            )
            patient_id = cursor.lastrowid
            _write_tokens(cursor, owner_id, patient_id, record)
        return {"id": patient_id, **record}

    @staticmethod
    def update(owner_id: int, patient_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Correct a patient in place: the id, and so the ordonnances, stay the same."""
        record = normalize_patient(payload)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "UPDATE patients SET record = %s, birthdate_token = %s WHERE id = %s AND owner_id = %s",
                (vault().seal_json(record), _birthdate_token(record), patient_id, owner_id),
            )
            if cursor.rowcount == 0 and not _exists(cursor, owner_id, patient_id):
                return None
            cursor.execute("DELETE FROM patient_search_tokens WHERE patient_id = %s", (patient_id,))
            _write_tokens(cursor, owner_id, patient_id, record)
        return {"id": patient_id, **record}

    @staticmethod
    def get(owner_id: int, patient_id: int) -> dict[str, Any] | None:
        rows = DatabasePool.execute_query(
            "SELECT id, record, last_seen_at FROM patients WHERE id = %s AND owner_id = %s",
            (patient_id, owner_id),
            dictionary=True,
        )
        return _open(rows[0]) if rows else None

    @staticmethod
    def search(owner_id: int, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Patients whose name words start with every searched word, or born on the searched date."""
        birthdate = parse_date(query, strict=False)
        if birthdate:
            rows = DatabasePool.execute_query(
                """
                SELECT id, record, last_seen_at FROM patients
                WHERE owner_id = %s AND birthdate_token = %s
                ORDER BY last_seen_at DESC LIMIT %s
                """,
                (owner_id, vault().blind(birthdate, "birthdate"), limit),
                dictionary=True,
            )
            return [_open(row) for row in rows]

        tokens = sorted(set(vault().query_tokens(query or "")))
        if not tokens:
            return []
        placeholders = ", ".join(["%s"] * len(tokens))
        rows = DatabasePool.execute_query(
            f"""
            SELECT p.id, p.record, p.last_seen_at
            FROM patients p
            JOIN patient_search_tokens t ON t.patient_id = p.id
            WHERE p.owner_id = %s AND t.owner_id = %s AND t.token IN ({placeholders})
            GROUP BY p.id, p.record, p.last_seen_at
            HAVING COUNT(DISTINCT t.token) = %s
            ORDER BY p.last_seen_at DESC
            LIMIT %s
            """,
            (owner_id, owner_id, *tokens, len(tokens), limit),
            dictionary=True,
        )
        return [_open(row) for row in rows]

    @staticmethod
    def recent(owner_id: int, limit: int = 8) -> list[dict[str, Any]]:
        """The prescriber's most recently seen patients."""
        rows = DatabasePool.execute_query(
            "SELECT id, record, last_seen_at FROM patients WHERE owner_id = %s ORDER BY last_seen_at DESC, id DESC LIMIT %s",
            (owner_id, limit),
            dictionary=True,
        )
        return [_open(row) for row in rows]

    @staticmethod
    def touch(owner_id: int, patient_id: int) -> None:
        """Mark the patient as just seen, so recent patients come first."""
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "UPDATE patients SET last_seen_at = CURRENT_TIMESTAMP WHERE id = %s AND owner_id = %s",
                (patient_id, owner_id),
            )

    @staticmethod
    def exists(owner_id: int, patient_id: int) -> bool:
        with DatabasePool.get_cursor() as cursor:
            return _exists(cursor, owner_id, patient_id)

    # Transition from patient_history -------------------------------------------

    @staticmethod
    def migrate_legacy_history() -> int:
        """Copy patient_history rows not yet copied; return how many were copied."""
        rows = DatabasePool.execute_query(
            """
            SELECT h.id, h.user_id, h.patient_title, h.patient_first_name, h.patient_last_name,
                   h.patient_birthdate, h.patient_weight, h.patient_address, h.clinical_notes, h.last_seen_at
            FROM patient_history h
            LEFT JOIN patients p ON p.legacy_history_id = h.id
            WHERE p.id IS NULL
            """,
            dictionary=True,
        )
        for row in rows:
            record = normalize_patient({
                "title": row["patient_title"],
                "first_name": row["patient_first_name"],
                "last_name": row["patient_last_name"],
                "birthdate": row["patient_birthdate"],
                "weight_kg": row["patient_weight"],
                "address": row["patient_address"],
                "clinical_notes": row["clinical_notes"],
            })
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO patients (owner_id, record, birthdate_token, legacy_history_id, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (row["user_id"], vault().seal_json(record), _birthdate_token(record), row["id"], row["last_seen_at"]),
                )
                _write_tokens(cursor, row["user_id"], cursor.lastrowid, record)
        return len(rows)

    @staticmethod
    def ensure_schema() -> None:
        """Create the legacy patient_history table when a deployment has not run migration 007."""
        with DatabasePool.get_cursor() as cursor:
            try:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS `patient_history` (
                        `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                        `user_id` BIGINT NOT NULL,
                        `patient_key` CHAR(64) NOT NULL,
                        `patient_title` VARCHAR(32) NULL,
                        `patient_first_name` VARCHAR(120) NULL,
                        `patient_last_name` VARCHAR(120) NULL,
                        `patient_birthdate` DATE NULL,
                        `patient_weight` DECIMAL(6,2) NULL,
                        `patient_address` TEXT NULL,
                        `clinical_notes` TEXT NULL,
                        `last_seen_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY `uq_patient_history_user_key` (`user_id`, `patient_key`),
                        KEY `idx_patient_history_search` (`user_id`, `patient_last_name`, `patient_first_name`),
                        KEY `idx_patient_history_last_seen` (`user_id`, `last_seen_at`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                )
            except Error as exc:
                if getattr(exc, "errno", None) != 1050:
                    raise


# Normalization -------------------------------------------------------------------

def normalize_patient(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the patient record as stored; raise PatientError on unreadable data."""
    payload = payload or {}
    record: dict[str, Any] = {field: _text(payload.get(field)) for field in TEXT_FIELDS}

    record["birthdate"] = _date_field(payload.get("birthdate"), "La date de naissance")
    record["weighed_on"] = _date_field(payload.get("weighed_on"), "La date de pesée")

    sex = _text(payload.get("sex")).upper() or None
    if sex is not None and sex not in SEXES:
        raise PatientError("Le sexe doit être F ou M.")
    record["sex"] = sex

    pregnancy = _text(payload.get("pregnancy")).lower() or None
    if pregnancy is not None and pregnancy not in PREGNANCY:
        raise PatientError("Grossesse : valeur inconnue.")
    record["pregnancy"] = pregnancy

    record["weight_kg"] = _weight(payload.get("weight_kg"))

    allergies = payload.get("allergies") or []
    if isinstance(allergies, str):
        allergies = re.split(r"[,;\n]", allergies)
    seen: list[str] = []
    for allergy in allergies:
        value = _text(allergy).upper()
        if value and value not in seen:
            seen.append(value)
    record["allergies"] = seen
    return record


def parse_date(value: Any, strict: bool = True) -> str | None:
    """Accept a date, an ISO date or DD/MM/YYYY; return ISO. Non-strict returns None on failure."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    for pattern, order in ((r"^(\d{4})-(\d{2})-(\d{2})$", "ymd"), (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "dmy")):
        match = re.match(pattern, text)
        if not match:
            continue
        parts = [int(part) for part in match.groups()]
        year, month, day = parts if order == "ymd" else (parts[2], parts[1], parts[0])
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            break
    if strict:
        raise PatientError("Date invalide.")
    return None


def _date_field(value: Any, label: str) -> str | None:
    try:
        return parse_date(value)
    except PatientError:
        raise PatientError(f"{label} est invalide.") from None


def _weight(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        weight = float(str(value).replace(",", ".").strip())
    except ValueError:
        raise PatientError("Le poids est invalide.") from None
    if not 0 < weight < 500:
        raise PatientError("Le poids est invalide.")
    return round(weight, 2)


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


# Storage helpers -----------------------------------------------------------------

def _open(row: dict[str, Any]) -> dict[str, Any]:
    record = vault().open_json(row["record"])
    last_seen = row.get("last_seen_at")
    return {
        "id": row["id"],
        **record,
        "last_seen_at": last_seen.isoformat() if hasattr(last_seen, "isoformat") else last_seen,
    }


def _birthdate_token(record: dict[str, Any]) -> str | None:
    return vault().blind(record["birthdate"], "birthdate") if record.get("birthdate") else None


def _write_tokens(cursor, owner_id: int, patient_id: int, record: dict[str, Any]) -> None:
    tokens = vault().name_tokens(f"{record.get('first_name', '')} {record.get('last_name', '')}")
    if tokens:
        cursor.executemany(
            "INSERT INTO patient_search_tokens (patient_id, owner_id, token) VALUES (%s, %s, %s)",
            [(patient_id, owner_id, token) for token in tokens],
        )


def _exists(cursor, owner_id: int, patient_id: int) -> bool:
    cursor.execute("SELECT 1 FROM patients WHERE id = %s AND owner_id = %s", (patient_id, owner_id))
    return cursor.fetchone() is not None
