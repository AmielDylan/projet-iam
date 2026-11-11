"""Patient module: each prescriber's own patients."""
from __future__ import annotations

import hashlib
from typing import Any

from mysql.connector import Error

from app.services.database import DatabasePool


PATIENT_FIELDS = (
    "patient_title",
    "patient_first_name",
    "patient_last_name",
    "patient_birthdate",
    "patient_weight",
    "patient_address",
    "clinical_notes",
)


class PatientService:
    """Search and save the patients of one prescriber."""

    @staticmethod
    def ensure_schema() -> None:
        """Create the patient table when a deployment has not run migration 007."""
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

    @staticmethod
    def search(user_id: int, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """Return the prescriber's patients whose name matches, most recent first."""
        query = (query or "").strip()
        if not query:
            return []
        pattern = f"%{query}%"
        return DatabasePool.execute_query(
            """
            SELECT id, patient_title, patient_first_name, patient_last_name, patient_birthdate,
                   patient_weight, patient_address, clinical_notes, last_seen_at
            FROM patient_history
            WHERE user_id = %s
              AND (patient_first_name LIKE %s OR patient_last_name LIKE %s OR CONCAT(patient_first_name, ' ', patient_last_name) LIKE %s)
            ORDER BY last_seen_at DESC
            LIMIT %s
            """,
            (user_id, pattern, pattern, pattern, limit),
            dictionary=True,
        )

    @staticmethod
    def save(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or update a patient, identified by first name, last name and birthdate."""
        data = {field: str(payload.get(field) or "").strip() for field in PATIENT_FIELDS}
        data["patient_key"] = patient_key(data)
        weight = data["patient_weight"] or None
        if weight is not None:
            try:
                weight = float(weight)
            except ValueError:
                weight = None

        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO patient_history
                    (user_id, patient_key, patient_title, patient_first_name, patient_last_name,
                     patient_birthdate, patient_weight, patient_address, clinical_notes, last_seen_at)
                VALUES (%s, %s, %s, %s, %s, NULLIF(%s, ''), %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                    patient_title = VALUES(patient_title),
                    patient_first_name = VALUES(patient_first_name),
                    patient_last_name = VALUES(patient_last_name),
                    patient_birthdate = VALUES(patient_birthdate),
                    patient_weight = VALUES(patient_weight),
                    patient_address = VALUES(patient_address),
                    clinical_notes = VALUES(clinical_notes),
                    last_seen_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    data["patient_key"],
                    data["patient_title"] or None,
                    data["patient_first_name"] or None,
                    data["patient_last_name"] or None,
                    data["patient_birthdate"],
                    weight,
                    data["patient_address"] or None,
                    data["clinical_notes"] or None,
                ),
            )
        return data


def patient_key(data: dict[str, Any]) -> str:
    """Derive the current patient identity from name and birthdate (replaced in ticket 03)."""
    identity = "|".join(
        str(data.get(field) or "").strip().upper()
        for field in ("patient_first_name", "patient_last_name", "patient_birthdate")
    )
    if identity == "||":
        identity = str(data)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()
