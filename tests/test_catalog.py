"""Tests for medication catalog and prescription analysis."""
from unittest.mock import patch

from openpyxl import Workbook

from app.services.catalog import MedicationCatalogService
from scripts.import_medication_catalog import EXPECTED_COLUMNS, read_rows


class TestMedicationCatalogService:
    """Service tests for prescription catalog behavior."""

    def test_split_substances(self):
        assert MedicationCatalogService.split_substances('aspirine | warfarine | ') == ['aspirine', 'warfarine']


class TestMedicationCatalogApi:
    """API tests for the V3 medication catalog endpoints."""

    def test_search_medications(self, client):
        with patch('app.api.routes.MedicationCatalogService.search') as mock_search:
            mock_search.return_value = [{'id': 1, 'name': 'ASPIRINE'}]

            response = client.get('/api/v1/medications/search?q=aspirine')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['results'][0]['name'] == 'ASPIRINE'

    def test_get_medication_not_found(self, client):
        with patch('app.api.routes.MedicationCatalogService.get') as mock_get:
            mock_get.return_value = None

            response = client.get('/api/v1/medications/999')

        assert response.status_code == 404

    def test_analyze_prescription_endpoint(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.analyze') as mock_analyze:
            mock_user.return_value = {'id': 1, 'role': 'prescriber', 'status': 'approved'}
            mock_analyze.return_value = {'alerts': [], 'summary': {'can_issue': True}, 'scope': {}}

            response = client.post('/api/v1/prescriptions/analyze', json={'lines': [{'name': 'ASPIRINE'}]})

        assert response.status_code == 200
        assert response.get_json()['summary']['can_issue'] is True

    def test_analysis_failure_is_reported_not_hidden(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.analyze', side_effect=RuntimeError('db down')):
            mock_user.return_value = {'id': 1, 'role': 'prescriber', 'status': 'approved'}
            response = client.post('/api/v1/prescriptions/analyze', json={'lines': [{'name': 'ASPIRINE'}]})

        assert response.status_code == 503
        assert response.get_json()['code'] == 'analysis_unavailable'

    def test_analyze_prescription_rejects_invalid_items(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user:
            mock_user.return_value = {'id': 1, 'role': 'prescriber', 'status': 'approved'}
            response = client.post('/api/v1/prescriptions/analyze', json={'items': 'ASPIRINE'})

        assert response.status_code == 400

    def test_analyze_prescription_requires_login(self, client):
        response = client.post('/api/v1/prescriptions/analyze', json={'items': [{'name': 'ASPIRINE'}]})

        assert response.status_code == 401


class TestMedicationCatalogImport:
    """Import parser tests."""

    def test_read_rows_from_xlsx(self, tmp_path):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(EXPECTED_COLUMNS)
        sheet.append([
            'METHOTREXATE',
            '2,5MG',
            None,
            'COMPRIMÉ',
            None,
            None,
            30,
            1,
            'methotrexate',
            'METHOTREXATE 2,5MG COMPRIMÉ 30',
        ])
        path = tmp_path / 'catalog.xlsx'
        workbook.save(path)

        rows = read_rows(path)

        assert len(rows) == 1
        assert rows[0]['Nom_Medicament'] == 'METHOTREXATE'
        assert rows[0]['Quantite_Unites'] == 30.0
        assert rows[0]['source_hash']


class TestAllergyInSearch:
    def test_search_flags_a_declared_allergy_on_the_suggestion(self, client):
        prescriber = {'id': 3, 'role': 'prescriber', 'status': 'approved'}
        with patch('app.api.routes.MedicationCatalogService.search') as search, \
             patch('app.api.routes.AuthService.current_user', return_value=prescriber), \
             patch('app.api.routes.PatientService.get', return_value={'allergies': ['AMOXICILLINE']}) as get_patient:
            search.return_value = [
                {'id': 1, 'name': 'CLAMOXYL', 'substances': ['AMOXICILLINE TRIHYDRATÉE']},
                {'id': 2, 'name': 'DOLIPRANE', 'substances': ['PARACÉTAMOL']},
            ]
            results = client.get('/api/v1/medications/search?q=cla&patient_id=9').get_json()['results']

        get_patient.assert_called_once_with(3, 9)
        assert results[0]['allergy_warning'] == ['AMOXICILLINE']
        assert results[1]['allergy_warning'] == []


class TestProductLabels:
    """Results that name, dosage and form cannot tell apart carry their full product name."""

    @staticmethod
    def _item(name, dosage, form, specialite):
        return {'name': name, 'dosage': dosage, 'form': form, 'specialite': specialite}

    def test_twins_and_unreliable_forms_get_a_label(self):
        results = [
            self._item('DOLIPRANE', '1G', 'COMPRIMÉ', 'DOLIPRANE 1G CPR 8'),
            self._item('DOLIPRANE', '1G', 'COMPRIMÉ', 'DOLIPRANE 1G CPR EFF 8'),
            self._item('DOLIPRANE', '1G', '', 'DOLIPRANE 1G AD SUPPO 8'),
            self._item('DOLIPRANE', '1G', 'GEL', 'DOLIPRANE 1G GELULE 8'),
            self._item('DOLIPRANE', '500MG', 'COMPRIMÉ', 'DOLIPRANE 500MG CPR 16'),
        ]
        with patch('app.services.catalog.DatabasePool.execute_query',
                   return_value=[('DOLIPRANE', '1G', 'COMPRIMÉ')]) as query:
            MedicationCatalogService._add_labels(results)

        assert [r['label'] for r in results] == [
            'DOLIPRANE 1G CPR 8', 'DOLIPRANE 1G CPR EFF 8', 'DOLIPRANE 1G AD SUPPO 8', 'DOLIPRANE 1G GELULE 8', '']
        assert query.call_args[0][1] == ('DOLIPRANE',)

    def test_label_survives_line_normalization(self):
        from app.services.ordonnance import normalize_content

        content = normalize_content({'lines': [{'medication_id': 3, 'name': 'DOLIPRANE', 'dosage': '1G',
                                                'form': 'COMPRIMÉ', 'label': 'DOLIPRANE 1G CPR EFF 8'}]})
        assert content['lines'][0]['label'] == 'DOLIPRANE 1G CPR EFF 8'
