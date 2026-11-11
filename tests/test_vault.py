"""Vault: encryption at rest and blind search index for health data."""
import base64
import os

import pytest

from app.services.vault import Vault, VaultError


def key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


@pytest.fixture
def vault():
    v = Vault(encryption_keys=f"k1:{key()}", index_key=key())
    return v


class TestSealing:
    def test_round_trip_keeps_the_document(self, vault):
        document = {'first_name': 'Awa', 'allergies': ['AMOXICILLINE'], 'weight': 18.5}
        assert vault.open_json(vault.seal_json(document)) == document

    def test_sealed_text_reveals_nothing(self, vault):
        sealed = vault.seal_json({'last_name': 'KOFFI'})
        assert 'KOFFI' not in sealed
        assert sealed.startswith('v1:k1:')

    def test_same_document_seals_differently_each_time(self, vault):
        assert vault.seal_json({'a': 1}) != vault.seal_json({'a': 1})

    def test_tampered_text_is_refused(self, vault):
        sealed = vault.seal_json({'a': 1})
        tampered = sealed[:-4] + ('AAAA' if not sealed.endswith('AAAA') else 'BBBB')
        with pytest.raises(VaultError):
            vault.open_json(tampered)

    def test_another_key_cannot_open(self, vault):
        sealed = vault.seal_json({'a': 1})
        stranger = Vault(encryption_keys=f"k1:{key()}", index_key=key())
        with pytest.raises(VaultError):
            stranger.open_json(sealed)


class TestRotation:
    def test_old_key_still_opens_and_reseal_moves_to_the_new_key(self):
        old, new, index = key(), key(), key()
        before = Vault(encryption_keys=f"k1:{old}", index_key=index)
        sealed = before.seal_json({'a': 1})

        after = Vault(encryption_keys=f"k2:{new},k1:{old}", index_key=index)
        assert after.open_json(sealed) == {'a': 1}
        assert after.needs_reseal(sealed)

        resealed = after.reseal(sealed)
        assert resealed.startswith('v1:k2:')
        assert not after.needs_reseal(resealed)
        assert Vault(encryption_keys=f"k2:{new}", index_key=index).open_json(resealed) == {'a': 1}


class TestSearchIndex:
    def test_name_prefixes_match_without_revealing_the_name(self, vault):
        tokens = vault.name_tokens('Koffi Awa')
        assert vault.query_tokens('kof') [0] in tokens
        assert vault.query_tokens('AWA')[0] in tokens
        assert all('KOF' not in token for token in tokens)

    def test_accents_and_case_are_ignored(self, vault):
        assert vault.query_tokens('héloïse') == vault.query_tokens('HELOISE')

    def test_one_letter_words_are_not_searchable(self, vault):
        assert vault.query_tokens('k') == []

    def test_exact_value_index_is_stable_per_purpose(self, vault):
        assert vault.blind('2019-04-02', 'birthdate') == vault.blind('2019-04-02', 'birthdate')
        assert vault.blind('2019-04-02', 'birthdate') != vault.blind('2019-04-02', 'other')


class TestConfiguration:
    def test_missing_keys_are_refused(self):
        with pytest.raises(VaultError):
            Vault(encryption_keys='', index_key=key())

    def test_short_key_is_refused(self):
        with pytest.raises(VaultError):
            Vault(encryption_keys='k1:' + base64.urlsafe_b64encode(b'short').decode(), index_key=key())


class TestProductionKeys:
    def test_production_refuses_to_start_without_keys(self, monkeypatch):
        from app.config import ProductionConfig

        monkeypatch.delenv('DATA_ENCRYPTION_KEYS', raising=False)
        monkeypatch.delenv('DATA_INDEX_KEY', raising=False)
        with pytest.raises(ValueError):
            ProductionConfig().DATA_ENCRYPTION_KEYS
        with pytest.raises(ValueError):
            ProductionConfig().DATA_INDEX_KEY

    def test_development_keys_build_a_working_vault(self):
        from app.config import DevelopmentConfig

        config = DevelopmentConfig()
        dev_vault = Vault(config.DATA_ENCRYPTION_KEYS, config.DATA_INDEX_KEY)
        assert dev_vault.open_json(dev_vault.seal_json({'a': 1})) == {'a': 1}
