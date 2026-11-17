"""Tests for the Groq interaction summary."""
from unittest.mock import MagicMock, patch

from app.services.summary import generate_interaction_summary

INTERACTION = [{'niveau': "PRÉCAUTION D'EMPLOI", 'class_1': 'AMIODARONE', 'class_2': 'SIMVASTATINE',
                'risques': 'Rhabdomyolyse', 'actions': 'Ne pas dépasser 20 mg/j'}]


def test_no_key_no_call(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    with patch('app.services.summary.http.post') as post:
        assert generate_interaction_summary('A', 'B', INTERACTION) is None
    post.assert_not_called()


def test_uses_an_available_model_and_returns_the_text(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.delenv('GROQ_MODEL', raising=False)
    response = MagicMock()
    response.json.return_value = {'choices': [{'message': {'content': ' Risque de rhabdomyolyse. '}}]}
    with patch('app.services.summary.http.post', return_value=response) as post:
        assert generate_interaction_summary('AMIODARONE', 'SIMVASTATINE', INTERACTION) == 'Risque de rhabdomyolyse.'
    body = post.call_args.kwargs['json']
    assert body['model'] == 'openai/gpt-oss-20b'
    assert body['reasoning_effort'] == 'low'


def test_model_can_be_overridden(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('GROQ_MODEL', 'qwen/qwen3.8-27b')
    with patch('app.services.summary.http.post') as post:
        generate_interaction_summary('A', 'B', INTERACTION)
    assert post.call_args.kwargs['json']['model'] == 'qwen/qwen3.8-27b'


def test_prompt_never_softens_a_contraindication(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    with patch('app.services.summary.http.post') as post:
        generate_interaction_summary('MICONAZOLE', 'WARFARINE', [{**INTERACTION[0], 'niveau': 'CONTRE-INDICATION'}])
    prompt = post.call_args.kwargs['json']['messages'][0]['content']
    assert 'contre-indiquée' in prompt
