"""Access log: who read or changed which ordonnance or patient, and when.

Identifiers only, never medical data. The table is append-only (migration 013).
Routes record an entry after a successful access, so a refused access is not
logged as a read.
"""
from __future__ import annotations

from typing import Any

from app.services.database import DatabasePool


OBJECT_TYPES = {"ordonnance", "patient"}
ACTIONS = {"read", "search", "list", "create", "update", "check", "issue", "print",
           "cancel", "renew", "discard"}


class AccessLog:
    @staticmethod
    def record(user_id: int, object_type: str, object_id: int | None, action: str, ip: str | None = None) -> None:
        if object_type not in OBJECT_TYPES or action not in ACTIONS:
            raise ValueError(f"Entrée de journal inconnue : {object_type}/{action}")
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO access_log (user_id, object_type, object_id, action, ip) VALUES (%s, %s, %s, %s, %s)",
                (user_id, object_type, object_id, action, (ip or "")[:45] or None),
            )

    @staticmethod
    def for_object(object_type: str, object_id: int, limit: int = 200) -> list[dict[str, Any]]:
        rows = DatabasePool.execute_query(
            """
            SELECT l.action, l.created_at, u.id AS user_id, u.first_name, u.last_name, u.email, u.role
            FROM access_log l
            JOIN iam_users u ON u.id = l.user_id
            WHERE l.object_type = %s AND l.object_id = %s
            ORDER BY l.id DESC
            LIMIT %s
            """,
            (object_type, object_id, limit),
            dictionary=True,
        )
        return [
            {
                "action": row["action"],
                "at": row["created_at"].isoformat(),
                "user": {key: row[key] for key in ("user_id", "first_name", "last_name", "email", "role")}
                | {"email": row["email"]},
            }
            for row in rows
        ]
