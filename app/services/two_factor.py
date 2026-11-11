"""Two-factor authentication with an authenticator app (ticket 22).

Optional during the pilot. TWO_FACTOR_REQUIRED=true makes it mandatory:
an account without it must enrol before anything else.

After the password, a 2FA account's session waits for a code: the API
answers 401 `two_factor_required` and pages redirect to the code page.
A code is accepted once (last time step kept); a recovery code once too.
"""
from __future__ import annotations

import os
import secrets
import time

import pyotp
from flask import jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.services.database import DatabasePool
from app.services.vault import vault


ISSUER = "DigiRemed"
RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
RECOVERY_COUNT = 10

OPEN_WHILE_PENDING = {"api.two_factor_verify", "api.auth_login", "api.auth_logout", "api.auth_session",
                      "web.two_factor_page", "web.login", "web.logout", "web.home", "static"}
OPEN_WHILE_ENROLLING = OPEN_WHILE_PENDING | {"api.two_factor_status", "api.two_factor_setup",
                                             "api.two_factor_confirm", "web.security_page"}


def required() -> bool:
    return os.environ.get("TWO_FACTOR_REQUIRED", "false").lower() in {"1", "true", "yes"}


class TwoFactor:
    @staticmethod
    def is_enabled(user_id: int) -> bool:
        rows = DatabasePool.execute_query(
            "SELECT enabled_at FROM user_two_factor WHERE user_id = %s", (user_id,))
        return bool(rows and rows[0][0])

    @staticmethod
    def setup(user_id: int, email: str) -> dict[str, str]:
        """Draw a new secret, kept pending until a code confirms it."""
        secret = pyotp.random_base32()
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_two_factor (user_id, pending_secret) VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE pending_secret = %s
                """,
                (user_id, vault().seal_json(secret), vault().seal_json(secret)),
            )
        uri = pyotp.TOTP(secret).provisioning_uri(name=email or str(user_id), issuer_name=ISSUER)
        return {"secret": secret, "otpauth_uri": uri}

    @staticmethod
    def confirm(user_id: int, code: str) -> list[str] | None:
        """Enable 2FA if the code matches the pending secret; return the recovery codes, shown once."""
        rows = DatabasePool.execute_query(
            "SELECT pending_secret FROM user_two_factor WHERE user_id = %s", (user_id,))
        if not rows or not rows[0][0]:
            return None
        secret = vault().open_json(rows[0][0])
        if not pyotp.TOTP(secret).verify(str(code or "").strip(), valid_window=1):
            return None
        codes = [_recovery_code() for _ in range(RECOVERY_COUNT)]
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_two_factor
                SET secret = pending_secret, pending_secret = NULL, enabled_at = NOW(), last_timestep = %s
                WHERE user_id = %s
                """,
                (_timestep(), user_id),
            )
            cursor.execute("DELETE FROM user_recovery_codes WHERE user_id = %s", (user_id,))
            cursor.executemany(
                "INSERT INTO user_recovery_codes (user_id, code_hash) VALUES (%s, %s)",
                [(user_id, generate_password_hash(code)) for code in codes],
            )
        return codes

    @staticmethod
    def verify(user_id: int, code: str = "", recovery_code: str = "") -> bool:
        if recovery_code:
            return TwoFactor._use_recovery_code(user_id, recovery_code)
        rows = DatabasePool.execute_query(
            "SELECT secret FROM user_two_factor WHERE user_id = %s AND enabled_at IS NOT NULL", (user_id,))
        if not rows:
            return False
        totp = pyotp.TOTP(vault().open_json(rows[0][0]))
        code = str(code or "").strip()
        now = _timestep()
        for step in (now - 1, now, now + 1):
            if secrets.compare_digest(totp.at(step * totp.interval), code):
                last = TwoFactor._last_timestep(user_id)
                if last is not None and step <= last:
                    return False  # already used: no replay
                with DatabasePool.get_cursor() as cursor:
                    cursor.execute("UPDATE user_two_factor SET last_timestep = %s WHERE user_id = %s",
                                   (step, user_id))
                return True
        return False

    @staticmethod
    def reset(user_id: int) -> None:
        with DatabasePool.get_cursor() as cursor:
            cursor.execute("DELETE FROM user_two_factor WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM user_recovery_codes WHERE user_id = %s", (user_id,))

    @staticmethod
    def _last_timestep(user_id: int) -> int | None:
        rows = DatabasePool.execute_query("SELECT last_timestep FROM user_two_factor WHERE user_id = %s", (user_id,))
        return rows[0][0] if rows else None

    @staticmethod
    def _use_recovery_code(user_id: int, code: str) -> bool:
        code = str(code or "").strip().lower()
        rows = DatabasePool.execute_query(
            "SELECT id, code_hash FROM user_recovery_codes WHERE user_id = %s AND used_at IS NULL", (user_id,))
        for row_id, code_hash in rows:
            if check_password_hash(code_hash, code):
                with DatabasePool.get_cursor() as cursor:
                    cursor.execute("UPDATE user_recovery_codes SET used_at = NOW() WHERE id = %s AND used_at IS NULL",
                                   (row_id,))
                    return cursor.rowcount == 1
        return False


# Session states -----------------------------------------------------------------

def after_password(user_id: int, role: str) -> dict[str, bool]:
    """Call right after a successful password check; returns what the client must do next.

    The global requirement applies to prescribers; any account may enable 2FA.
    """
    if TwoFactor.is_enabled(user_id):
        session["two_factor_pending"] = True
        return {"two_factor_required": True}
    if required() and role == "prescriber":
        session["two_factor_enroll"] = True
        return {"two_factor_enrollment_required": True}
    return {}


def complete() -> None:
    session.pop("two_factor_pending", None)
    session.pop("two_factor_enroll", None)


def enforce_two_factor():
    """Flask before_request hook, after the session lock."""
    if not session.get("user_id"):
        return None
    if session.get("two_factor_pending") and request.endpoint not in OPEN_WHILE_PENDING:
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "code": "two_factor_required",
                            "error": "Saisissez le code de votre application d'authentification."}), 401
        return redirect(url_for("web.two_factor_page", next=request.path))
    if session.get("two_factor_enroll") and request.endpoint not in OPEN_WHILE_ENROLLING:
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "code": "two_factor_enrollment_required",
                            "error": "Activez la double authentification pour continuer."}), 403
        return redirect(url_for("web.security_page"))
    return None


def _timestep() -> int:
    return int(time.time()) // 30


def _recovery_code() -> str:
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"
