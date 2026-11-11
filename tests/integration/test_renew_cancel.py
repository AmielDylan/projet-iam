"""Renewing and cancelling issued ordonnances."""
from unittest.mock import patch

import pytest

from app.services.database import DatabasePool
from app.services.ordonnance import (
    CANCEL_REASONS, InvalidContent, NeedsConfirmation, NotEditable, OrdonnanceService,
)
from tests.integration.test_issue import ready_draft

CATALOG = {7: {'id': 7, 'name': 'ADVIL', 'substances': ['IBUPROFENE']},
           5: {'id': 5, 'name': 'COUMADINE', 'substances': ['WARFARINE']}}
ASDEC = [{'class_1': 'AINS', 'class_2': 'AVK', 'niveau': 'Association déconseillée',
          'risques': '', 'details': '', 'actions': ''}]
LINES = [{'line_id': 'a', 'medication_id': 7, 'name': 'Advil', 'posology': '1/j', 'quantity': '1 boîte'},
         {'line_id': 'b', 'medication_id': 5, 'name': 'Coumadine', 'posology': '1/j'}]


def issued_with_derogation(owner):
    with patch('app.services.analysis.MedicationCatalogService.get', side_effect=CATALOG.get), \
         patch('app.services.ordonnance.MedicationCatalogService.get', side_effect=CATALOG.get), \
         patch('app.services.analysis.InteractionService.get_interactions', return_value=ASDEC):
        draft = ready_draft(owner, lines=LINES)
        alert_id = OrdonnanceService.check(owner, draft['id'])['reasons'][0]['alert_id']
        content = {**draft['content'], 'lab_results': 'Créatinine 9 mg/L', 'derogations': {alert_id: 'INR suivi'}}
        saved = OrdonnanceService.save_draft(owner, draft['id'], content, version=draft['version'])
        return OrdonnanceService.issue(owner, draft['id'], version=saved['version'])


class TestRenew:
    def test_renewal_prefills_lines_and_establishment_without_derogations(self, prescriber):
        source = issued_with_derogation(prescriber)
        with patch('app.services.ordonnance.MedicationCatalogService.get', side_effect=CATALOG.get):
            renewal = OrdonnanceService.renew(prescriber, source['id'])

        draft = renewal['ordonnance']
        assert draft['status'] == 'draft' and draft['origin_id'] == source['id']
        assert draft['patient_id'] == source['patient_id']
        assert draft['content']['establishment_id'] == source['establishment_id']
        assert [(l['name'], l['posology'], l['quantity']) for l in draft['content']['lines']] == \
            [('Advil', '1/j', '1 boîte'), ('Coumadine', '1/j', '')]
        assert draft['content']['derogations'] == {}
        assert draft['content']['lab_results'] == ''
        assert renewal['notices'] == []

    def test_line_whose_catalog_entry_disappeared_becomes_free_text_and_is_signalled(self, prescriber):
        source = issued_with_derogation(prescriber)
        with patch('app.services.ordonnance.MedicationCatalogService.get', side_effect={7: CATALOG[7]}.get):
            renewal = OrdonnanceService.renew(prescriber, source['id'])

        coumadine = renewal['ordonnance']['content']['lines'][1]
        assert coumadine['medication_id'] is None and coumadine['is_free_text'] is True
        assert renewal['notices'] == [{'line_id': 'b', 'code': 'catalog_missing',
                                       'message': "Coumadine n'est plus au catalogue : la ligne passe en saisie libre."}]

    def test_a_draft_cannot_be_renewed(self, prescriber):
        draft = ready_draft(prescriber)
        with pytest.raises(NotEditable):
            OrdonnanceService.renew(prescriber, draft['id'])


class TestCancel:
    def test_cancel_needs_a_reason_and_keeps_date_and_reason(self, prescriber):
        draft = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])

        with pytest.raises(InvalidContent):
            OrdonnanceService.cancel(prescriber, issued['id'], '   ')
        cancelled = OrdonnanceService.cancel(prescriber, issued['id'], 'Erreur de posologie')

        assert cancelled['status'] == 'cancelled'
        assert cancelled['cancel_reason'] == 'Erreur de posologie'
        assert cancelled['cancelled_at']
        assert cancelled['snapshot']['number'] == issued['number']
        stored = DatabasePool.execute_query('SELECT cancel_reason FROM ordonnances WHERE id = %s', (issued['id'],))[0][0]
        assert 'posologie' not in stored

    def test_only_issued_ordonnances_can_be_cancelled_and_only_once(self, prescriber):
        draft = ready_draft(prescriber)
        with pytest.raises(NotEditable):
            OrdonnanceService.cancel(prescriber, draft['id'], 'Erreur')
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        OrdonnanceService.cancel(prescriber, issued['id'], 'Erreur')
        with pytest.raises(NotEditable):
            OrdonnanceService.cancel(prescriber, issued['id'], 'Encore')

    def test_renewing_a_cancelled_ordonnance_needs_confirmation(self, prescriber):
        draft = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        OrdonnanceService.cancel(prescriber, issued['id'], 'Erreur')

        with pytest.raises(NeedsConfirmation):
            OrdonnanceService.renew(prescriber, issued['id'])
        assert OrdonnanceService.renew(prescriber, issued['id'], confirm_cancelled=True)['ordonnance']['status'] == 'draft'

    def test_cancel_and_correct_chains_both(self, prescriber):
        draft = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])

        result = OrdonnanceService.cancel_and_correct(prescriber, issued['id'], CANCEL_REASONS[0])

        assert result['cancelled']['status'] == 'cancelled'
        assert result['ordonnance']['origin_id'] == issued['id']
        assert 'Impression ratée' in CANCEL_REASONS


class TestRenewCancelApi:
    def test_endpoints(self, client, prescriber):
        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        draft = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        with patch('app.api.routes.AuthService.current_user', return_value=user):
            reasons = client.get('/api/v1/ordonnances/cancel-reasons').get_json()['reasons']
            renewed = client.post(f"/api/v1/ordonnances/{issued['id']}/renew", json={})
            corrected = client.post(f"/api/v1/ordonnances/{issued['id']}/cancel-and-correct", json={'reason': reasons[0]})
            again = client.post(f"/api/v1/ordonnances/{issued['id']}/renew", json={})

        assert renewed.status_code == 201
        assert corrected.status_code == 201
        assert corrected.get_json()['cancelled']['status'] == 'cancelled'
        assert again.status_code == 409 and again.get_json()['code'] == 'confirm_cancelled'
