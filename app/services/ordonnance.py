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

import base64
import uuid
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services.analysis import analyze
from app.services.catalog import MedicationCatalogService
from app.services.catalog_gaps import CatalogGaps
from app.services.database import DatabasePool
from app.services.patient import PatientError, PatientService, parse_date
from app.services.prescriber_code import PrescriberCodes
from app.services.referential import ReferentialService
from app.services.vault import vault


MAX_LINES = 60
PAGE_SIZE = 50
LISTED_STATUSES = ("draft", "issued", "cancelled")
CANCEL_REASONS = [
    "Impression ratée",
    "Erreur de posologie",
    "Erreur de médicament",
    "Erreur de patient",
    "Traitement modifié",
]
PEDIATRIC_AGE = 15
# Prescribers' local date (Benin: UTC+1, no daylight saving). The server runs in UTC.
LOCAL_TIMEZONE = timezone(timedelta(hours=float(os.environ.get("APP_UTC_OFFSET_HOURS", "1"))))
WEIGHT_MAX_AGE_DAYS = 92
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


class NeedsConfirmation(OrdonnanceError):
    status = 409
    code = "confirm_cancelled"

    def __init__(self, message: str = "Cette ordonnance a été annulée. Confirmez pour la reconduire quand même."):
        super().__init__(message)


class IssueRefused(OrdonnanceError):
    status = 422
    code = "issue_refused"

    def __init__(self, reasons: list[dict[str, Any]]):
        super().__init__("L'ordonnance ne peut pas encore être émise")
        self.reasons = reasons


# Service ------------------------------------------------------------------------

class OrdonnanceService:
    """Create, save, issue, cancel, renew and list a prescriber's ordonnances."""

    @staticmethod
    def create_draft(owner_id: int, content: dict[str, Any] | None = None, origin_id: int | None = None) -> dict[str, Any]:
        """Start a draft, empty or prefilled (renewal)."""
        normalized = normalize_content(content or {})
        _check_references(owner_id, normalized)
        sealed = vault().seal_json(normalized)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ordonnances (owner_id, status, version, content, patient_id, establishment_id, origin_id)
                VALUES (%s, 'draft', 1, %s, %s, %s, %s)
                """,
                (owner_id, sealed, normalized["patient_id"], normalized["establishment_id"], origin_id),
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
    def check(owner_id: int, ordonnance_id: int) -> dict[str, Any]:
        """Everything the verification step shows: refusal reasons, warnings, analysis, referentials."""
        ordonnance = OrdonnanceService.get(owner_id, ordonnance_id)
        if ordonnance is None:
            raise NotFound()
        if ordonnance["status"] != "draft":
            raise NotEditable()
        evaluation = _evaluate(owner_id, ordonnance["content"])
        return {
            "version": ordonnance["version"],
            "can_issue": not evaluation["reasons"],
            "reasons": evaluation["reasons"],
            "warnings": evaluation["warnings"],
            "analysis": evaluation["analysis"],
            "referentials": ReferentialService.current(),
        }

    @staticmethod
    def issue(owner_id: int, ordonnance_id: int, version: int) -> dict[str, Any]:
        """Re-run every check and the IAM analysis on the server, then freeze and number the draft.

        `version` is the version the prescriber reviewed: what is printed is what was read.
        Issuing an already issued ordonnance returns it unchanged (double click, retry).
        """
        ordonnance = OrdonnanceService.get(owner_id, ordonnance_id)
        if ordonnance is None:
            raise NotFound()
        if ordonnance["status"] == "issued":
            return ordonnance
        if ordonnance["status"] != "draft":
            raise NotEditable()
        if int(version) != ordonnance["version"]:
            raise VersionConflict(ordonnance)

        evaluation = _evaluate(owner_id, ordonnance["content"])
        if evaluation["reasons"]:
            raise IssueRefused(evaluation["reasons"])

        code = PrescriberCodes.ensure(owner_id)
        snapshot = _snapshot(owner_id, ordonnance["content"], evaluation)
        year = date.fromisoformat(snapshot["prescribed_on"]).year

        with DatabasePool.get_cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT status, version FROM ordonnances WHERE id = %s AND owner_id = %s FOR UPDATE",
                (ordonnance_id, owner_id),
            )
            row = cursor.fetchone()
            if row["status"] != "draft" or row["version"] != ordonnance["version"]:
                raise VersionConflict(OrdonnanceService.get(owner_id, ordonnance_id))
            cursor.execute(
                """
                INSERT INTO prescriber_sequences (owner_id, year, last_number) VALUES (%s, %s, 1)
                ON DUPLICATE KEY UPDATE last_number = last_number + 1
                """,
                (owner_id, year),
            )
            cursor.execute(
                "SELECT last_number FROM prescriber_sequences WHERE owner_id = %s AND year = %s",
                (owner_id, year),
            )
            number = f"{code}-{year}-{cursor.fetchone()['last_number']:06d}"
            cursor.execute("SELECT NOW() AS now")  # the database clock, like every other timestamp
            snapshot["number"] = number
            snapshot["issued_at"] = cursor.fetchone()["now"].isoformat()
            cursor.execute(
                """
                UPDATE ordonnances
                SET status = 'issued', number = %s, snapshot = %s, issued_at = %s
                WHERE id = %s
                """,
                (number, vault().seal_json(snapshot), snapshot["issued_at"], ordonnance_id),
            )
        # Anonymous count of free-text medications, for catalog enrichment (ticket 15).
        CatalogGaps.record_free_entries([line["name"] for line in snapshot["lines"] if line["is_free_text"]])
        return OrdonnanceService.get(owner_id, ordonnance_id)

    @staticmethod
    def cancel(owner_id: int, ordonnance_id: int, reason: str) -> dict[str, Any]:
        """Cancel an issued ordonnance, keeping the document, the reason and the date."""
        reason = _text(reason)
        if not reason:
            raise InvalidContent("Indiquez le motif de l'annulation")
        ordonnance = OrdonnanceService.get(owner_id, ordonnance_id)
        if ordonnance is None:
            raise NotFound()
        if ordonnance["status"] != "issued":
            raise NotEditable("Seule une ordonnance émise peut être annulée")
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE ordonnances SET status = 'cancelled', cancelled_at = NOW(), cancel_reason = %s
                WHERE id = %s AND owner_id = %s AND status = 'issued'
                """,
                (vault().seal_json(reason[:500]), ordonnance_id, owner_id),
            )
        return OrdonnanceService.get(owner_id, ordonnance_id)

    @staticmethod
    def renew(owner_id: int, ordonnance_id: int, confirm_cancelled: bool = False) -> dict[str, Any]:
        """New draft for the same patient, prefilled from an issued ordonnance and linked to it.

        Derogations are never carried over: the analysis runs again on today's catalog.
        A line whose catalog entry disappeared becomes free text, with a notice.
        """
        source = OrdonnanceService.get(owner_id, ordonnance_id)
        if source is None:
            raise NotFound()
        if source["status"] == "draft":
            raise NotEditable("Un brouillon se modifie directement ; seule une ordonnance émise se reconduit")
        if source["status"] == "cancelled" and not confirm_cancelled:
            raise NeedsConfirmation()

        frozen = source["snapshot"]
        notices = []
        lines = []
        for line in frozen["lines"]:
            copy = {key: line.get(key) for key in ("line_id", "medication_id", *LINE_TEXT_FIELDS)}
            copy["substances"] = line.get("dci") or line.get("substances") or []
            if copy["medication_id"] and MedicationCatalogService.get(int(copy["medication_id"])) is None:
                copy["medication_id"] = None
                notices.append({"line_id": line["line_id"], "code": "catalog_missing",
                                "message": f"{line['name']} n'est plus au catalogue : la ligne passe en saisie libre."})
            lines.append(copy)

        content = {
            "patient_id": source["patient_id"] if PatientService.exists(owner_id, source["patient_id"]) else None,
            "establishment_id": source["establishment_id"],
            "general_note": frozen.get("general_note", ""),
            "duration": frozen.get("duration", ""),
            "renewal": frozen.get("renewal", ""),
            "lines": lines,
        }
        try:
            draft = OrdonnanceService.create_draft(owner_id, content, origin_id=ordonnance_id)
        except InvalidContent:  # establishment removed since: the prescriber picks another one
            draft = OrdonnanceService.create_draft(owner_id, {**content, "establishment_id": None}, origin_id=ordonnance_id)
        return {"ordonnance": draft, "notices": notices}

    @staticmethod
    def cancel_and_correct(owner_id: int, ordonnance_id: int, reason: str) -> dict[str, Any]:
        """Cancel, then open a prefilled renewal: for a failed print or an error seen just after."""
        cancelled = OrdonnanceService.cancel(owner_id, ordonnance_id, reason)
        renewal = OrdonnanceService.renew(owner_id, ordonnance_id, confirm_cancelled=True)
        return {"cancelled": cancelled, **renewal}

    @staticmethod
    def list(owner_id: int, status: str | None = None, patient_id: int | None = None,
             page: int = 1, per_page: int = PAGE_SIZE) -> dict[str, Any]:
        """The prescriber's ordonnances, most recent first, optionally filtered by status or patient."""
        if status is not None and status not in LISTED_STATUSES:
            raise ValueError(f"Statut inconnu : {status}")
        where = ["owner_id = %s", "status <> 'discarded'"]
        params: list[Any] = [owner_id]
        if status:
            where.append("status = %s")
            params.append(status)
        if patient_id:
            where.append("patient_id = %s")
            params.append(patient_id)
        condition = " AND ".join(where)

        total = DatabasePool.execute_query(f"SELECT COUNT(*) FROM ordonnances WHERE {condition}", tuple(params))[0][0]
        page = max(1, int(page or 1))
        rows = DatabasePool.execute_query(
            f"""
            SELECT * FROM ordonnances WHERE {condition}
            ORDER BY updated_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (*params, per_page, (page - 1) * per_page),
            dictionary=True,
        )
        patients: dict[int, Any] = {}
        items = []
        for row in rows:
            item = _serialize(row)
            if item["patient_id"] and item["patient_id"] not in patients:
                patients[item["patient_id"]] = PatientService.get(owner_id, item["patient_id"])
            items.append(_summary(item, patients.get(item["patient_id"])))
        return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // per_page))}

    @staticmethod
    def discard_draft(owner_id: int, ordonnance_id: int) -> None:
        """Delete a draft from the prescriber's view; an issued ordonnance is never deleted."""
        ordonnance = OrdonnanceService.get(owner_id, ordonnance_id)
        if ordonnance is None:
            raise NotFound()
        if ordonnance["status"] != "draft":
            raise NotEditable("Une ordonnance émise ne peut pas être supprimée")
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "UPDATE ordonnances SET status = 'discarded' WHERE id = %s AND owner_id = %s AND status = 'draft'",
                (ordonnance_id, owner_id),
            )


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
    snapshot = vault().open_json(row["snapshot"]) if row.get("snapshot") else None
    return {
        "snapshot": snapshot,
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
        "cancel_reason": vault().open_json(row["cancel_reason"]) if row.get("cancel_reason") else None,
    }


def _summary(item: dict[str, Any], patient: dict[str, Any] | None) -> dict[str, Any]:
    """A list row: enough to recognize an ordonnance, from the snapshot once issued."""
    source = item["snapshot"] or item["content"]
    frozen_patient = (item["snapshot"] or {}).get("patient")
    who = frozen_patient or patient or {}
    return {
        key: item[key]
        for key in ("id", "status", "number", "version", "patient_id", "origin_id",
                    "created_at", "updated_at", "issued_at", "cancelled_at")
    } | {
        "patient": {key: who.get(key) for key in ("first_name", "last_name", "birthdate")} if who else None,
        "medications": [line.get("name") for line in source.get("lines", []) if line.get("name")],
    }


# Issuance -----------------------------------------------------------------------

def _evaluate(owner_id: int, content: dict[str, Any]) -> dict[str, Any]:
    """Refusal reasons and warnings for a draft, with the IAM analysis."""
    from app.services.auth import EstablishmentService

    reasons: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    on_date = date.fromisoformat(content.get("prescribed_on") or local_today().isoformat())

    patient = PatientService.get(owner_id, content["patient_id"]) if content.get("patient_id") else None
    if patient is None:
        reasons.append(_reason("patient_missing", "Choisissez le patient."))
    else:
        if not patient.get("sex"):
            reasons.append(_reason("sex_missing", "Indiquez le sexe du patient."))
        if not patient.get("birthdate"):
            reasons.append(_reason("birthdate_missing", "Indiquez la date de naissance du patient."))
        elif age_on(patient["birthdate"], on_date)[0] < PEDIATRIC_AGE:
            if not patient.get("weight_kg") or not patient.get("weighed_on"):
                reasons.append(_reason("weight_missing", "Avant 15 ans, le poids et sa date de pesée sont obligatoires."))
            elif (on_date - date.fromisoformat(patient["weighed_on"])).days > WEIGHT_MAX_AGE_DAYS:
                warnings.append(_reason("weight_stale", "La pesée date de plus de 3 mois."))

    establishment = (
        EstablishmentService.get(owner_id, content["establishment_id"]) if content.get("establishment_id") else None
    )
    if not establishment or not establishment.get("is_active"):
        reasons.append(_reason("establishment_missing", "Choisissez l'établissement qui figurera en en-tête."))

    lines = [line for line in content["lines"] if line.get("name") or line.get("medication_id")]
    if not lines:
        reasons.append(_reason("no_lines", "Ajoutez au moins un médicament."))
    without_posology = [line["line_id"] for line in lines if not line.get("posology")]
    if without_posology:
        reasons.append(_reason("posology_missing", "Indiquez la posologie de chaque ligne.", without_posology))

    analysis = analyze(lines, patient=patient, derogations=content.get("derogations"))
    for alert in analysis["alerts"]:
        if alert["requirement"] == "blocking":
            reasons.append(_reason("alert_blocking", alert["message"], alert["line_ids"], alert["id"]))
        elif alert["requirement"] == "justify" and not alert["derogation"]:
            reasons.append(_reason("alert_unjustified", alert["message"], alert["line_ids"], alert["id"]))

    return {"reasons": reasons, "warnings": warnings, "analysis": analysis,
            "patient": patient, "lines": lines, "on_date": on_date}


def local_today() -> date:
    return datetime.now(LOCAL_TIMEZONE).date()


def _reason(code: str, message: str, line_ids: list[str] | None = None, alert_id: str | None = None) -> dict[str, Any]:
    reason: dict[str, Any] = {"code": code, "message": message}
    if line_ids:
        reason["line_ids"] = line_ids
    if alert_id:
        reason["alert_id"] = alert_id
    return reason


def age_on(birthdate: str, on_date: date) -> tuple[int, int]:
    """Age in whole years and whole months on a given date."""
    born = date.fromisoformat(birthdate)
    months = (on_date.year - born.year) * 12 + on_date.month - born.month - (1 if on_date.day < born.day else 0)
    return months // 12, months


def age_label(birthdate: str | None, on_date: date) -> str:
    if not birthdate:
        return ""
    years, months = age_on(birthdate, on_date)
    return f"{months} mois" if years < 2 else f"{years} ans"


def _snapshot(owner_id: int, content: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
    """Everything the reprint needs, frozen: later edits elsewhere never change it."""
    prescriber = prescriber_identity(owner_id)
    prescriber["prescriber_code"] = PrescriberCodes.of(owner_id)

    patient = dict(evaluation["patient"])
    patient.pop("last_seen_at", None)
    patient["age_label"] = age_label(patient.get("birthdate"), evaluation["on_date"])

    lines = []
    for line in evaluation["lines"]:
        entry = MedicationCatalogService.get(int(line["medication_id"])) if line.get("medication_id") else None
        lines.append({**line, "dci": (entry or {}).get("substances", []), "is_free_text": entry is None})

    analysis = evaluation["analysis"]
    derogations = [
        {"alert_id": alert["id"], "reason": alert["derogation"], "message": alert["message"],
         "type": alert["type"], "level": alert["level"], "line_ids": alert["line_ids"]}
        for alert in analysis["alerts"] if alert.get("derogation")
    ]
    return {
        "prescribed_on": evaluation["on_date"].isoformat(),
        "prescriber": prescriber,
        "establishment": _establishment_for_print(owner_id, content["establishment_id"]),
        "patient": patient,
        "lines": lines,
        "general_note": content.get("general_note", ""),
        "lab_results": content.get("lab_results", ""),
        "duration": content.get("duration", ""),
        "renewal": content.get("renewal", ""),
        "analysis": analysis,
        "derogations": derogations,
        "warnings": evaluation["warnings"],
        "referentials": ReferentialService.current(),
    }


def prescriber_identity(owner_id: int) -> dict[str, Any]:
    """Name, profession and identifiers printed in the header: profile first, account as fallback."""
    from app.services.auth import AuthService, ProfileService

    user = AuthService.get_user(owner_id) or {}
    profile = ProfileService.get_profile(owner_id)
    prescriber = {key: value for key, value in profile.items() if value}
    for key in ("first_name", "last_name", "profession", "order_number", "phone", "email"):
        prescriber.setdefault(key, user.get(key) or "")
    return prescriber


def _establishment_for_print(owner_id: int, establishment_id: int) -> dict[str, Any]:
    rows = DatabasePool.execute_query(
        "SELECT * FROM prescriber_establishments WHERE id = %s AND user_id = %s",
        (establishment_id, owner_id),
        dictionary=True,
    )
    row = rows[0]
    fields = ("name", "type", "address", "phone", "email", "identifier_label", "identifier_value",
              "secondary_identifier_label", "secondary_identifier_value", "free_text")
    establishment = {field: row.get(field) or "" for field in fields}
    establishment["paper_format"] = row.get("paper_format") or "A5"
    logo = row.get("logo_content")
    establishment["logo"] = (
        f"data:{row['logo_mime_type']};base64,{base64.b64encode(logo).decode()}" if logo else None
    )
    return establishment
