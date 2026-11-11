"""Patient module: data rules and wiring. Storage is covered in tests/integration."""
from unittest.mock import patch

import pytest

from app import create_app
from app.config import DevelopmentConfig
from app.services.patient import PatientError, normalize_patient


PRESCRIBER = {'id': 7, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}


class TestNormalizePatient:
    def test_accepts_french_dates_and_decimal_commas(self):
        record = normalize_patient({'birthdate': '02/04/2019', 'weight_kg': '18,5', 'weighed_on': '2026-10-01'})
        assert record['birthdate'] == '2019-04-02'
        assert record['weighed_on'] == '2026-10-01'
        assert record['weight_kg'] == 18.5

    def test_allergies_are_uppercased_and_deduplicated(self):
        record = normalize_patient({'allergies': 'amoxicilline; Amoxicilline, ibuprofène'})
        assert record['allergies'] == ['AMOXICILLINE', 'IBUPROFÈNE']

    @pytest.mark.parametrize('payload', [
        {'birthdate': '31/02/2019'},
        {'weight_kg': 'lourd'},
        {'weight_kg': '0'},
        {'sex': 'X'},
        {'pregnancy': 'peut-être'},
    ])
    def test_unreadable_data_is_refused_with_a_message(self, payload):
        with pytest.raises(PatientError):
            normalize_patient(payload)

    def test_partial_patient_is_accepted(self):
        record = normalize_patient({'last_name': 'Koffi'})
        assert record['last_name'] == 'Koffi'
        assert record['sex'] is None and record['birthdate'] is None


class TestPatientApiAccess:
    def test_one_letter_search_returns_nothing(self, client):
        with patch('app.api.routes.AuthService.current_user', return_value=PRESCRIBER), \
             patch('app.api.routes.PatientService.search') as search:
            response = client.get('/api/v1/patients?q=k')
        assert response.get_json() == {'success': True, 'results': []}
        search.assert_not_called()

    def test_only_prescribers_reach_patients(self, client):
        admin = {**PRESCRIBER, 'role': 'admin'}
        with patch('app.api.routes.AuthService.current_user', return_value=admin), \
             patch('app.api.routes.PatientService.create') as create:
            response = client.post('/api/v1/patients', json={'last_name': 'Koffi'})
        assert response.status_code == 403
        create.assert_not_called()


class TestStartup:
    def test_startup_prepares_schema_then_copies_patient_history(self):
        with patch('app.services.database.DatabasePool.initialize'), \
             patch('app.AuthService.ensure_schema'), \
             patch('app.PatientService.ensure_schema'), \
             patch('app.SchemaMigrator.apply_pending') as migrate, \
             patch('app.PatientService.migrate_legacy_history') as copy_history, \
             patch.dict('os.environ', {'ADMIN_EMAIL': '', 'ADMIN_PASSWORD': ''}):
            create_app(DevelopmentConfig())

        migrate.assert_called_once()
        copy_history.assert_called_once()

    def test_auth_schema_no_longer_touches_patients(self):
        from unittest.mock import MagicMock

        from app.services.auth import AuthService

        cursor = MagicMock()
        with patch('app.services.auth.DatabasePool') as db:
            db.get_cursor.return_value.__enter__.return_value = cursor
            AuthService.ensure_schema()
        executed = ' '.join(str(call.args[0]) for call in cursor.execute.call_args_list)
        assert 'patient' not in executed.lower()
