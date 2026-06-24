"""Authentication, prescriber profile, and patient history services."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from functools import wraps
from typing import Any, Callable

from flask import current_app, flash, redirect, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.services.database import DatabasePool
from app.services.email import EmailDeliveryError, EmailService


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

PROFESSIONS = (
    "Médecin",
    "Pharmacien",
    "Chirurgien-dentiste",
    "Sage-femme",
    "Infirmier",
    "Autre professionnel autorisé",
)

IDENTITY_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


class AuthService:
    """Session-backed auth helpers for the Flask app."""

    @staticmethod
    def ensure_schema() -> None:
        """Create the auth tables when a deployment has not run migration 007."""
        with DatabasePool.get_cursor() as cursor:
            def create_table(sql: str) -> None:
                try:
                    cursor.execute(sql)
                except Error as exc:
                    if getattr(exc, "errno", None) != 1050:
                        raise

            def add_column(table: str, column: str, definition: str) -> None:
                try:
                    cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
                except Error as exc:
                    if getattr(exc, "errno", None) != 1060:
                        raise

            create_table(
                """
                CREATE TABLE IF NOT EXISTS `iam_users` (
                    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                    `email` VARCHAR(255) NOT NULL,
                    `password_hash` VARCHAR(255) NOT NULL,
                    `role` VARCHAR(32) NOT NULL DEFAULT 'prescriber',
                    `status` VARCHAR(32) NOT NULL DEFAULT 'pending',
                    `first_name` VARCHAR(120) NULL,
                    `last_name` VARCHAR(120) NULL,
                    `birthdate` DATE NULL,
                    `profession` VARCHAR(120) NULL,
                    `order_number` VARCHAR(160) NULL,
                    `phone` VARCHAR(80) NULL,
                    `requested_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `reviewed_at` TIMESTAMP NULL,
                    `reviewed_by` BIGINT NULL,
                    `review_note` TEXT NULL,
                    `temporary_password_expires_at` DATETIME NULL,
                    `must_change_password` TINYINT NOT NULL DEFAULT 0,
                    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY `uq_iam_users_email` (`email`),
                    KEY `idx_iam_users_role_status` (`role`, `status`),
                    KEY `idx_iam_users_reviewed_by` (`reviewed_by`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            for column, definition in (
                ("birthdate", "DATE NULL AFTER `last_name`"),
                ("profession", "VARCHAR(120) NULL AFTER `birthdate`"),
                ("order_number", "VARCHAR(160) NULL AFTER `profession`"),
                ("phone", "VARCHAR(80) NULL AFTER `order_number`"),
                ("temporary_password_expires_at", "DATETIME NULL AFTER `review_note`"),
                ("must_change_password", "TINYINT NOT NULL DEFAULT 0 AFTER `temporary_password_expires_at`"),
            ):
                add_column("iam_users", column, definition)

            create_table(
                """
                CREATE TABLE IF NOT EXISTS `identity_documents` (
                    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` BIGINT NOT NULL,
                    `filename` VARCHAR(255) NOT NULL,
                    `mime_type` VARCHAR(120) NOT NULL,
                    `size_bytes` INT NOT NULL,
                    `content` LONGBLOB NOT NULL,
                    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY `uq_identity_documents_user` (`user_id`),
                    KEY `idx_identity_documents_created` (`created_at`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            create_table(
                """
                CREATE TABLE IF NOT EXISTS `prescriber_profiles` (
                    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` BIGINT NOT NULL,
                    `title` VARCHAR(32) NULL,
                    `first_name` VARCHAR(120) NULL,
                    `last_name` VARCHAR(120) NULL,
                    `profession` VARCHAR(160) NULL,
                    `organization` VARCHAR(180) NULL,
                    `address` TEXT NULL,
                    `phone` VARCHAR(80) NULL,
                    `email` VARCHAR(255) NULL,
                    `country` VARCHAR(120) NULL,
                    `identifier_label` VARCHAR(120) NULL,
                    `identifier_value` VARCHAR(160) NULL,
                    `secondary_identifier_label` VARCHAR(120) NULL,
                    `secondary_identifier_value` VARCHAR(160) NULL,
                    `extra_details` TEXT NULL,
                    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY `uq_prescriber_profiles_user` (`user_id`),
                    KEY `idx_prescriber_profiles_name` (`last_name`, `first_name`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            create_table(
                """
                CREATE TABLE IF NOT EXISTS `prescriber_establishments` (
                    `id` BIGINT PRIMARY KEY AUTO_INCREMENT,
                    `user_id` BIGINT NOT NULL,
                    `name` VARCHAR(180) NOT NULL,
                    `type` VARCHAR(120) NULL,
                    `address` TEXT NULL,
                    `phone` VARCHAR(80) NULL,
                    `email` VARCHAR(255) NULL,
                    `identifier_label` VARCHAR(120) NULL,
                    `identifier_value` VARCHAR(160) NULL,
                    `secondary_identifier_label` VARCHAR(120) NULL,
                    `secondary_identifier_value` VARCHAR(160) NULL,
                    `free_text` TEXT NULL,
                    `logo_filename` VARCHAR(255) NULL,
                    `logo_mime_type` VARCHAR(120) NULL,
                    `logo_size_bytes` INT NULL,
                    `logo_content` LONGBLOB NULL,
                    `is_active` TINYINT NOT NULL DEFAULT 1,
                    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY `idx_prescriber_establishments_user` (`user_id`, `is_active`),
                    KEY `idx_prescriber_establishments_name` (`name`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            create_table(
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

    @staticmethod
    def current_session_user() -> dict[str, Any] | None:
        """Return the user data already stored in the session."""
        user_id = session.get("user_id")
        if not user_id:
            return None
        return {
            "id": int(user_id),
            "email": session.get("email"),
            "role": session.get("role"),
            "status": session.get("status", "approved"),
            "must_change_password": bool(session.get("must_change_password")),
        }

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
            SELECT id, email, role, status, first_name, last_name, birthdate, profession,
                   order_number, phone, requested_at, reviewed_at, review_note,
                   temporary_password_expires_at, must_change_password
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
        password: str = "",
        first_name: str = "",
        last_name: str = "",
        role: str = "prescriber",
        birthdate: str = "",
        profession: str = "",
        order_number: str = "",
        phone: str = "",
        identity_document: Any = None,
    ) -> tuple[bool, str, dict | None]:
        email = (email or "").strip().lower()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        birthdate = (birthdate or "").strip()
        profession = (profession or "").strip()
        order_number = (order_number or "").strip()
        phone = (phone or "").strip()
        role = "prescriber"
        if not all([email, first_name, last_name, birthdate, profession, order_number, phone]):
            return False, "Tous les champs d'identité prescripteur sont requis.", None
        if profession not in PROFESSIONS:
            return False, "Profession invalide.", None
        document, error = AuthService.validate_identity_document(identity_document)
        if error:
            return False, error, None
        try:
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO iam_users
                        (email, password_hash, role, status, first_name, last_name,
                         birthdate, profession, order_number, phone, must_change_password)
                    VALUES (%s, '', %s, 'pending', %s, %s, NULLIF(%s, ''), %s, %s, %s, 0)
                    """,
                    (email, role, first_name, last_name, birthdate, profession, order_number, phone),
                )
                user_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO identity_documents (user_id, filename, mime_type, size_bytes, content)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        document["filename"],
                        document["mime_type"],
                        document["size_bytes"],
                        document["content"],
                    ),
                )
            return True, "Demande créée. Elle doit être validée par l'administrateur.", None
        except Error as exc:
            # Duplicate email
            if getattr(exc, "errno", None) == 1062:
                return False, "Un compte existe déjà avec cet email.", {"error_source": "duplicate_email"}
            # Return a safe, user-friendly message plus a minimal error source for diagnostics
            return False, "Impossible de créer la demande pour le moment.", {"error_source": "database"}

    @staticmethod
    def create_prescriber_request(email: str, password: str, first_name: str, last_name: str) -> tuple[bool, str]:
        return AuthService.create_account_request(email, password, first_name, last_name, "prescriber")

    @staticmethod
    def validate_identity_document(file_storage: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not file_storage or not getattr(file_storage, "filename", ""):
            return None, "Pièce d'identité requise."
        filename = secure_filename(file_storage.filename) or "piece-identite"
        content = file_storage.read()
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        max_size = current_app.config["APP_CONFIG"].MAX_IDENTITY_DOCUMENT_BYTES
        if not content:
            return None, "Pièce d'identité vide."
        if len(content) > max_size:
            return None, "Pièce d'identité trop volumineuse: limite 5 Mo."
        mime_type = (getattr(file_storage, "mimetype", "") or "").lower()
        if mime_type not in IDENTITY_DOCUMENT_MIME_TYPES:
            return None, "Format de pièce invalide: PDF, JPG ou PNG uniquement."
        return {
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "content": content,
        }, None

    @staticmethod
    def authenticate(email: str, password: str) -> tuple[bool, str]:
        rows = DatabasePool.execute_query(
            """
            SELECT id, email, password_hash, role, status,
                   temporary_password_expires_at, must_change_password
            FROM iam_users
            WHERE email = %s
            LIMIT 1
            """,
            ((email or "").strip().lower(),),
            dictionary=True,
        )
        user = rows[0] if rows else None
        if not user or not user.get("password_hash") or not check_password_hash(user["password_hash"], password or ""):
            return False, "Identifiants invalides."
        if user["status"] != "approved":
            return False, "Compte en attente de validation administrative."
        if user.get("temporary_password_expires_at"):
            expires_at = user["temporary_password_expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at < datetime.now():
                return False, "Mot de passe temporaire expiré."
        session.clear()
        session["user_id"] = int(user["id"])
        session["email"] = user["email"]
        session["role"] = user["role"]
        session["status"] = user["status"]
        session["must_change_password"] = bool(user.get("must_change_password"))
        return True, "Connexion réussie."

    @staticmethod
    def logout() -> None:
        session.clear()

    @staticmethod
    def list_account_requests(reviewer: dict[str, Any]) -> list[dict[str, Any]]:
        """Return account requests the current reviewer is allowed to manage."""
        if reviewer.get("role") != "admin" or reviewer.get("status") != "approved":
            return []

        return DatabasePool.execute_query(
            """
            SELECT u.id, u.email, u.role, u.first_name, u.last_name, u.birthdate, u.profession,
                   u.order_number, u.phone, u.status, u.requested_at, u.reviewed_at, u.review_note,
                   d.id IS NOT NULL AS has_identity_document,
                   d.filename AS identity_document_filename,
                   d.mime_type AS identity_document_mime_type,
                   d.size_bytes AS identity_document_size
            FROM iam_users u
            LEFT JOIN identity_documents d ON d.user_id = u.id
            WHERE u.role = 'prescriber'
            ORDER BY
                CASE u.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
                u.requested_at DESC
            """,
            dictionary=True,
        )

    @staticmethod
    def list_prescriber_requests() -> list[dict[str, Any]]:
        return DatabasePool.execute_query(
            """
            SELECT id, email, role, first_name, last_name, birthdate, profession,
                   order_number, phone, status, requested_at, reviewed_at, review_note
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
            return target.get("role") == "prescriber"
        return False

    @staticmethod
    def build_temporary_password_message(target: dict[str, Any], password: str) -> str:
        """Build the text an admin can send when SMTP is unavailable."""
        full_name = " ".join([target.get("first_name") or "", target.get("last_name") or ""]).strip()
        greeting = f"Bonjour {full_name}," if full_name else "Bonjour,"
        return (
            f"{greeting}\n\n"
            "Votre compte prescripteur Projet IAM a été validé.\n\n"
            f"Adresse de connexion: {target['email']}\n"
            f"Mot de passe temporaire: {password}\n\n"
            "Ce mot de passe est valable 24h. Vous devrez le changer à la première connexion.\n"
            "Connexion: https://projet-iam-web-production.up.railway.app/connexion\n\n"
            "Projet IAM"
        )

    @staticmethod
    def review_account(user_id: int, reviewer: dict[str, Any], approve: bool, note: str = "") -> tuple[bool, str, dict[str, Any] | None]:
        target = AuthService.get_user(user_id)
        if not target:
            return False, "Compte introuvable.", None
        if not AuthService.can_review(reviewer, target):
            return False, "Vous ne pouvez pas traiter cette demande.", None
        status = "approved" if approve else "rejected"
        password = secrets.token_urlsafe(12) if approve else ""
        password_hash = generate_password_hash(password) if approve else None
        email_sent = False
        manual_delivery = None
        if approve:
            manual_message = AuthService.build_temporary_password_message(target, password)
            try:
                EmailService.send(
                    target["email"],
                    "Votre compte Projet IAM est validé",
                    manual_message,
                )
                email_sent = True
            except EmailDeliveryError:
                manual_delivery = {
                    "required": True,
                    "email": target["email"],
                    "text": manual_message,
                    "expires_in_hours": 24,
                }
        with DatabasePool.get_cursor() as cursor:
            if approve:
                cursor.execute(
                    """
                    UPDATE iam_users
                    SET status = %s,
                        password_hash = %s,
                        temporary_password_expires_at = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL 24 HOUR),
                        must_change_password = 1,
                        reviewed_by = %s,
                        reviewed_at = CURRENT_TIMESTAMP,
                        review_note = %s
                    WHERE id = %s
                    """,
                    (status, password_hash, int(reviewer["id"]), (note or "").strip() or None, user_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE iam_users
                    SET status = %s,
                        reviewed_by = %s,
                        reviewed_at = CURRENT_TIMESTAMP,
                        review_note = %s
                    WHERE id = %s
                    """,
                    (status, int(reviewer["id"]), (note or "").strip() or None, user_id),
                )
            cursor.execute("DELETE FROM identity_documents WHERE user_id = %s", (user_id,))
        if not approve:
            return True, "Demande refusée.", None
        if email_sent:
            return True, "Demande acceptée et mot de passe envoyé.", None
        return True, "Demande acceptée. SMTP indisponible: copiez le message de transmission.", {"manual_delivery": manual_delivery}

    @staticmethod
    def review_prescriber(user_id: int, reviewer_id: int, approve: bool, note: str = "") -> None:
        reviewer = AuthService.get_user(reviewer_id) or {"id": reviewer_id, "role": "admin", "status": "approved"}
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
                        temporary_password_expires_at = NULL,
                        must_change_password = 0,
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

    @staticmethod
    def get_identity_document(user_id: int) -> dict[str, Any] | None:
        rows = DatabasePool.execute_query(
            """
            SELECT d.filename, d.mime_type, d.size_bytes, d.content, u.status
            FROM identity_documents d
            JOIN iam_users u ON u.id = d.user_id
            WHERE d.user_id = %s AND u.status = 'pending'
            LIMIT 1
            """,
            (user_id,),
            dictionary=True,
        )
        return rows[0] if rows else None

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> tuple[bool, str]:
        if not new_password or len(new_password) < 8:
            return False, "Le nouveau mot de passe doit contenir au moins 8 caractères."
        rows = DatabasePool.execute_query(
            """
            SELECT password_hash
            FROM iam_users
            WHERE id = %s
            LIMIT 1
            """,
            (user_id,),
            dictionary=True,
        )
        user = rows[0] if rows else None
        if not user or not check_password_hash(user["password_hash"], current_password or ""):
            return False, "Mot de passe actuel invalide."
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE iam_users
                SET password_hash = %s,
                    temporary_password_expires_at = NULL,
                    must_change_password = 0
                WHERE id = %s
                """,
                (generate_password_hash(new_password), user_id),
            )
        session["must_change_password"] = False
        return True, "Mot de passe mis à jour."


ESTABLISHMENT_FIELDS = (
    "name",
    "type",
    "address",
    "phone",
    "email",
    "identifier_label",
    "identifier_value",
    "secondary_identifier_label",
    "secondary_identifier_value",
    "free_text",
)


class EstablishmentService:
    """Prescriber establishment management."""

    @staticmethod
    def list_for_prescriber(user_id: int, active_only: bool = True) -> list[dict[str, Any]]:
        where_active = "AND is_active = 1" if active_only else ""
        rows = DatabasePool.execute_query(
            f"""
            SELECT id, name, type, address, phone, email, identifier_label, identifier_value,
                   secondary_identifier_label, secondary_identifier_value, free_text,
                   logo_filename, logo_mime_type, logo_size_bytes, logo_content IS NOT NULL AS has_logo,
                   is_active, created_at, updated_at
            FROM prescriber_establishments
            WHERE user_id = %s {where_active}
            ORDER BY is_active DESC, name ASC
            """,
            (user_id,),
            dictionary=True,
        )
        return [EstablishmentService.serialize(row) for row in rows]

    @staticmethod
    def list_all_for_admin() -> list[dict[str, Any]]:
        rows = DatabasePool.execute_query(
            """
            SELECT e.id, e.user_id, e.name, e.type, e.address, e.phone, e.email,
                   e.identifier_label, e.identifier_value, e.secondary_identifier_label,
                   e.secondary_identifier_value, e.free_text, e.logo_filename,
                   e.logo_mime_type, e.logo_size_bytes, e.logo_content IS NOT NULL AS has_logo,
                   e.is_active, e.created_at, e.updated_at,
                   u.first_name, u.last_name, u.email AS prescriber_email
            FROM prescriber_establishments e
            JOIN iam_users u ON u.id = e.user_id
            ORDER BY u.last_name ASC, u.first_name ASC, e.name ASC
            """,
            dictionary=True,
        )
        return [EstablishmentService.serialize(row, include_prescriber=True) for row in rows]

    @staticmethod
    def upsert(user_id: int, payload: dict[str, Any], logo: Any = None, establishment_id: int | None = None) -> tuple[bool, str, dict[str, Any] | None]:
        data = {field: str(payload.get(field) or "").strip() for field in ESTABLISHMENT_FIELDS}
        data["is_active"] = str(payload.get("is_active", "1")).lower() not in {"0", "false", "no"}
        if not data["name"]:
            return False, "Nom d'établissement requis.", None
        logo_data, error = EstablishmentService.validate_logo(logo)
        if error:
            return False, error, None
        with DatabasePool.get_cursor() as cursor:
            if establishment_id:
                logo_sql = ""
                params: list[Any] = [
                    data["name"],
                    data["type"] or None,
                    data["address"] or None,
                    data["phone"] or None,
                    data["email"] or None,
                    data["identifier_label"] or None,
                    data["identifier_value"] or None,
                    data["secondary_identifier_label"] or None,
                    data["secondary_identifier_value"] or None,
                    data["free_text"] or None,
                    1 if data["is_active"] else 0,
                ]
                if logo_data:
                    logo_sql = """,
                        logo_filename = %s,
                        logo_mime_type = %s,
                        logo_size_bytes = %s,
                        logo_content = %s"""
                    params.extend([
                        logo_data["filename"],
                        logo_data["mime_type"],
                        logo_data["size_bytes"],
                        logo_data["content"],
                    ])
                params.extend([establishment_id, user_id])
                cursor.execute(
                    f"""
                    UPDATE prescriber_establishments
                    SET name = %s,
                        type = %s,
                        address = %s,
                        phone = %s,
                        email = %s,
                        identifier_label = %s,
                        identifier_value = %s,
                        secondary_identifier_label = %s,
                        secondary_identifier_value = %s,
                        free_text = %s,
                        is_active = %s
                        {logo_sql}
                    WHERE id = %s AND user_id = %s
                    """,
                    tuple(params),
                )
                target_id = establishment_id
            else:
                cursor.execute(
                    """
                    INSERT INTO prescriber_establishments
                        (user_id, name, type, address, phone, email, identifier_label, identifier_value,
                         secondary_identifier_label, secondary_identifier_value, free_text,
                         logo_filename, logo_mime_type, logo_size_bytes, logo_content, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        data["name"],
                        data["type"] or None,
                        data["address"] or None,
                        data["phone"] or None,
                        data["email"] or None,
                        data["identifier_label"] or None,
                        data["identifier_value"] or None,
                        data["secondary_identifier_label"] or None,
                        data["secondary_identifier_value"] or None,
                        data["free_text"] or None,
                        logo_data["filename"] if logo_data else None,
                        logo_data["mime_type"] if logo_data else None,
                        logo_data["size_bytes"] if logo_data else None,
                        logo_data["content"] if logo_data else None,
                        1 if data["is_active"] else 0,
                    ),
                )
                target_id = int(cursor.lastrowid)
        establishment = EstablishmentService.get(user_id, target_id)
        return True, "Établissement enregistré.", establishment

    @staticmethod
    def get(user_id: int, establishment_id: int) -> dict[str, Any] | None:
        rows = DatabasePool.execute_query(
            """
            SELECT id, name, type, address, phone, email, identifier_label, identifier_value,
                   secondary_identifier_label, secondary_identifier_value, free_text,
                   logo_filename, logo_mime_type, logo_size_bytes, logo_content IS NOT NULL AS has_logo,
                   is_active, created_at, updated_at
            FROM prescriber_establishments
            WHERE id = %s AND user_id = %s
            LIMIT 1
            """,
            (establishment_id, user_id),
            dictionary=True,
        )
        return EstablishmentService.serialize(rows[0]) if rows else None

    @staticmethod
    def delete(user_id: int, establishment_id: int) -> bool:
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "UPDATE prescriber_establishments SET is_active = 0 WHERE id = %s AND user_id = %s",
                (establishment_id, user_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def validate_logo(file_storage: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not file_storage or not getattr(file_storage, "filename", ""):
            return None, None
        filename = secure_filename(file_storage.filename) or "logo"
        content = file_storage.read()
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass
        if len(content) > 1024 * 1024:
            return None, "Logo trop volumineux: limite 1 Mo."
        mime_type = (getattr(file_storage, "mimetype", "") or "").lower()
        if mime_type not in {"image/jpeg", "image/png"}:
            return None, "Format logo invalide: JPG ou PNG uniquement."
        return {"filename": filename, "mime_type": mime_type, "size_bytes": len(content), "content": content}, None

    @staticmethod
    def serialize(row: dict[str, Any], include_prescriber: bool = False) -> dict[str, Any]:
        item = {key: row.get(key) for key in (
            "id", "name", "type", "address", "phone", "email", "identifier_label", "identifier_value",
            "secondary_identifier_label", "secondary_identifier_value", "free_text", "logo_filename",
            "logo_mime_type", "logo_size_bytes", "has_logo", "is_active"
        )}
        item["has_logo"] = bool(item.get("has_logo"))
        item["is_active"] = bool(item.get("is_active"))
        if include_prescriber:
            item["prescriber"] = {
                "id": row.get("user_id"),
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "email": row.get("prescriber_email"),
            }
        return item


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
        user = AuthService.current_user()
        if not user:
            return redirect(url_for("web.login", next=request.path))
        if user.get("must_change_password") and request.endpoint != "web.change_password":
            return redirect(url_for("web.change_password"))
        return view(*args, **kwargs)

    return wrapped


def require_approved_prescriber(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = AuthService.current_user()
        if not user:
            return redirect(url_for("web.login", next=request.path))
        if user.get("must_change_password"):
            return redirect(url_for("web.change_password"))
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
            return redirect(url_for("web.login", next=request.path))
        if user.get("must_change_password"):
            return redirect(url_for("web.change_password"))
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
            return redirect(url_for("web.login", next=request.path))
        if user.get("must_change_password"):
            return redirect(url_for("web.change_password"))
        if user["role"] != "admin" or user["status"] != "approved":
            flash("Accès modération requis.", "warning")
            return redirect(url_for("web.home"))
        return view(*args, **kwargs)

    return wrapped
