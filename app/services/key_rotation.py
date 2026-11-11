"""Key rotation for health data (used by scripts/rotate_data_keys.py).

Encryption key rotation:
  1. Generate a key: python -m app.services.vault
  2. Put it first in DATA_ENCRYPTION_KEYS, keep the old one after it: "k2:NEW,k1:OLD". Deploy.
  3. Run: python scripts/rotate_data_keys.py reseal
  4. When it reports 0 values left on old keys, remove the old key from DATA_ENCRYPTION_KEYS. Deploy.

Search index key rotation:
  1. Replace DATA_INDEX_KEY. Deploy (patient search is empty until step 2 ends).
  2. Run: python scripts/rotate_data_keys.py reindex
"""
from __future__ import annotations

from app.services.database import DatabasePool
from app.services.vault import vault


SEALED_COLUMNS = (
    ("patients", "record"),
    ("ordonnances", "content"),
    ("ordonnances", "snapshot"),
    ("ordonnances", "cancel_reason"),
    ("ordonnance_versions", "content"),
)


def reseal_all(batch_size: int = 200) -> dict[tuple[str, str], int]:
    """Re-encrypt every value sealed with an old key; return how many per column."""
    counts = {}
    for table, column in SEALED_COLUMNS:
        counts[(table, column)] = _reseal_column(table, column, batch_size)
    return counts


def _reseal_column(table: str, column: str, batch_size: int) -> int:
    done = 0
    last_id = 0
    while True:
        rows = DatabasePool.execute_query(
            f"SELECT id, `{column}` FROM `{table}` WHERE id > %s AND `{column}` IS NOT NULL ORDER BY id LIMIT %s",
            (last_id, batch_size),
        )
        if not rows:
            return done
        with DatabasePool.get_cursor() as cursor:
            cursor.execute("SET @digiremed_key_rotation = 1")
            try:
                for row_id, sealed in rows:
                    if not vault().needs_reseal(sealed):
                        continue
                    resealed = vault().reseal(sealed)
                    if vault().open_json(resealed) != vault().open_json(sealed):
                        raise RuntimeError(f"Rechiffrement incohérent : {table}.{column} #{row_id}")
                    cursor.execute(
                        f"UPDATE `{table}` SET `{column}` = %s WHERE id = %s AND `{column}` = %s",
                        (resealed, row_id, sealed),
                    )
                    done += cursor.rowcount
            finally:
                cursor.execute("SET @digiremed_key_rotation = NULL")
        last_id = rows[-1][0]


def reindex_patients() -> int:
    """Rebuild every patient search token with the current DATA_INDEX_KEY."""
    from app.services.patient import _birthdate_token, _write_tokens

    rows = DatabasePool.execute_query("SELECT id, owner_id, record FROM patients ORDER BY id")
    for patient_id, owner_id, sealed in rows:
        record = vault().open_json(sealed)
        with DatabasePool.get_cursor() as cursor:
            cursor.execute("DELETE FROM patient_search_tokens WHERE patient_id = %s", (patient_id,))
            cursor.execute("UPDATE patients SET birthdate_token = %s WHERE id = %s",
                           (_birthdate_token(record), patient_id))
            _write_tokens(cursor, owner_id, patient_id, record)
    return len(rows)
