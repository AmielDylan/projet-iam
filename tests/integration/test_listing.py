"""Listing ordonnances: filters, pagination, patient history, deleting drafts."""
from unittest.mock import patch

import pytest

from app.services.ordonnance import NotEditable, NotFound, OrdonnanceService
from app.services.patient import PatientService
from tests.integration.test_issue import ready_draft


def ids(page):
    return [item['id'] for item in page['items']]


class TestList:
    def test_most_recent_first_with_status_and_patient_filters(self, prescriber):
        first = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, first['id'], version=first['version'])
        draft = ready_draft(prescriber)
        empty = OrdonnanceService.create_draft(prescriber)

        everything = OrdonnanceService.list(prescriber)
        assert ids(everything) == [empty['id'], draft['id'], issued['id']]
        assert ids(OrdonnanceService.list(prescriber, status='issued')) == [issued['id']]
        assert ids(OrdonnanceService.list(prescriber, patient_id=draft['patient_id'])) == [draft['id']]

        summary = next(item for item in everything['items'] if item['id'] == issued['id'])
        assert summary['number'] == issued['number']
        assert summary['patient']['last_name'] == 'Koffi'
        assert summary['medications'] == ['Tisane de kinkéliba']

    def test_pages_of_fifty(self, prescriber):
        for _ in range(53):
            OrdonnanceService.create_draft(prescriber)
        first = OrdonnanceService.list(prescriber, page=1)
        second = OrdonnanceService.list(prescriber, page=2)
        assert (first['total'], first['pages'], len(first['items']), len(second['items'])) == (53, 2, 50, 3)
        assert not set(ids(first)) & set(ids(second))

    def test_never_lists_another_prescribers_ordonnances(self, prescriber, other_prescriber):
        OrdonnanceService.create_draft(prescriber)
        assert OrdonnanceService.list(other_prescriber)['items'] == []

    def test_unknown_status_filter_is_refused(self, prescriber):
        with pytest.raises(ValueError):
            OrdonnanceService.list(prescriber, status='everything')


class TestDiscardDraft:
    def test_a_draft_can_be_deleted_an_issued_ordonnance_never(self, prescriber):
        draft = ready_draft(prescriber)
        to_issue = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, to_issue['id'], version=to_issue['version'])

        OrdonnanceService.discard_draft(prescriber, draft['id'])
        assert OrdonnanceService.get(prescriber, draft['id']) is None
        assert draft['id'] not in ids(OrdonnanceService.list(prescriber))
        with pytest.raises(NotEditable):
            OrdonnanceService.discard_draft(prescriber, issued['id'])

    def test_another_prescriber_cannot_delete(self, prescriber, other_prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        with pytest.raises(NotFound):
            OrdonnanceService.discard_draft(other_prescriber, draft['id'])


class TestListApi:
    def test_list_patient_history_and_delete(self, client, prescriber):
        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        draft = ready_draft(prescriber)
        with patch('app.api.routes.AuthService.current_user', return_value=user):
            listing = client.get('/api/v1/ordonnances?status=draft').get_json()
            history = client.get(f"/api/v1/patients/{draft['patient_id']}/ordonnances").get_json()
            bad = client.get('/api/v1/ordonnances?status=nope')
            deleted = client.delete(f"/api/v1/ordonnances/{draft['id']}")
            after = client.get('/api/v1/ordonnances').get_json()

        assert [item['id'] for item in listing['items']] == [draft['id']]
        assert history['patient']['last_name'] == 'Koffi'
        assert [item['id'] for item in history['items']] == [draft['id']]
        assert bad.status_code == 400
        assert deleted.status_code == 200
        assert after['items'] == [] and after['total'] == 0


class TestNewOrdonnancePage:
    def test_new_reuses_an_untouched_empty_draft_and_prefills_a_patient(self, client, prescriber):
        from app.services.patient import PatientService

        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0, 'profession': 'Médecin'}
        patient = PatientService.create(prescriber, {'last_name': 'Koffi'})
        with patch('app.services.auth.AuthService.current_user', return_value=user):
            first = client.get('/ordonnances/nouvelle').headers['Location']
            second = client.get('/ordonnances/nouvelle').headers['Location']
            for_patient = client.get(f"/ordonnances/nouvelle?patient={patient['id']}").headers['Location']
            page = client.get(first)

        assert first == second
        assert for_patient != first and 'etape=2' in for_patient
        assert page.status_code == 200 and 'initial-data' in page.get_data(as_text=True)
