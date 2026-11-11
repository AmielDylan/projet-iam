"""Patient module: search and save a prescriber's patients."""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app import create_app
from app.config import DevelopmentConfig
from app.services.patient import PatientService


PRESCRIBER = {
    'id': 7,
    'role': 'prescriber',
    'status': 'approved',
    'must_change_password': 0,
}


def mock_cursor(db):
    """Return the cursor yielded by DatabasePool.get_cursor()."""
    cursor = MagicMock()
    db.get_cursor.return_value.__enter__.return_value = cursor
    return cursor


def executed_sql(cursor):
    return ' '.join(str(call.args[0]) for call in cursor.execute.call_args_list)


class TestPatientSearch:
    def test_blank_query_returns_nothing_without_querying(self):
        with patch('app.services.patient.DatabasePool') as db:
            assert PatientService.search(7, '   ') == []
            db.execute_query.assert_not_called()

    def test_search_is_scoped_to_the_prescriber(self):
        with patch('app.services.patient.DatabasePool') as db:
            db.execute_query.return_value = [{'id': 1, 'patient_last_name': 'KOFFI'}]

            results = PatientService.search(7, 'kof')

            assert results == [{'id': 1, 'patient_last_name': 'KOFFI'}]
            sql, params = db.execute_query.call_args.args[:2]
            assert 'FROM patient_history' in sql
            assert params[0] == 7
            assert '%kof%' in params

    def test_api_search_serializes_dates_and_weight(self, client):
        with patch('app.api.routes.AuthService.current_user', return_value=PRESCRIBER), \
             patch('app.services.patient.DatabasePool') as db:
            db.execute_query.return_value = [{
                'id': 1,
                'patient_last_name': 'KOFFI',
                'patient_birthdate': date(2019, 4, 2),
                'patient_weight': Decimal('18.50'),
                'last_seen_at': datetime(2026, 11, 10, 9, 30),
            }]

            response = client.get('/api/v1/patients/search?q=kof')

        assert response.status_code == 200
        result = response.get_json()['results'][0]
        assert result['patient_birthdate'] == '2019-04-02'
        assert result['patient_weight'] == 18.5
        assert result['last_seen_at'] == '2026-11-10T09:30:00'

    def test_api_search_ignores_one_letter_queries(self, client):
        with patch('app.api.routes.AuthService.current_user', return_value=PRESCRIBER), \
             patch('app.services.patient.DatabasePool') as db:
            response = client.get('/api/v1/patients/search?q=k')

        assert response.get_json() == {'success': True, 'results': []}
        db.execute_query.assert_not_called()


class TestPatientSave:
    def test_same_identity_gives_same_key_whatever_the_case(self):
        with patch('app.services.patient.DatabasePool') as db:
            mock_cursor(db)
            first = PatientService.save(7, {
                'patient_first_name': 'Awa', 'patient_last_name': 'Koffi',
                'patient_birthdate': '2019-04-02',
            })
            second = PatientService.save(7, {
                'patient_first_name': ' AWA ', 'patient_last_name': 'koffi',
                'patient_birthdate': '2019-04-02',
            })

        assert first['patient_key'] == second['patient_key']
        assert len(first['patient_key']) == 64

    def test_save_upserts_into_the_prescriber_history(self):
        with patch('app.services.patient.DatabasePool') as db:
            cursor = mock_cursor(db)
            PatientService.save(7, {
                'patient_last_name': 'Koffi', 'patient_weight': '18,5',
            })

        sql, params = cursor.execute.call_args.args
        assert 'INSERT INTO patient_history' in sql
        assert 'ON DUPLICATE KEY UPDATE' in sql
        assert params[0] == 7
        assert params[6] is None  # unreadable weight is dropped, not stored

    def test_api_save_returns_the_saved_patient(self, client):
        with patch('app.api.routes.AuthService.current_user', return_value=PRESCRIBER), \
             patch('app.services.patient.DatabasePool') as db:
            mock_cursor(db)
            response = client.post('/api/v1/patients', json={
                'patient_first_name': 'Awa', 'patient_last_name': 'Koffi',
            })

        body = response.get_json()
        assert body['success'] is True
        assert body['patient']['patient_last_name'] == 'Koffi'
        assert 'patient_key' in body['patient']

    def test_api_save_requires_a_prescriber(self, client):
        admin = {**PRESCRIBER, 'role': 'admin'}
        with patch('app.api.routes.AuthService.current_user', return_value=admin), \
             patch('app.services.patient.DatabasePool') as db:
            response = client.post('/api/v1/patients', json={'patient_last_name': 'Koffi'})

        assert response.status_code == 403
        db.get_cursor.assert_not_called()


class TestPatientSchema:
    def test_patient_module_creates_the_history_table(self):
        with patch('app.services.patient.DatabasePool') as db:
            cursor = mock_cursor(db)
            PatientService.ensure_schema()

        assert 'CREATE TABLE IF NOT EXISTS `patient_history`' in executed_sql(cursor)

    def test_auth_schema_no_longer_touches_patients(self):
        from app.services.auth import AuthService

        with patch('app.services.auth.DatabasePool') as db:
            cursor = mock_cursor(db)
            AuthService.ensure_schema()

        assert 'patient' not in executed_sql(cursor).lower()

    def test_app_startup_prepares_the_patient_schema(self):
        with patch('app.services.database.DatabasePool.initialize'), \
             patch('app.AuthService.ensure_schema'), \
             patch('app.PatientService.ensure_schema') as patient_schema, \
             patch.dict('os.environ', {'ADMIN_EMAIL': '', 'ADMIN_PASSWORD': ''}):
            create_app(DevelopmentConfig())

        patient_schema.assert_called_once()
