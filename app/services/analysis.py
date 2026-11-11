"""IAM analysis of an ordonnance.

Given the lines of a draft (and the patient's clinical data), return every
alert with a stable id and what it requires:

- blocking: a contraindication (CI). Never lifted, whatever the reason.
- justify: an ASDEC interaction, the same DCI on two lines, or a declared
  allergy. Lifted only by a written benefit-risk reason (a derogation).
- info: precautions (PE) and points to consider (APEC).

Substances always come from the catalog for catalog lines: what the browser
sends is never trusted. A failed lookup raises instead of hiding a risk.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from itertools import combinations
from typing import Any

from app.services.catalog import MedicationCatalogService
from app.services.interaction import InteractionService


NOT_CHECKED = [
    "La grossesse et l'allaitement",
    "La fonction rénale et hépatique",
    "Les doses et les durées de traitement",
    "Les plantes, compléments et préparations",
    "Les allergies à une classe de médicaments (seules les DCI déclarées sont comparées)",
    "Les lignes en saisie libre",
]

DISCLAIMER = (
    "Aide à la décision fondée sur le thésaurus des interactions médicamenteuses de l'ANSM (France). "
    "Elle ne remplace pas le jugement du prescripteur."
)

REQUIREMENT_BY_LEVEL = {"CI": "blocking", "ASDEC": "justify", "PE": "info", "APEC": "info"}


def analyze(
    lines: list[dict[str, Any]],
    patient: dict[str, Any] | None = None,
    derogations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze the lines of an ordonnance; see the module docstring."""
    resolved = [_resolve(line) for line in lines if _has_medication(line)]
    analyzable = [line for line in resolved if line["substances"]]

    alerts = []
    alerts += _interaction_alerts(analyzable)
    alerts += _same_substance_alerts(analyzable)
    alerts += _allergy_alerts(analyzable, patient or {})

    accepted = {
        str(alert_id): reason.strip()
        for alert_id, reason in (derogations or {}).items()
        if isinstance(reason, str) and reason.strip()
    }
    for alert in alerts:
        reason = accepted.get(alert["id"]) if alert["requirement"] == "justify" else None
        alert["derogation"] = reason

    blocking = [a for a in alerts if a["requirement"] == "blocking"]
    unjustified = [a for a in alerts if a["requirement"] == "justify" and not a["derogation"]]
    return {
        "alerts": alerts,
        "summary": {
            "lines_count": len(resolved),
            "blocking_count": len(blocking),
            "to_justify_count": len([a for a in alerts if a["requirement"] == "justify"]),
            "unjustified_count": len(unjustified),
            "can_issue": not blocking and not unjustified,
        },
        "scope": {
            "not_checked": NOT_CHECKED,
            "free_text_lines": [line["name"] for line in resolved if not line["substances"]],
            "disclaimer": DISCLAIMER,
        },
    }


# Line resolution ----------------------------------------------------------------

def _has_medication(line: dict[str, Any]) -> bool:
    return bool(line.get("medication_id") or str(line.get("name") or "").strip())


def _resolve(line: dict[str, Any]) -> dict[str, Any]:
    entry = None
    if line.get("medication_id"):
        entry = MedicationCatalogService.get(int(line["medication_id"]))
    # Compare without accents, but look interactions up with the catalog spelling.
    lookup: dict[str, str] = {}
    for substance in (entry or {}).get("substances", []):
        key = normalize_dci(substance)
        if key and key not in lookup:
            lookup[key] = str(substance).strip().upper()
    return {
        "line_id": str(line.get("line_id")),
        "name": str(line.get("name") or (entry or {}).get("name") or "").strip(),
        "substances": sorted(lookup),
        "lookup": lookup,
        "fingerprint": _fingerprint(line),
    }


def normalize_dci(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", text).strip().upper()


def _fingerprint(line: dict[str, Any]) -> str:
    """Any change to a line changes its fingerprint, and so the ids of its alerts."""
    return hashlib.sha256(json.dumps(line, sort_keys=True, default=str).encode()).hexdigest()


def _alert_id(alert_type: str, level: str | None, key: str, lines: list[dict[str, Any]]) -> str:
    parts = [alert_type, level or "", key, *sorted(line["fingerprint"] for line in lines)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


# Alerts -------------------------------------------------------------------------

def _interaction_alerts(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    for first, second in combinations(lines, 2):
        seen = set()
        for substance_1 in first["substances"]:
            for substance_2 in second["substances"]:
                pair = (first["lookup"][substance_1], second["lookup"][substance_2])
                for interaction in InteractionService.get_interactions(*pair):
                    level = level_from_niveau(interaction.get("niveau"))
                    classes = sorted([interaction.get("class_1") or "", interaction.get("class_2") or ""])
                    key = (level, *classes)
                    if key in seen:
                        continue
                    seen.add(key)
                    alerts.append({
                        "id": _alert_id("interaction", level, "/".join(classes), [first, second]),
                        "type": "interaction",
                        "level": level,
                        "requirement": REQUIREMENT_BY_LEVEL.get(level, "info"),
                        "line_ids": [first["line_id"], second["line_id"]],
                        "message": f"{first['name']} et {second['name']} : {interaction.get('niveau') or 'interaction'}",
                        "details": {
                            "classes": classes,
                            "substances": [substance_1, substance_2],
                            "niveau": interaction.get("niveau") or "",
                            "risks": interaction.get("risques") or "",
                            "conduct": interaction.get("actions") or "",
                            "comment": interaction.get("details") or "",
                        },
                    })
    order = {"CI": 0, "ASDEC": 1, "PE": 2, "APEC": 3, None: 4}
    return sorted(alerts, key=lambda alert: order.get(alert["level"], 4))


def _same_substance_alerts(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_substance: dict[str, list[dict[str, Any]]] = {}
    for line in lines:
        for substance in line["substances"]:
            by_substance.setdefault(substance, []).append(line)
    alerts = []
    for substance, concerned in sorted(by_substance.items()):
        if len(concerned) < 2:
            continue
        names = ", ".join(line["name"] for line in concerned)
        alerts.append({
            "id": _alert_id("same_substance", None, substance, concerned),
            "type": "same_substance",
            "level": None,
            "requirement": "justify",
            "line_ids": [line["line_id"] for line in concerned],
            "message": f"{substance.capitalize()} prescrit sur plusieurs lignes : {names}",
            "details": {"substances": [substance]},
        })
    return alerts


def _allergy_alerts(lines: list[dict[str, Any]], patient: dict[str, Any]) -> list[dict[str, Any]]:
    allergies = [normalize_dci(a) for a in patient.get("allergies") or [] if normalize_dci(a)]
    alerts = []
    for allergy in allergies:
        concerned = [line for line in lines if any(_contains_dci(s, allergy) for s in line["substances"])]
        for line in concerned:
            alerts.append({
                "id": _alert_id("allergy", None, allergy, [line]),
                "type": "allergy",
                "level": None,
                "requirement": "justify",
                "line_ids": [line["line_id"]],
                "message": f"Allergie déclarée à {allergy.capitalize()} : {line['name']}",
                "details": {"substances": [allergy]},
            })
    return alerts


def _contains_dci(substance: str, allergy: str) -> bool:
    """AMOXICILLINE matches AMOXICILLINE and AMOXICILLINE TRIHYDRATEE, not CLAMOXYL."""
    return substance == allergy or re.search(rf"(^| ){re.escape(allergy)}( |$)", substance) is not None


def level_from_niveau(niveau: str | None) -> str | None:
    value = normalize_dci(niveau)
    if "CONTRE" in value or re.search(r"(^|[^A-Z])CI([^A-Z]|$)", value):
        return "CI"
    if "DECONSEIL" in value or "ASDEC" in value:
        return "ASDEC"
    if "PRECAUTION" in value or re.search(r"(^|[^A-Z])PE([^A-Z]|$)", value):
        return "PE"
    if "PRENDRE EN COMPTE" in value or "APEC" in value:
        return "APEC"
    return None
