"""IAM analysis of an ordonnance: interactions, same substance, allergies, derogations."""
from unittest.mock import patch

import pytest

from app.services.analysis import analyze

CATALOG = {
    1: {'id': 1, 'name': 'DOLIPRANE', 'substances': ['PARACÉTAMOL']},
    2: {'id': 2, 'name': 'EFFERALGAN', 'substances': ['PARACETAMOL']},
    3: {'id': 3, 'name': 'IXPRIM', 'substances': ['TRAMADOL', 'PARACETAMOL']},
    4: {'id': 4, 'name': 'KARDEGIC', 'substances': ['ACIDE ACETYLSALICYLIQUE']},
    5: {'id': 5, 'name': 'COUMADINE', 'substances': ['WARFARINE']},
    6: {'id': 6, 'name': 'CLAMOXYL', 'substances': ['AMOXICILLINE']},
    7: {'id': 7, 'name': 'ADVIL', 'substances': ['IBUPROFENE']},
    8: {'id': 8, 'name': 'VOLTARENE', 'substances': ['DICLOFENAC']},
}

INTERACTIONS = {
    frozenset(['ACIDE ACETYLSALICYLIQUE', 'WARFARINE']): [{
        'class_1': 'ACIDE ACETYLSALICYLIQUE', 'class_2': 'ANTIVITAMINES K',
        'niveau': 'Contre-indication', 'risques': 'Majoration du risque hémorragique',
        'details': '', 'actions': '',
    }],
    frozenset(['IBUPROFENE', 'WARFARINE']): [{
        'class_1': 'ANTI-INFLAMMATOIRES NON STEROIDIENS', 'class_2': 'ANTIVITAMINES K',
        'niveau': 'Association DECONSEILLEE', 'risques': 'Risque hémorragique', 'details': '', 'actions': '',
    }],
}


def line(line_id, medication_id=None, name=None, **extra):
    return {'line_id': line_id, 'medication_id': medication_id,
            'name': name or (CATALOG[medication_id]['name'] if medication_id else 'Tisane'),
            'posology': '1 par jour', 'substances': [], **extra}


@pytest.fixture(autouse=True)
def fake_references():
    def interactions(a, b):
        return INTERACTIONS.get(frozenset([a, b]), [])

    with patch('app.services.analysis.MedicationCatalogService.get', side_effect=CATALOG.get), \
         patch('app.services.analysis.InteractionService.get_interactions', side_effect=interactions) as lookup:
        yield lookup


def alerts_of(result, alert_type):
    return [alert for alert in result['alerts'] if alert['type'] == alert_type]


class TestSameSubstance:
    def test_two_brands_of_the_same_dci_raise_one_alert_naming_both_lines(self):
        result = analyze([line('a', 1), line('b', 2)])
        [alert] = alerts_of(result, 'same_substance')
        assert alert['line_ids'] == ['a', 'b']
        assert alert['requirement'] == 'justify'
        assert 'PARACETAMOL' in alert['message'].upper()

    def test_a_combination_product_triggers_when_one_of_its_dci_is_already_prescribed(self):
        result = analyze([line('a', 1), line('b', 3)])
        assert [a['line_ids'] for a in alerts_of(result, 'same_substance')] == [['a', 'b']]

    def test_same_class_but_different_dci_is_not_a_duplicate(self):
        result = analyze([line('a', 7), line('b', 8)])
        assert alerts_of(result, 'same_substance') == []
        assert all(alert['type'] != 'therapeutic_duplicate' for alert in result['alerts'])


class TestInteractions:
    def test_ci_blocks_and_cannot_be_derogated(self):
        first = analyze([line('a', 4), line('b', 5)])
        [alert] = alerts_of(first, 'interaction')
        assert alert['level'] == 'CI' and alert['requirement'] == 'blocking'

        second = analyze([line('a', 4), line('b', 5)], derogations={alert['id']: 'Bénéfice supérieur au risque'})
        assert second['summary']['can_issue'] is False
        assert alerts_of(second, 'interaction')[0]['derogation'] is None

    def test_asdec_requires_a_written_reason(self):
        result = analyze([line('a', 7), line('b', 5)])
        [alert] = alerts_of(result, 'interaction')
        assert alert['level'] == 'ASDEC' and alert['requirement'] == 'justify'
        assert result['summary']['can_issue'] is False

        justified = analyze([line('a', 7), line('b', 5)], derogations={alert['id']: 'Douleur rebelle, INR surveillé'})
        assert justified['summary']['can_issue'] is True
        assert alerts_of(justified, 'interaction')[0]['derogation'] == 'Douleur rebelle, INR surveillé'

    def test_blank_reason_is_not_a_derogation(self):
        result = analyze([line('a', 7), line('b', 5)])
        alert_id = alerts_of(result, 'interaction')[0]['id']
        assert analyze([line('a', 7), line('b', 5)], derogations={alert_id: '   '})['summary']['can_issue'] is False
        assert analyze([line('a', 7), line('b', 5)], derogations={alert_id: True})['summary']['can_issue'] is False

    def test_lookup_failure_stops_the_analysis_instead_of_hiding_a_risk(self, fake_references):
        fake_references.side_effect = RuntimeError('database down')
        with pytest.raises(RuntimeError):
            analyze([line('a', 4), line('b', 5)])


class TestAlertIdentity:
    def test_changing_a_concerned_line_invalidates_the_derogation(self):
        before = alerts_of(analyze([line('a', 7), line('b', 5), line('c', 6)]), 'interaction')[0]['id']
        other_line_changed = alerts_of(analyze([line('a', 7), line('b', 5), line('c', 6, posology='2 par jour')]), 'interaction')[0]['id']
        concerned_line_changed = alerts_of(analyze([line('a', 7, posology='3 par jour'), line('b', 5), line('c', 6)]), 'interaction')[0]['id']

        assert other_line_changed == before
        assert concerned_line_changed != before


class TestAllergies:
    def test_declared_allergy_to_a_dci_must_be_justified(self):
        result = analyze([line('a', 6)], patient={'allergies': ['amoxicilline']})
        [alert] = alerts_of(result, 'allergy')
        assert alert['line_ids'] == ['a'] and alert['requirement'] == 'justify'

    def test_no_allergy_alert_without_matching_dci(self):
        assert alerts_of(analyze([line('a', 1)], patient={'allergies': ['AMOXICILLINE']}), 'allergy') == []


class TestScope:
    def test_free_text_lines_are_listed_as_not_analyzed(self):
        result = analyze([line('a', 1), line('b', None, 'Préparation magistrale')])
        assert result['scope']['free_text_lines'] == ['Préparation magistrale']
        assert result['scope']['not_checked']

    def test_line_whose_catalog_entry_disappeared_counts_as_free_text(self):
        result = analyze([line('a', 999, 'Ancien médicament')])
        assert result['scope']['free_text_lines'] == ['Ancien médicament']

    def test_client_supplied_substances_are_ignored_for_catalog_lines(self):
        result = analyze([line('a', 1, substances=['WARFARINE']), line('b', 4)])
        assert alerts_of(result, 'interaction') == []
