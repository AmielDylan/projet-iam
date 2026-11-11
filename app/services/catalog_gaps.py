"""Catalog gaps seen in use, and catalog entries created by an administrator.

Free-text medications are counted when an ordonnance is issued, once per
ordonnance and without any link to the patient, the prescriber or the
ordonnance. Together with searches that found nothing, they tell the
administrator which medications to add. A created entry carries thesaurus
substances, so the IAM analysis covers it for every prescriber.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from mysql.connector import Error

from app.services.analysis import normalize_dci
from app.services.database import DatabasePool
from app.services.referential import ReferentialService


class CatalogEntryError(ValueError):
    """Raised when a catalog entry cannot be created; the message is shown to the admin."""


class CatalogGaps:
    @staticmethod
    def record_free_entries(names: list[str]) -> None:
        keys: dict[str, str] = {}
        for name in names:
            key = normalize_dci(name)[:190]
            if key and key not in keys:
                keys[key] = str(name).strip()[:255]
        if not keys:
            return
        with DatabasePool.get_cursor() as cursor:
            for key, name in keys.items():
                cursor.execute(
                    """
                    INSERT INTO medication_free_entries (name_key, name, occurrences) VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE occurrences = occurrences + 1, last_seen_at = CURRENT_TIMESTAMP
                    """,
                    (key, name),
                )

    @staticmethod
    def list(limit: int = 100) -> list[dict[str, Any]]:
        """Open gaps, most frequent first: free-text entries and searches without result."""
        gaps: dict[str, dict[str, Any]] = {}
        resolved = set()
        for row in DatabasePool.execute_query(
            "SELECT name_key, name, occurrences, resolved_catalog_id, last_seen_at FROM medication_free_entries",
            dictionary=True,
        ):
            if row["resolved_catalog_id"]:
                resolved.add(row["name_key"])
                continue
            if row["occurrences"]:
                gaps[row["name_key"]] = {"label": row["name"], "free_text_count": row["occurrences"],
                                         "search_miss_count": 0, "last_seen_at": row["last_seen_at"]}
        for row in DatabasePool.execute_query(
            "SELECT query, COUNT(*) AS n, MAX(created_at) AS last_seen_at FROM medication_search_miss GROUP BY query",
            dictionary=True,
        ):
            key = normalize_dci(row["query"])[:190]
            if not key or key in resolved:
                continue
            gap = gaps.setdefault(key, {"label": row["query"].strip(), "free_text_count": 0,
                                        "search_miss_count": 0, "last_seen_at": row["last_seen_at"]})
            gap["search_miss_count"] += row["n"]
            gap["last_seen_at"] = max(gap["last_seen_at"], row["last_seen_at"])

        result = []
        for key, gap in gaps.items():
            total = gap["free_text_count"] + gap["search_miss_count"]
            result.append({**gap, "key": key, "total": total, "last_seen_at": gap["last_seen_at"].isoformat()})
        result.sort(key=lambda gap: (-gap["total"], gap["label"].upper()))
        return result[:limit]

    @staticmethod
    def substances(query: str, limit: int = 15) -> list[str]:
        """Thesaurus substances for the admin's substance picker."""
        query = (query or "").strip()
        if len(query) < 2:
            return []
        rows = DatabasePool.execute_query(
            "SELECT substances FROM substances WHERE substances LIKE %s ORDER BY substances LIMIT %s",
            (f"%{query}%", limit),
        )
        return [row[0] for row in rows]

    @staticmethod
    def create_entry(admin_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "").strip()
        dosage = str(payload.get("dosage") or "").strip()
        form = str(payload.get("form") or "").strip()
        if not name or len(name) > 255:
            raise CatalogEntryError("Nom du médicament requis (255 caractères au plus).")
        wanted = payload.get("substances") or []
        if isinstance(wanted, str):
            wanted = wanted.split("|")
        wanted = [normalize_dci(s) for s in wanted if normalize_dci(s)]
        if not wanted:
            raise CatalogEntryError("Rattachez au moins une substance du thésaurus.")

        known = {normalize_dci(row[0]): row[0] for row in DatabasePool.execute_query("SELECT substances FROM substances")}
        missing = [s for s in wanted if s not in known]
        if missing:
            raise CatalogEntryError(f"Substance absente du thésaurus : {', '.join(missing)}")
        substances = list(dict.fromkeys(known[s] for s in wanted))

        identity = "|".join([normalize_dci(name), normalize_dci(dosage), normalize_dci(form), *sorted(substances)])
        batch_id = f"manual-{admin_id}-{uuid.uuid4().hex[:8]}"
        try:
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO medication_catalog
                        (nom_medicament, dosage, forme_galenique, substances, specialite, searchable_text,
                         source_hash, normalized_key, match_status, last_import_batch_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual', %s)
                    """,
                    (name, dosage or None, form or None, "|".join(substances), name,
                     " ".join([name, dosage, form, *substances]),
                     hashlib.sha256(f"manual|{identity}".encode()).hexdigest(),
                     hashlib.sha256(f"{normalize_dci(name)}|{normalize_dci(dosage)}".encode()).hexdigest(),
                     batch_id),
                )
                catalog_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO medication_enrichment_audit
                        (import_batch_id, catalog_id, action_type, target_table, target_id, status, reason, payload_json)
                    VALUES (%s, %s, 'manual_catalog_entry', 'medication_catalog', %s, 'applied', %s, %s)
                    """,
                    (batch_id, catalog_id, catalog_id, f"Ajout manuel par l'administrateur {admin_id}",
                     json.dumps({"name": name, "dosage": dosage, "form": form, "substances": substances},
                                ensure_ascii=False)),
                )
                resolves = normalize_dci(payload.get("resolves") or name)[:190]
                cursor.execute(
                    """
                    INSERT INTO medication_free_entries (name_key, name, occurrences, resolved_catalog_id)
                    VALUES (%s, %s, 0, %s)
                    ON DUPLICATE KEY UPDATE resolved_catalog_id = %s
                    """,
                    (resolves, name, catalog_id, catalog_id),
                )
        except Error as exc:
            if getattr(exc, "errno", None) == 1062:
                raise CatalogEntryError("Ce médicament existe déjà au catalogue.") from None
            raise
        ReferentialService.record("catalog", f"Ajout manuel : {name}"[:190])
        return {"id": catalog_id, "name": name, "dosage": dosage, "form": form, "substances": substances}
