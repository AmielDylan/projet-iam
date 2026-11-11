"""Issuing: refusals, numbering, frozen snapshot, print view."""
import re
from unittest.mock import patch

import pytest

from app.services.auth import EstablishmentService
from app.services.database import DatabasePool
from app.services.ordonnance import IssueRefused, NotEditable, OrdonnanceService, VersionConflict, local_today
from app.services.patient import PatientService
from app.services.prescriber_code import ALPHABET, PrescriberCodes
from app.services.referential import ReferentialService


ADULT = {'first_name': 'Awa', 'last_name': 'Koffi', 'birthdate': '1980-05-01', 'sex': 'F'}


def establishment(owner, name='Clinique du Lac'):
    ok, _, item = EstablishmentService.upsert(owner, {'name': name, 'address': 'Cotonou'})
    assert ok
    return item


def ready_draft(owner, patient=ADULT, lines=None):
    patient_id = PatientService.create(owner, patient)['id']
    draft = OrdonnanceService.create_draft(owner)
    content = {
        'patient_id': patient_id,
        'establishment_id': establishment(owner)['id'],
        'general_note': 'Revoir dans 10 jours',
        'lines': lines if lines is not None else [
            {'line_id': 'l1', 'name': 'Tisane de kinkéliba', 'posology': '1 tasse le soir', 'quantity': '1 sachet'},
        ],
    }
    return OrdonnanceService.save_draft(owner, draft['id'], content, version=1)


def reason_codes(exc):
    return [reason['code'] for reason in exc.value.reasons]


class TestRefusals:
    def test_empty_draft_lists_every_missing_piece(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        with pytest.raises(IssueRefused) as refused:
            OrdonnanceService.issue(prescriber, draft['id'], version=1)
        assert {'patient_missing', 'establishment_missing', 'no_lines'} <= set(reason_codes(refused))

    def test_line_without_posology_is_refused(self, prescriber):
        draft = ready_draft(prescriber, lines=[{'line_id': 'l1', 'name': 'Doliprane'}])
        with pytest.raises(IssueRefused) as refused:
            OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        assert reason_codes(refused) == ['posology_missing']
        assert refused.value.reasons[0]['line_ids'] == ['l1']

    def test_child_needs_a_dated_weight_and_stale_weight_only_warns(self, prescriber):
        child = {'last_name': 'Agbo', 'birthdate': '2022-01-10', 'sex': 'M'}
        draft = ready_draft(prescriber, patient=child)
        with pytest.raises(IssueRefused) as refused:
            OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        assert reason_codes(refused) == ['weight_missing']

        PatientService.update(prescriber, draft['patient_id'], {**child, 'weight_kg': '14', 'weighed_on': '2025-01-01'})
        check = OrdonnanceService.check(prescriber, draft['id'])
        assert check['can_issue'] is True
        assert [w['code'] for w in check['warnings']] == ['weight_stale']

    def test_sex_is_required(self, prescriber):
        draft = ready_draft(prescriber, patient={'last_name': 'Koffi', 'birthdate': '1980-05-01'})
        with pytest.raises(IssueRefused) as refused:
            OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        assert reason_codes(refused) == ['sex_missing']

    def test_blocking_alert_is_a_reason(self, prescriber):
        catalog = {1: {'id': 1, 'name': 'KARDEGIC', 'substances': ['ACIDE ACETYLSALICYLIQUE']},
                   2: {'id': 2, 'name': 'COUMADINE', 'substances': ['WARFARINE']}}
        ci = [{'class_1': 'A', 'class_2': 'B', 'niveau': 'Contre-indication', 'risques': '', 'details': '', 'actions': ''}]
        lines = [{'line_id': 'a', 'medication_id': 1, 'name': 'Kardegic', 'posology': '1/j'},
                 {'line_id': 'b', 'medication_id': 2, 'name': 'Coumadine', 'posology': '1/j'}]
        with patch('app.services.analysis.MedicationCatalogService.get', side_effect=catalog.get), \
             patch('app.services.ordonnance.MedicationCatalogService.get', side_effect=catalog.get), \
             patch('app.services.analysis.InteractionService.get_interactions', return_value=ci):
            draft = ready_draft(prescriber, lines=lines)
            with pytest.raises(IssueRefused) as refused:
                OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        assert reason_codes(refused) == ['alert_blocking']
        assert refused.value.reasons[0]['line_ids'] == ['a', 'b']


class TestIssuing:
    def test_issue_numbers_freezes_and_locks_the_ordonnance(self, prescriber):
        ReferentialService.record('thesaurus', 'Thésaurus ANSM septembre 2026', '2026-09-01')
        draft = ready_draft(prescriber)

        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])

        code = PrescriberCodes.of(prescriber)
        assert issued['status'] == 'issued'
        assert issued['number'] == f'{code}-{local_today().year}-000001'
        snapshot = issued['snapshot']
        assert snapshot['patient']['last_name'] == 'Koffi'
        assert snapshot['establishment']['name'] == 'Clinique du Lac'
        assert snapshot['establishment']['paper_format'] == 'A5'
        assert snapshot['prescriber']['prescriber_code'] == code
        assert snapshot['lines'][0]['name'] == 'Tisane de kinkéliba'
        assert snapshot['referentials']['thesaurus']['label'] == 'Thésaurus ANSM septembre 2026'
        assert snapshot['analysis']['scope']['free_text_lines'] == ['Tisane de kinkéliba']

        with pytest.raises(NotEditable):
            OrdonnanceService.save_draft(prescriber, draft['id'], {'lines': []}, version=issued['version'])

    def test_issuing_twice_returns_the_same_ordonnance(self, prescriber):
        draft = ready_draft(prescriber)
        first = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        second = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        assert second['number'] == first['number']

    def test_issue_refuses_a_version_the_prescriber_did_not_review(self, prescriber):
        draft = ready_draft(prescriber)
        with pytest.raises(VersionConflict):
            OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'] - 1)

    def test_numbers_follow_each_prescribers_own_sequence(self, prescriber, other_prescriber):
        numbers = [OrdonnanceService.issue(owner, d['id'], version=d['version'])['number']
                   for owner, d in ((prescriber, ready_draft(prescriber)),
                                    (prescriber, ready_draft(prescriber)),
                                    (other_prescriber, ready_draft(other_prescriber)))]
        assert numbers[0].endswith('-000001') and numbers[1].endswith('-000002')
        assert numbers[2].endswith('-000001')
        assert numbers[2][:4] != numbers[0][:4]

    def test_later_profile_or_establishment_changes_do_not_alter_the_reprint(self, prescriber, client):
        draft = ready_draft(prescriber)
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        EstablishmentService.upsert(prescriber, {'name': 'Nouveau nom'}, establishment_id=draft['establishment_id'])
        PatientService.update(prescriber, draft['patient_id'], {**ADULT, 'last_name': 'Changé'})

        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        with patch('app.web.routes.AuthService.current_user', return_value=user):
            page = client.get(f"/ordonnances/{issued['id']}/impression").get_data(as_text=True)

        assert 'Clinique du Lac' in page and 'Nouveau nom' not in page
        assert 'Koffi' in page and 'Changé' not in page
        assert issued['number'] in page
        assert '<button' not in page and '<nav' not in page

    def test_print_view_is_404_for_another_prescriber_and_for_drafts(self, prescriber, other_prescriber, client):
        draft = ready_draft(prescriber)
        stranger = {'id': other_prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        owner = {**stranger, 'id': prescriber}
        with patch('app.web.routes.AuthService.current_user', return_value=owner):
            assert client.get(f"/ordonnances/{draft['id']}/impression").status_code == 404
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        with patch('app.web.routes.AuthService.current_user', return_value=stranger):
            assert client.get(f"/ordonnances/{issued['id']}/impression").status_code == 404


class TestPrescriberCodes:
    def test_codes_are_four_unambiguous_characters_given_retroactively(self, prescriber, other_prescriber):
        with DatabasePool.get_cursor() as cursor:
            cursor.execute('UPDATE iam_users SET prescriber_code = NULL')
        assert PrescriberCodes.ensure_all() == 2
        codes = {PrescriberCodes.of(prescriber), PrescriberCodes.of(other_prescriber)}
        assert len(codes) == 2
        for code in codes:
            assert re.fullmatch(f'[{ALPHABET}]{{4}}', code)
            assert not set(code) & set('O0I1L')


class TestIssueApi:
    def test_issue_endpoint_reports_reasons_then_issues(self, client, prescriber):
        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        empty = OrdonnanceService.create_draft(prescriber)
        draft = ready_draft(prescriber)
        with patch('app.api.routes.AuthService.current_user', return_value=user):
            refused = client.post(f"/api/v1/ordonnances/{empty['id']}/issue", json={'version': 1})
            check = client.get(f"/api/v1/ordonnances/{draft['id']}/check")
            issued = client.post(f"/api/v1/ordonnances/{draft['id']}/issue", json={'version': draft['version']})

        assert refused.status_code == 422
        assert refused.get_json()['code'] == 'issue_refused'
        assert check.get_json()['check']['can_issue'] is True
        assert issued.get_json()['ordonnance']['status'] == 'issued'


class TestPaperFormat:
    def test_establishment_in_a4_prints_in_a4(self, prescriber, client):
        draft = ready_draft(prescriber)
        EstablishmentService.upsert(prescriber, {'name': 'Clinique du Lac', 'paper_format': 'a4'},
                                    establishment_id=draft['establishment_id'])
        issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        with patch('app.web.routes.AuthService.current_user', return_value=user):
            page = client.get(f"/ordonnances/{issued['id']}/impression").get_data(as_text=True)
        assert issued['snapshot']['establishment']['paper_format'] == 'A4'
        assert 'size: A4' in page

    def test_unknown_paper_format_is_refused(self, prescriber):
        ok, message, _ = EstablishmentService.upsert(prescriber, {'name': 'X', 'paper_format': 'Letter'})
        assert not ok and 'A5 ou A4' in message
