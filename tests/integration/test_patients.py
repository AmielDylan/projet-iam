"""Patients: stable identity, encrypted record, blind search, isolation."""
from unittest.mock import patch

from app.services.database import DatabasePool
from app.services.patient import PatientService
from app.services.schema import SchemaMigrator


AWA = {
    'first_name': 'Awa', 'last_name': 'Koffi', 'birthdate': '02/04/2019',
    'sex': 'F', 'weight_kg': '18,5', 'weighed_on': '2026-10-01',
    'allergies': ['amoxicilline', ' Amoxicilline '], 'address': 'Cotonou',
}


def raw_record(patient_id):
    return DatabasePool.execute_query('SELECT record FROM patients WHERE id = %s', (patient_id,))[0][0]


class TestPatientRecord:
    def test_create_then_get_returns_normalized_data(self, prescriber):
        created = PatientService.create(prescriber, AWA)
        patient = PatientService.get(prescriber, created['id'])

        assert patient['last_name'] == 'Koffi'
        assert patient['birthdate'] == '2019-04-02'
        assert patient['weight_kg'] == 18.5
        assert patient['allergies'] == ['AMOXICILLINE']

    def test_record_is_encrypted_in_the_database(self, prescriber):
        created = PatientService.create(prescriber, AWA)
        stored = raw_record(created['id'])
        assert 'Koffi' not in stored and 'KOFFI' not in stored and '2019' not in stored

    def test_renaming_keeps_the_same_patient(self, prescriber):
        created = PatientService.create(prescriber, AWA)
        updated = PatientService.update(prescriber, created['id'], {**AWA, 'last_name': 'Koffy'})

        assert updated['id'] == created['id']
        assert [p['id'] for p in PatientService.search(prescriber, 'koffy')] == [created['id']]
        assert PatientService.search(prescriber, 'koffi') == []


class TestPatientSearch:
    def test_finds_by_name_prefix_and_by_several_words(self, prescriber):
        created = PatientService.create(prescriber, AWA)
        PatientService.create(prescriber, {'first_name': 'Awa', 'last_name': 'Mensah'})

        assert [p['id'] for p in PatientService.search(prescriber, 'kof')] == [created['id']]
        assert [p['id'] for p in PatientService.search(prescriber, 'awa ko')] == [created['id']]
        assert len(PatientService.search(prescriber, 'awa')) == 2

    def test_finds_by_birthdate_in_both_formats(self, prescriber):
        created = PatientService.create(prescriber, AWA)
        assert [p['id'] for p in PatientService.search(prescriber, '02/04/2019')] == [created['id']]
        assert [p['id'] for p in PatientService.search(prescriber, '2019-04-02')] == [created['id']]

    def test_never_finds_another_prescribers_patient(self, prescriber, other_prescriber):
        created = PatientService.create(prescriber, AWA)

        assert PatientService.search(other_prescriber, 'koffi') == []
        assert PatientService.get(other_prescriber, created['id']) is None
        assert PatientService.update(other_prescriber, created['id'], {'last_name': 'X'}) is None


class TestLegacyHistory:
    def test_history_is_migrated_once_without_loss(self, prescriber):
        with DatabasePool.get_cursor() as cursor:
            for first, last in (('Awa', 'Koffi'), ('Kossi', 'Agbo')):
                cursor.execute(
                    "INSERT INTO patient_history (user_id, patient_key, patient_first_name, patient_last_name, "
                    "patient_birthdate, patient_weight) VALUES (%s, SHA2(%s, 256), %s, %s, '2019-04-02', 18.50)",
                    (prescriber, first + last, first, last),
                )

        assert PatientService.migrate_legacy_history() == 2
        assert PatientService.migrate_legacy_history() == 0

        found = PatientService.search(prescriber, 'agbo')
        assert len(found) == 1
        assert found[0]['birthdate'] == '2019-04-02'
        assert found[0]['weight_kg'] == 18.5


class TestStartupIsRepeatable:
    def test_a_second_start_changes_nothing(self, db):
        from app.services.auth import AuthService

        AuthService.ensure_schema()
        PatientService.ensure_schema()
        assert SchemaMigrator.apply_pending() == []


class TestPatientApi:
    def test_create_search_and_update_through_the_api(self, client, prescriber):
        user = {'id': prescriber, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}
        with patch('app.api.routes.AuthService.current_user', return_value=user):
            created = client.post('/api/v1/patients', json=AWA).get_json()['patient']
            found = client.get('/api/v1/patients?q=kof').get_json()['results']
            renamed = client.put(f"/api/v1/patients/{created['id']}", json={**AWA, 'last_name': 'Koffy'})
            missing = client.get('/api/v1/patients/999999')
            invalid = client.post('/api/v1/patients', json={**AWA, 'birthdate': '31/02/2019'})

        assert [p['id'] for p in found] == [created['id']]
        assert renamed.get_json()['patient']['last_name'] == 'Koffy'
        assert missing.status_code == 404
        assert invalid.status_code == 400
