"""AI summary service using Groq API (free tier)."""
import os
import logging
import requests as http

logger = logging.getLogger(__name__)

_GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
_GROQ_MODEL = 'llama-3.1-8b-instant'


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
        f"Tu es un pharmacien expert. Rédige un résumé clinique clair et concis (3-4 phrases) "
        f"de l'interaction médicamenteuse entre {med1} et {med2} pour un professionnel de santé.\n\n"
        f"Données d'interaction :\n" + "\n".join(lines) + "\n\n"
        "Consignes :\n"
        "- Commence par le niveau de gravité le plus élevé\n"
        "- Mentionne le mécanisme pharmacologique principal si pertinent\n"
        "- Indique la conduite à tenir principale\n"
        "- Réponds uniquement en français, de manière factuelle et concise, sans introduction"
    )

    try:
        resp = http.post(
            _GROQ_URL,
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': _GROQ_MODEL,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 300,
                'temperature': 0.2,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except Exception:
        logger.exception("Groq summary failed for %s / %s", med1, med2)
        return None
