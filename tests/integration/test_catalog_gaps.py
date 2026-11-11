"""Catalog gaps: free-text entries and search misses, turned into catalog entries."""
from unittest.mock import patch

import pytest

from app.services.catalog import MedicationCatalogService
from app.services.catalog_gaps import CatalogGaps, CatalogEntryError
from app.services.database import DatabasePool
from app.services.ordonnance import OrdonnanceService
from tests.integration.test_issue import ready_draft


def issue_with(owner, names):
    lines = [{'line_id': f'l{i}', 'name': name, 'posology': '1/j'} for i, name in enumerate(names)]
    draft = ready_draft(owner, lines=lines)
    return OrdonnanceService.issue(owner, draft['id'], version=draft['version'])


@pytest.fixture
def thesaurus(db):
    with DatabasePool.get_cursor() as cursor:
        cursor.executemany('INSERT INTO substances (substances) VALUES (%s)', [('ARTEMETHER',), ('LUMEFANTRINE',)])


def test_gaps_merge_free_text_and_search_misses_by_frequency(prescriber, other_prescriber):
    issue_with(prescriber, ['Coartem 20/120', 'Tisane'])
    issue_with(other_prescriber, ['coartem 20/120'])
    MedicationCatalogService.log_search_miss('Tisane')

    gaps = CatalogGaps.list()
    assert [(g['label'], g['free_text_count'], g['search_miss_count']) for g in gaps] == [
        ('Coartem 20/120', 2, 0), ('Tisane', 1, 1)]


def test_gaps_hold_no_patient_or_prescriber_data(prescriber):
    issue_with(prescriber, ['Coartem'])
    columns = {row[0] for row in DatabasePool.execute_query(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'medication_free_entries' AND table_schema = DATABASE()")}
    assert columns == {'name_key', 'name', 'occurrences', 'resolved_catalog_id', 'last_seen_at'}


def test_admin_creates_an_entry_that_prescribers_find_and_the_analysis_uses(prescriber, thesaurus):
    issue_with(prescriber, ['Coartem'])
    entry = CatalogGaps.create_entry(admin_id=1, payload={
        'name': 'Coartem', 'dosage': '20 mg/120 mg', 'form': 'comprimé',
        'substances': ['artéméther', 'LUMEFANTRINE'], 'resolves': 'Coartem'})

    found = MedicationCatalogService.search('coartem')
    assert [item['id'] for item in found] == [entry['id']]
    assert found[0]['substances'] == ['ARTEMETHER', 'LUMEFANTRINE']
    assert CatalogGaps.list() == []

    audit = DatabasePool.execute_query(
        'SELECT action_type, status, catalog_id FROM medication_enrichment_audit', dictionary=True)
    assert audit == [{'action_type': 'manual_catalog_entry', 'status': 'applied', 'catalog_id': entry['id']}]


def test_unknown_substance_is_refused(thesaurus):
    with pytest.raises(CatalogEntryError):
        CatalogGaps.create_entry(admin_id=1, payload={'name': 'X', 'substances': ['PLANTE INCONNUE']})


def test_admin_api(client, prescriber, thesaurus):
    admin = {'id': 1, 'role': 'admin', 'status': 'approved', 'must_change_password': 0}
    issue_with(prescriber, ['Coartem'])
    with patch('app.api.routes.AuthService.current_user', return_value=admin):
        gaps = client.get('/api/v1/admin/catalog/gaps').get_json()['gaps']
        substances = client.get('/api/v1/admin/catalog/substances?q=arte').get_json()['results']
        created = client.post('/api/v1/admin/catalog/entries',
                              json={'name': 'Coartem', 'substances': ['ARTEMETHER', 'LUMEFANTRINE']})
    with patch('app.api.routes.AuthService.current_user',
               return_value={**admin, 'id': prescriber, 'role': 'prescriber'}):
        refused = client.get('/api/v1/admin/catalog/gaps')

    assert gaps[0]['label'] == 'Coartem'
    assert substances == ['ARTEMETHER']
    assert created.status_code == 201
    assert refused.status_code == 403


def test_search_matches_every_word_across_name_dosage_and_dci(db):
    with DatabasePool.get_cursor() as cursor:
        for name, dosage, subs in (('DOLIPRANE', '1G', 'PARACETAMOL'), ('DOLIPRANE', '500MG', 'PARACETAMOL'),
                                   ('DOLIPRANE', '150MG | 81G', 'PARACETAMOL'),
                                   ('EFFERALGAN', '1000MG', 'PARACETAMOL')):
            cursor.execute(
                "INSERT INTO medication_catalog (nom_medicament, dosage, substances, specialite, source_hash, normalized_key) "
                "VALUES (%s, %s, %s, %s, SHA2(CONCAT(%s, %s), 256), SHA2(%s, 256))",
                (name, dosage, subs, name, name, dosage, name))

    assert [(r['name'], r['dosage']) for r in MedicationCatalogService.search('doliprane 1000')] == [('DOLIPRANE', '1G')]
    assert [(r['name'], r['dosage']) for r in MedicationCatalogService.search('doliprane 1g')] == [('DOLIPRANE', '1G')]
    assert {r['name'] for r in MedicationCatalogService.search('paracetamol 1000')} == {'DOLIPRANE', 'EFFERALGAN'}
    assert MedicationCatalogService.search('doliprane')[0]['name'] == 'DOLIPRANE'
