"""Prescriber signature and stamp: transparent PNG images kept in the account.

The background is removed in the browser before upload (white paper made transparent).
Images are sealed by the vault: a signature could be used to forge an ordonnance.
They are frozen in the snapshot at issuance and shown on the PDF only; on paper the
prescriber signs and stamps by hand.
"""
from __future__ import annotations

import base64

from app.services.database import DatabasePool
from app.services.vault import vault


KINDS = ("signature", "stamp")
MAX_BYTES = 512 * 1024
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class AssetError(ValueError):
    """Raised when an image cannot be accepted; the message is shown to the prescriber."""


class PrescriberAssets:
    @staticmethod
    def save(user_id: int, kind: str, content: bytes) -> None:
        _check_kind(kind)
        if not content or not content.startswith(PNG_MAGIC):
            raise AssetError("L'image doit être un PNG.")
        if len(content) > MAX_BYTES:
            raise AssetError("Image trop lourde : 500 Ko au plus.")
        sealed = vault().seal_json(base64.b64encode(content).decode())
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO prescriber_assets (user_id, kind, content) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE content = %s",
                (user_id, kind, sealed, sealed),
            )

    @staticmethod
    def get(user_id: int, kind: str) -> bytes | None:
        _check_kind(kind)
        rows = DatabasePool.execute_query(
            "SELECT content FROM prescriber_assets WHERE user_id = %s AND kind = %s", (user_id, kind))
        return base64.b64decode(vault().open_json(rows[0][0])) if rows else None

    @staticmethod
    def delete(user_id: int, kind: str) -> None:
        _check_kind(kind)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute("DELETE FROM prescriber_assets WHERE user_id = %s AND kind = %s", (user_id, kind))

    @staticmethod
    def status(user_id: int) -> dict[str, bool]:
        rows = DatabasePool.execute_query("SELECT kind FROM prescriber_assets WHERE user_id = %s", (user_id,))
        present = {row[0] for row in rows}
        return {kind: kind in present for kind in KINDS}

    @staticmethod
    def data_uris(user_id: int) -> dict[str, str | None]:
        """For the issuance snapshot."""
        uris: dict[str, str | None] = {}
        for kind in KINDS:
            content = PrescriberAssets.get(user_id, kind)
            uris[kind] = f"data:image/png;base64,{base64.b64encode(content).decode()}" if content else None
        return uris


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise AssetError("Image inconnue : signature ou cachet seulement.")
