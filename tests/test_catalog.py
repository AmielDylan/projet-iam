"""Tests for medication catalog and prescription analysis."""
from unittest.mock import patch

from openpyxl import Workbook

from app.services.catalog import MedicationCatalogService
from scripts.import_medication_catalog import EXPECTED_COLUMNS, read_rows


class TestMedicationCatalogService:
    """Service tests for prescription catalog behavior."""

    def test_split_substances(self):
        assert MedicationCatalogService.split_substances('aspirine | warfarine | ') == ['aspirine', 'warfarine']

    def test_analyze_free_text_unknown(self):
        result = MedicationCatalogService.analyze_prescription([
            {'client_id': 'm1', 'name': 'Préparation locale', 'is_free_text': True}
        ])

        assert result['success'] is True
        assert result['summary']['items_count'] == 1
        assert result['alerts'][0]['type'] == 'unknown_medication'

    @patch('app.services.catalog.InteractionService.get_classes_from_substance')
    @patch('app.services.catalog.InteractionService.get_interactions')
    @patch('app.services.catalog.MedicationCatalogService.get')
    def test_analyze_catalog_pair(self, mock_get, mock_interactions, mock_classes):
        mock_get.side_effect = [
            {'id': 1, 'name': 'ASPIRINE', 'dosage': '', 'form': '', 'box_count': None, 'substances': ['ACIDE ACETYLSALICYLIQUE'], 'is_known': True},
            {'id': 2, 'name': 'WARFARINE', 'dosage': '', 'form': '', 'box_count': None, 'substances': ['WARFARINE'], 'is_known': True},
        ]
        mock_interactions.return_value = [{
            'class_1': 'ANTIAGREGANTS',
            'class_2': 'ANTICOAGULANTS',
            'details': 'Risque hémorragique',
            'risques': 'Hémorragie',
            'niveau': 'Association déconseillée',
            'niveau_id': 2,
            'actions': 'Surveillance'
        }]
        mock_classes.return_value = []

        result = MedicationCatalogService.analyze_prescription([
            {'client_id': 'm1', 'medication_id': 1},
            {'client_id': 'm2', 'medication_id': 2},
        ])

        assert result['summary']['interactions_count'] == 1
        assert result['alerts'][0]['type'] == 'interaction'
        assert result['alerts'][0]['severity'] == 'major'


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
        with patch('app.api.routes.MedicationCatalogService.analyze_prescription') as mock_analyze:
            mock_analyze.return_value = {
                'success': True,
                'items': [],
                'alerts': [],
                'interactions': [],
                'summary': {'items_count': 0, 'alerts_count': 0, 'interactions_count': 0, 'can_print': True}
            }

            response = client.post('/api/v1/prescriptions/analyze', json={'items': [{'name': 'ASPIRINE'}]})

        assert response.status_code == 200
        assert response.get_json()['success'] is True

    def test_analyze_prescription_rejects_invalid_items(self, client):
        response = client.post('/api/v1/prescriptions/analyze', json={'items': 'ASPIRINE'})

        assert response.status_code == 400


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
