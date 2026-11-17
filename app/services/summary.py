"""AI summary service using Groq API (free tier)."""
import os
import logging
import requests as http

logger = logging.getLogger(__name__)

_GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
# Groq retires models: llama-3.1-8b-instant disappeared in 2026. GROQ_MODEL overrides the default.
_GROQ_MODEL = 'openai/gpt-oss-20b'


def generate_interaction_summary(med1: str, med2: str, interactions: list) -> str | None:
    """
    Call Groq to produce a concise French clinical summary.
    Returns None when GROQ_API_KEY is missing or the call fails.
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None

    lines = []
    for it in interactions:
        niveau  = it.get('niveau', '')
        class_1 = it.get('class_1', '')
        class_2 = it.get('class_2', '')
        risques = (it.get('risques') or '')[:200]
        actions = (it.get('actions') or '')[:150]
        line = f"• {niveau} ({class_1} / {class_2})"
        if risques:
            line += f" — Risques : {risques}"
        if actions:
            line += f" — CAT : {actions}"
        lines.append(line)

    prompt = (
        f"Résume en 2 phrases simples et claires l'interaction entre {med1} et {med2}.\n"
        f"Données : {' | '.join(lines)}\n\n"
        "Règles strictes :\n"
        "- 2 phrases maximum, en français courant\n"
        "- Pas de titres, pas de tirets, pas de listes, pas de markdown\n"
        "- Commence directement par le risque principal\n"
        "- Termine par ce qu'il faut faire\n"
        "- Aucune introduction ni formule de politesse\n"
        "- Si un niveau est une CONTRE-INDICATION, écris que l'association est contre-indiquée "
        "et ne doit pas être prescrite ; ne propose jamais de la surveiller ou d'ajuster une dose à la place"
    )

    return _ask(prompt, f'{med1} / {med2}')



def _ask(prompt: str, about: str) -> str | None:
    """One Groq completion, or None when the key is missing or the call fails."""
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None
    try:
        resp = http.post(
            _GROQ_URL,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': os.environ.get('GROQ_MODEL') or _GROQ_MODEL,
                # gpt-oss reasons before answering: keep it short, and leave room for both.
                'reasoning_effort': 'low',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 400,
                'temperature': 0.1,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip() or None
    except Exception:
        logger.exception("Groq call failed for %s", about)
        return None


LEVEL_LABELS = {
    'CI': 'contre-indication',
    'ASDEC': 'association déconseillée',
    'PE': "précaution d'emploi",
    'APEC': 'à prendre en compte',
}
# Successful explanations only, so that a failure is retried; the analysis reruns at every keystroke.
_explanations: dict[tuple[str, ...], str] = {}
_MAX_CACHED = 2000


def explain_interaction(drug_1: str, drug_2: str, level: str, risks: str, conduct: str) -> str | None:
    """One plain-language sentence on an interaction alert of the ordonnance.

    Only drug names and thesaurus text are sent to Groq, never patient data.
    """
    key = (drug_1, drug_2, level, risks, conduct)
    if key in _explanations:
        return _explanations[key]
    level_label = LEVEL_LABELS.get(level, 'interaction')
    prompt = (
        f"Explique en une seule phrase courte, en français courant, l'interaction entre {drug_1} et {drug_2}.\n"
        f"Niveau ANSM : {level_label}.\n"
        f"Risques : {risks[:300] or 'non précisés'}\n"
        f"Conduite à tenir : {conduct[:300] or 'non précisée'}\n\n"
        "Règles strictes :\n"
        "- Une seule phrase, 30 mots maximum\n"
        "- Mots simples : remplace le jargon par ce qu'il veut dire (par exemple « saignements » pour « hémorragies »)\n"
        "- Dis le risque, puis ce qu'il faut faire\n"
        "- Pas de titre, pas de liste, pas de markdown, pas d'introduction\n"
        "- Si le niveau est une contre-indication, dis que l'association est contre-indiquée et ne doit pas être "
        "prescrite ; ne propose jamais de la surveiller ou d'ajuster une dose à la place"
    )
    text = _ask(prompt, f'{drug_1} / {drug_2}')
    if text:
        if len(_explanations) >= _MAX_CACHED:
            _explanations.clear()
        _explanations[key] = text
    return text
