"""Prescriber codes: four characters that prefix every ordonnance number.

No ambiguous characters (0/O, 1/I/L), so a pharmacist can read a number
aloud or type it without mistakes. Given at account approval, and
retroactively to approved prescribers who have none.
"""
from __future__ import annotations

import secrets

from mysql.connector import Error

from app.services.database import DatabasePool


ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LENGTH = 4


def generate() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


class PrescriberCodes:
    @staticmethod
    def of(user_id: int) -> str | None:
        rows = DatabasePool.execute_query("SELECT prescriber_code FROM iam_users WHERE id = %s", (user_id,))
        return rows[0][0] if rows else None

    @staticmethod
    def ensure(user_id: int) -> str:
        """Return the prescriber's code, giving one if needed."""
        code = PrescriberCodes.of(user_id)
        if code:
            return code
        for _ in range(50):
            candidate = generate()
            try:
                with DatabasePool.get_cursor() as cursor:
                    cursor.execute(
                        "UPDATE iam_users SET prescriber_code = %s WHERE id = %s AND prescriber_code IS NULL",
                        (candidate, user_id),
                    )
            except Error as exc:
                if getattr(exc, "errno", None) == 1062:  # code already taken: draw again
                    continue
                raise
            return PrescriberCodes.of(user_id)
        raise RuntimeError("Impossible d'attribuer un code prescripteur")

    @staticmethod
    def ensure_all() -> int:
        """Give a code to every approved prescriber without one; return how many."""
        rows = DatabasePool.execute_query(
            "SELECT id FROM iam_users WHERE role = 'prescriber' AND status = 'approved' AND prescriber_code IS NULL"
        )
        for (user_id,) in rows:
            PrescriberCodes.ensure(user_id)
        return len(rows)
