"""Authentication, prescriber profile, and patient history services."""
from __future__ import annotations

import hashlib
from functools import wraps
from typing import Any, Callable

from flask import flash, redirect, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

from app.services.database import DatabasePool


PROFILE_FIELDS = (
    "title",
    "first_name",
    "last_name",
    "profession",
    "organization",
    "address",
    "phone",
    "email",
    "country",
    "identifier_label",
    "identifier_value",
    "secondary_identifier_label",
    "secondary_identifier_value",
    "extra_details",
)

PATIENT_FIELDS = (
    "patient_title",
    "patient_first_name",
    "patient_last_name",
    "patient_birthdate",
    "patient_weight",
    "patient_address",
    "clinical_notes",
)


class AuthService:
    """Session-backed auth helpers for the Flask app."""

    REQUESTABLE_ROLES = {"pharmacy", "prescriber"}

    @staticmethod
    def current_user() -> dict[str, Any] | None:
        user_id = session.get("user_id")
        if not user_id:
            return None
        return AuthService.get_user(int(user_id))

    @staticmethod
    def get_user(user_id: int) -> dict[str, Any] | None:
        rows = DatabasePool.execute_query(
            """
            SELECT id, email, role, status, first_name, last_name, requested_at, reviewed_at, review_note
            FROM iam_users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,),
            dictionary=True,
        )
        return rows[0] if rows else None

    @staticmethod
    def create_account_request(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = "prescriber",
    ) -> tuple[bool, str]:
        email = (email or "").strip().lower()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        role = (role or "prescriber").strip().lower()
        if role not in AuthService.REQUESTABLE_ROLES:
            return False, "Type de compte invalide."
        if not email or not password or len(password) < 8:
            return False, "Email et mot de passe de 8 caractères minimum requis."
        try:
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name)
                    VALUES (%s, %s, %s, 'pending', %s, %s)
                    """,
                    (email, generate_password_hash(password), role, first_name, last_name),
                )
            reviewer = "un administrateur" if role == "pharmacy" else "la pharmacie modératrice"
            return True, f"Demande créée. Elle doit être validée par {reviewer}."
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                return False, "Un compte existe déjà avec cet email."
            return False, "Impossible de créer la demande pour le moment."

    @staticmethod
    def create_prescriber_request(email: str, password: str, first_name: str, last_name: str) -> tuple[bool, str]:
        return AuthService.create_account_request(email, password, first_name, last_name, "prescriber")

    @staticmethod
    def authenticate(email: str, password: str) -> tuple[bool, str]:
        rows = DatabasePool.execute_query(
            """
            SELECT id, email, password_hash, role, status
            FROM iam_users
            WHERE email = %s
            LIMIT 1
            """,
            ((email or "").strip().lower(),),
            dictionary=True,
        )
        user = rows[0] if rows else None
        if not user or not check_password_hash(user["password_hash"], password or ""):
            return False, "Identifiants invalides."
        if user["status"] != "approved":
            return False, "Compte en attente de validation administrative."
        session.clear()
        session["user_id"] = int(user["id"])
        session["role"] = user["role"]
        return True, "Connexion réussie."

    @staticmethod
    def logout() -> None:
        session.clear()

    @staticmethod
    def list_account_requests(reviewer: dict[str, Any]) -> list[dict[str, Any]]:
        """Return account requests the current reviewer is allowed to manage."""
        role = reviewer.get("role")
        if role == "admin":
            params: tuple[Any, ...] = ("pharmacy",)
            role_filter = "role = %s"
        elif role == "pharmacy":
            params = ("prescriber",)
            role_filter = "role = %s"
        else:
            return []

        return DatabasePool.execute_query(
            """
            SELECT id, email, role, first_name, last_name, status, requested_at, reviewed_at, review_note
            FROM iam_users
            WHERE """ + role_filter + """
            ORDER BY
                CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
                requested_at DESC
            """,
            params,
            dictionary=True,
        )

    @staticmethod
    def list_prescriber_requests() -> list[dict[str, Any]]:
        return DatabasePool.execute_query(
            """
            SELECT id, email, role, first_name, last_name, status, requested_at, reviewed_at, review_note
            FROM iam_users
            WHERE role = 'prescriber'
            ORDER BY
                CASE status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
                requested_at DESC
            """,
            dictionary=True,
        )

    @staticmethod
    def can_review(reviewer: dict[str, Any], target: dict[str, Any]) -> bool:
        if reviewer.get("status") != "approved":
            return False
        if reviewer.get("role") == "admin":
            return target.get("role") == "pharmacy"
        if reviewer.get("role") == "pharmacy":
            return target.get("role") == "prescriber"
        return False

    @staticmethod
    def review_account(user_id: int, reviewer: dict[str, Any], approve: bool, note: str = "") -> tuple[bool, str]:
        target = AuthService.get_user(user_id)
        if not target:
            return False, "Compte introuvable."
        if not AuthService.can_review(reviewer, target):
            return False, "Vous ne pouvez pas traiter cette demande."
        status = "approved" if approve else "rejected"
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE iam_users
                SET status = %s, reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP, review_note = %s
                WHERE id = %s
                """,
                (status, int(reviewer["id"]), (note or "").strip() or None, user_id),
            )
        return True, "Demande mise à jour."

    @staticmethod
    def review_prescriber(user_id: int, reviewer_id: int, approve: bool, note: str = "") -> None:
        reviewer = AuthService.get_user(reviewer_id) or {"id": reviewer_id, "role": "pharmacy", "status": "approved"}
        AuthService.review_account(user_id, reviewer, approve, note)

    @staticmethod
    def create_admin(email: str, password: str, first_name: str = "", last_name: str = "") -> tuple[bool, str]:
        email = (email or "").strip().lower()
        if not email or not password or len(password) < 8:
            return False, "ADMIN_EMAIL et ADMIN_PASSWORD de 8 caractères minimum sont requis."
        password_hash = generate_password_hash(password)
        try:
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name, reviewed_at)
                    VALUES (%s, %s, 'admin', 'approved', %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        role = %s,
                        status = %s,
                        password_hash = %s,
                        first_name = %s,
                        last_name = %s,
                        reviewed_at = CURRENT_TIMESTAMP
                    """,
                    (
                        email,
                        password_hash,
                        first_name,
                        last_name,
                        "admin",
                        "approved",
                        password_hash,
                        first_name,
                        last_name,
                    ),
                )
            return True, "Compte administrateur créé ou mis à jour."
        except Error:
            return False, "Impossible de créer le compte administrateur."


class ProfileService:
    """Prescriber profile and scoped patient history."""

    @staticmethod
    def get_profile(user_id: int) -> dict[str, Any]:
        rows = DatabasePool.execute_query(
            f"""
            SELECT {', '.join(PROFILE_FIELDS)}
            FROM prescriber_profiles
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
            dictionary=True,
        )
        if rows:
            return {field: rows[0].get(field) or "" for field in PROFILE_FIELDS}

        user = AuthService.get_user(user_id) or {}
        return {
            field: (user.get(field) if field in ("first_name", "last_name") else "") or ""
            for field in PROFILE_FIELDS
        }

    @staticmethod
    def save_profile(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        data = {field: str(payload.get(field) or "").strip() for field in PROFILE_FIELDS}
        columns = ", ".join(["user_id", *PROFILE_FIELDS])
        placeholders = ", ".join(["%s"] * (len(PROFILE_FIELDS) + 1))
        updates = ", ".join(f"{field} = VALUES({field})" for field in PROFILE_FIELDS)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO prescriber_profiles ({columns})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {updates}
                """,
                (user_id, *[data[field] or None for field in PROFILE_FIELDS]),
            )
        return data

    @staticmethod
    def search_patients(user_id: int, query: str, limit: int = 8) -> list[dict[str, Any]]:
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
    def upsert_patient(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
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
    identity = "|".join(
        str(data.get(field) or "").strip().upper()
        for field in ("patient_first_name", "patient_last_name", "patient_birthdate")
    )
    if identity == "||":
        identity = str(data)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def require_login(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not AuthService.current_user():
            flash("Connexion requise.", "warning")
            return redirect(url_for("web.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def require_approved_prescriber(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = AuthService.current_user()
        if not user:
            flash("Connexion requise.", "warning")
            return redirect(url_for("web.login", next=request.path))
        if user["role"] != "prescriber" or user["status"] != "approved":
            flash("Compte prescripteur validé requis.", "warning")
            return redirect(url_for("web.home"))
        return view(*args, **kwargs)

    return wrapped


def require_admin(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = AuthService.current_user()
        if not user:
            flash("Connexion administrateur requise.", "warning")
            return redirect(url_for("web.login", next=request.path))
        if user["role"] != "admin" or user["status"] != "approved":
            flash("Accès administrateur requis.", "warning")
            return redirect(url_for("web.home"))
        return view(*args, **kwargs)

    return wrapped


def require_account_reviewer(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = AuthService.current_user()
        if not user:
            flash("Connexion requise.", "warning")
            return redirect(url_for("web.login", next=request.path))
        if user["role"] not in {"admin", "pharmacy"} or user["status"] != "approved":
            flash("Accès modération requis.", "warning")
            return redirect(url_for("web.home"))
        return view(*args, **kwargs)

    return wrapped
