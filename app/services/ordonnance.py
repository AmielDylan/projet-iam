"""Ordonnance module: the whole life cycle of a prescription.

Draft, then issued (frozen and numbered), then possibly cancelled.
Every rule lives behind this interface; HTTP routes stay thin.
See CONTEXT.md for the vocabulary and .scratch/ordonnance-v4/spec.md for the rules.

Every method takes the prescriber's id first. An ordonnance that does not
belong to that prescriber behaves as if it did not exist.

The content (patient, establishment, lines, notes, derogations) is one
document sealed by the vault. Each save writes an append-only version.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.services.database import DatabasePool
from app.services.patient import PatientError, PatientService, parse_date
from app.services.vault import vault


MAX_LINES = 60
TEXT_FIELDS = ("general_note", "lab_results", "duration", "renewal")
LINE_TEXT_FIELDS = ("name", "dosage", "form", "posology", "duration", "renewal", "quantity", "note")


# Errors -------------------------------------------------------------------------

class OrdonnanceError(Exception):
    """Base error; `status` and `code` let the API answer without knowing the rules."""

    status = 400
    code = "invalid"


class InvalidContent(OrdonnanceError):
    pass


class NotFound(OrdonnanceError):
    status = 404
    code = "not_found"

    def __init__(self, message: str = "Ordonnance introuvable"):
        super().__init__(message)


class NotEditable(OrdonnanceError):
    status = 409
    code = "not_editable"

    def __init__(self, message: str = "Une ordonnance émise ne peut plus être modifiée"):
        super().__init__(message)


class VersionConflict(OrdonnanceError):
    status = 409
    code = "version_conflict"

    def __init__(self, current: dict[str, Any]):
        super().__init__("Le brouillon a été modifié ailleurs entre-temps")
        self.current = current


# Service ------------------------------------------------------------------------

class OrdonnanceService:
    """Create, save, issue, cancel, renew and list a prescriber's ordonnances."""

    @staticmethod
    def create_draft(owner_id: int, origin_id: int | None = None) -> dict[str, Any]:
        """Start an empty draft (renewal from an issued ordonnance comes with ticket 08)."""
        content = normalize_content({})
        sealed = vault().seal_json(content)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO ordonnances (owner_id, status, version, content, origin_id) VALUES (%s, 'draft', 1, %s, %s)",
                (owner_id, sealed, origin_id),
            )
            ordonnance_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO ordonnance_versions (ordonnance_id, version, content) VALUES (%s, 1, %s)",
                (ordonnance_id, sealed),
            )
        return OrdonnanceService.get(owner_id, ordonnance_id)

    @staticmethod
    def save_draft(owner_id: int, ordonnance_id: int, content: dict[str, Any], version: int) -> dict[str, Any]:
        """Save the full draft content; refuse it if another tab saved a newer version.

        Re-sending a save that already went through (same content, previous version)
        returns the current state instead of a conflict.
        """
        normalized = normalize_content(content)
        _check_references(owner_id, normalized)
        sealed = vault().seal_json(normalized)

        with DatabasePool.get_cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT * FROM ordonnances WHERE id = %s AND owner_id = %s FOR UPDATE",
                (ordonnance_id, owner_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise NotFound()
            if row["status"] != "draft":
                raise NotEditable()
            if int(version) != row["version"]:
                current = _serialize(row)
                if current["content"] == normalized:
                    return current
                raise VersionConflict(current)

            next_version = row["version"] + 1
            cursor.execute(
                """
                UPDATE ordonnances
                SET content = %s, version = %s, patient_id = %s, establishment_id = %s
                WHERE id = %s
                """,
                (sealed, next_version, normalized["patient_id"], normalized["establishment_id"], ordonnance_id),
            )
            cursor.execute(
                "INSERT INTO ordonnance_versions (ordonnance_id, version, content) VALUES (%s, %s, %s)",
                (ordonnance_id, next_version, sealed),
            )

        if normalized["patient_id"]:
            PatientService.touch(owner_id, normalized["patient_id"])
        return OrdonnanceService.get(owner_id, ordonnance_id)

    @staticmethod
    def get(owner_id: int, ordonnance_id: int) -> dict[str, Any] | None:
        """Read one ordonnance with its content."""
        rows = DatabasePool.execute_query(
            "SELECT * FROM ordonnances WHERE id = %s AND owner_id = %s AND status <> 'discarded'",
            (ordonnance_id, owner_id),
            dictionary=True,
        )
        return _serialize(rows[0]) if rows else None

    @staticmethod
    def issue(owner_id: int, ordonnance_id: int) -> dict[str, Any]:
        """Re-run the IAM analysis, then freeze and number the draft, or return the reasons for refusal."""
        raise NotImplementedError("Ticket 04")

    @staticmethod
    def cancel(owner_id: int, ordonnance_id: int, reason: str) -> dict[str, Any]:
        """Cancel an issued ordonnance, keeping the document, the reason and the date."""
        raise NotImplementedError("Ticket 07")

    @staticmethod
    def renew(owner_id: int, ordonnance_id: int) -> dict[str, Any]:
        """Create a new draft linked to, and prefilled from, an issued ordonnance."""
        raise NotImplementedError("Ticket 08")

    @staticmethod
    def list(owner_id: int, status: str | None = None, patient_id: int | None = None) -> list[dict[str, Any]]:
        """List the prescriber's ordonnances, optionally filtered by status or patient."""
        raise NotImplementedError("Ticket 06")


# Content ------------------------------------------------------------------------

def normalize_content(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the draft document as stored; raise InvalidContent on unreadable data."""
    payload = payload or {}
    if not isinstance(payload, dict):
        raise InvalidContent("Contenu d'ordonnance invalide")

    content: dict[str, Any] = {
        "patient_id": _optional_id(payload.get("patient_id"), "patient"),
        "establishment_id": _optional_id(payload.get("establishment_id"), "établissement"),
    }
    try:
        content["prescribed_on"] = parse_date(payload.get("prescribed_on"))
    except PatientError:
        raise InvalidContent("La date de prescription est invalide") from None
    for field in TEXT_FIELDS:
        content[field] = _text(payload.get(field))

    lines = payload.get("lines") or []
    if not isinstance(lines, list):
        raise InvalidContent("Les lignes de prescription sont invalides")
    if len(lines) > MAX_LINES:
        raise InvalidContent(f"Une ordonnance compte au plus {MAX_LINES} lignes")
    content["lines"] = []
    seen_ids: set[str] = set()
    for line in lines:
        normalized = _normalize_line(line)
        if normalized["line_id"] in seen_ids:
            normalized["line_id"] = uuid.uuid4().hex[:12]
        seen_ids.add(normalized["line_id"])
        content["lines"].append(normalized)

    derogations = payload.get("derogations") or {}
    if not isinstance(derogations, dict):
        raise InvalidContent("Les dérogations sont invalides")
    content["derogations"] = {
        str(alert_id): _text(reason)
        for alert_id, reason in derogations.items()
        if _text(reason)
    }
    return content


def _normalize_line(line: Any) -> dict[str, Any]:
    if not isinstance(line, dict):
        raise InvalidContent("Ligne de prescription invalide")
    normalized: dict[str, Any] = {
        "line_id": _text(line.get("line_id"))[:40] or uuid.uuid4().hex[:12],
        "medication_id": _optional_id(line.get("medication_id"), "médicament"),
    }
    for field in LINE_TEXT_FIELDS:
        normalized[field] = _text(line.get(field))
    substances = line.get("substances") or []
    if isinstance(substances, str):
        substances = substances.split("|")
    normalized["substances"] = [_text(s).upper() for s in substances if _text(s)]
    normalized["is_free_text"] = normalized["medication_id"] is None
    return normalized


def _check_references(owner_id: int, content: dict[str, Any]) -> None:
    from app.services.auth import EstablishmentService

    if content["patient_id"] and not PatientService.exists(owner_id, content["patient_id"]):
        raise InvalidContent("Patient introuvable")
    if content["establishment_id"] and not EstablishmentService.get(owner_id, content["establishment_id"]):
        raise InvalidContent("Établissement introuvable")


def _optional_id(value: Any, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise InvalidContent(f"Identifiant de {label} invalide") from None
    if number <= 0:
        raise InvalidContent(f"Identifiant de {label} invalide")
    return number


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "status": row["status"],
        "version": row["version"],
        "patient_id": row["patient_id"],
        "establishment_id": row["establishment_id"],
        "origin_id": row["origin_id"],
        "number": row["number"],
        "content": vault().open_json(row["content"]),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
        "issued_at": _iso(row["issued_at"]),
        "cancelled_at": _iso(row["cancelled_at"]),
    }
