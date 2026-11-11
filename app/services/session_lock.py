"""Session lock after inactivity (ticket 17).

After SESSION_IDLE_LOCK_MINUTES without a request, the session is locked:
the API answers 423 `session_locked` and pages redirect to the login page,
so no patient data is shown. The same user unlocks with their password and
finds everything as it was (drafts are saved on the server). Logging in as
someone else replaces the session.
"""
from __future__ import annotations

import os
import time

from flask import jsonify, redirect, request, session, url_for


IDLE_SECONDS = int(float(os.environ.get("SESSION_IDLE_LOCK_MINUTES", "10")) * 60)

# Reachable while locked: unlocking, switching user, reading the lock state, static files.
OPEN_ENDPOINTS = {
    "api.auth_unlock", "api.auth_login", "api.auth_logout", "api.auth_session",
    "web.login", "web.logout", "web.home", "static",
}


def enforce_session_lock():
    """Flask before_request hook."""
    if not session.get("user_id"):
        return None
    now = int(time.time())
    last = session.get("last_activity")
    if last is not None and now - int(last) > IDLE_SECONDS:
        session["locked"] = True

    if session.get("locked"):
        if request.endpoint in OPEN_ENDPOINTS:
            return None
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "code": "session_locked",
                            "error": "Session verrouillée après inactivité. Saisissez votre mot de passe."}), 423
        return redirect(url_for("web.login", next=request.path, locked=1))

    session["last_activity"] = now
    return None


def unlock() -> None:
    session.pop("locked", None)
    session["last_activity"] = int(time.time())


def is_locked() -> bool:
    return bool(session.get("locked"))
