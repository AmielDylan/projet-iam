"""Drafts: autosave with versions, conflicts, isolation, encryption."""
from unittest.mock import patch

import mysql.connector
import pytest

from app.services.database import DatabasePool
from app.services.ordonnance import (
    InvalidContent, NotFound, OrdonnanceService, VersionConflict,
)
from app.services.patient import PatientService


def content(**overrides):
    base = {
        'general_note': 'À prendre au cours du repas',
        'lab_results': 'Créatinine 9 mg/L',
        'lines': [
            {'line_id': 'l1', 'medication_id': 12, 'name': 'Doliprane', 'dosage': '500 mg',
             'posology': '1 comprimé 3 fois par jour', 'quantity': '1 boîte'},
            {'line_id': 'l2', 'name': 'Tisane maison', 'posology': 'le soir'},
        ],
    }
    base.update(overrides)
    return base


class TestDraftLifecycle:
    def test_new_draft_starts_empty_at_version_one(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        assert draft['status'] == 'draft'
        assert draft['version'] == 1
        assert draft['content']['lines'] == []

    def test_saving_bumps_the_version_and_reload_restores_everything(self, prescriber):
        patient = PatientService.create(prescriber, {'last_name': 'Koffi'})
        draft = OrdonnanceService.create_draft(prescriber)

        saved = OrdonnanceService.save_draft(prescriber, draft['id'], content(patient_id=patient['id']), version=1)
        reloaded = OrdonnanceService.get(prescriber, draft['id'])

        assert saved['version'] == 2
        assert reloaded['version'] == 2
        assert reloaded['patient_id'] == patient['id']
        assert reloaded['content']['general_note'] == 'À prendre au cours du repas'
        assert [line['name'] for line in reloaded['content']['lines']] == ['Doliprane', 'Tisane maison']
        assert reloaded['content']['lines'][1]['is_free_text'] is True
        assert reloaded['content']['lines'][0]['is_free_text'] is False

    def test_stale_version_is_refused_with_the_current_state(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        OrdonnanceService.save_draft(prescriber, draft['id'], content(general_note='onglet A'), version=1)

        with pytest.raises(VersionConflict) as conflict:
            OrdonnanceService.save_draft(prescriber, draft['id'], content(general_note='onglet B'), version=1)

        assert conflict.value.current['version'] == 2
        assert conflict.value.current['content']['general_note'] == 'onglet A'

    def test_resending_the_same_save_is_harmless(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        first = OrdonnanceService.save_draft(prescriber, draft['id'], content(), version=1)
        retry = OrdonnanceService.save_draft(prescriber, draft['id'], content(), version=1)

        assert retry['version'] == first['version'] == 2

    def test_every_save_keeps_an_immutable_dated_version(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        OrdonnanceService.save_draft(prescriber, draft['id'], content(general_note='v2'), version=1)
        OrdonnanceService.save_draft(prescriber, draft['id'], content(general_note='v3'), version=2)

        rows = DatabasePool.execute_query(
            'SELECT version, created_at FROM ordonnance_versions WHERE ordonnance_id = %s ORDER BY version',
            (draft['id'],),
        )
        assert [row[0] for row in rows] == [1, 2, 3]
        assert all(row[1] is not None for row in rows)

        for statement in ('UPDATE ordonnance_versions SET version = 9', 'DELETE FROM ordonnance_versions'):
            with pytest.raises(mysql.connector.Error):
                with DatabasePool.get_cursor() as cursor:
                    cursor.execute(statement)

    def test_content_and_versions_are_encrypted(self, prescriber):
        draft = OrdonnanceService.create_draft(prescriber)
        OrdonnanceService.save_draft(prescriber, draft['id'], content(), version=1)

        stored = DatabasePool.execute_query('SELECT content FROM ordonnances WHERE id = %s', (draft['id'],))[0][0]
        versions = DatabasePool.execute_query('SELECT content FROM ordonnance_versions')
        for text in [stored, *(row[0] for row in versions)]:
            assert 'Doliprane' not in text and 'Créatinine' not in text


class TestDraftIsolation:
    def test_another_prescriber_cannot_read_or_save(self, prescriber, other_prescriber):
        draft = OrdonnanceService.create_draft(prescriber)

        assert OrdonnanceService.get(other_prescriber, draft['id']) is None
        with pytest.raises(NotFound):
            OrdonnanceService.save_draft(other_prescriber, draft['id'], content(), version=1)

    def test_cannot_attach_another_prescribers_patient(self, prescriber, other_prescriber):
        stranger = PatientService.create(other_prescriber, {'last_name': 'Agbo'})
        draft = OrdonnanceService.create_draft(prescriber)

        with pytest.raises(InvalidContent):
            OrdonnanceService.save_draft(prescriber, draft['id'], content(patient_id=stranger['id']), version=1)


class TestDraftApi:
    def user(self, user_id):
        return {'id': user_id, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0,
                'profession': 'Médecin'}

    def test_autosave_round_trip_and_errors(self, client, prescriber, other_prescriber):
        with patch('app.api.routes.AuthService.current_user', return_value=self.user(prescriber)):
            created = client.post('/api/v1/ordonnances', json={})
            draft = created.get_json()['ordonnance']
            saved = client.put(f"/api/v1/ordonnances/{draft['id']}", json={'version': 1, 'content': content()})
            stale = client.put(f"/api/v1/ordonnances/{draft['id']}", json={'version': 1, 'content': content(general_note='x')})
            reloaded = client.get(f"/api/v1/ordonnances/{draft['id']}")

        with patch('app.api.routes.AuthService.current_user', return_value=self.user(other_prescriber)):
            foreign = client.get(f"/api/v1/ordonnances/{draft['id']}")

        assert created.status_code == 201
        assert saved.get_json()['ordonnance']['version'] == 2
        assert stale.status_code == 409
        assert stale.get_json()['code'] == 'version_conflict'
        assert stale.get_json()['current']['version'] == 2
        assert reloaded.get_json()['ordonnance']['content']['lines'][0]['name'] == 'Doliprane'
        assert foreign.status_code == 404
