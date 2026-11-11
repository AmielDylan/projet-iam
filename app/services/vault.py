"""Vault: encryption at rest and blind search index for health data.

Health data (patient records, ordonnance contents and versions) is stored as
sealed text: AES-256-GCM, with the key id written in clear so that old keys
keep working during a rotation.

Keys come from the host's environment, never from the database:

- DATA_ENCRYPTION_KEYS: "kid:base64key[,kid:base64key...]". The first key
  seals new data; the others only open older data.
- DATA_INDEX_KEY: base64 key for the HMAC search index. Changing it requires
  rebuilding the index (scripts/rotate_data_keys.py).

Generate keys with: python -m app.services.vault
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import unicodedata
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


FORMAT = "v1"
MIN_TOKEN_LENGTH = 2
MAX_TOKEN_LENGTH = 20


class VaultError(Exception):
    """Raised when keys are missing or sealed text cannot be opened."""


class Vault:
    """Seal and open documents; build search tokens that do not reveal the text."""

    def __init__(self, encryption_keys: str, index_key: str):
        self._keys = _parse_keys(encryption_keys)
        self._current_id = next(iter(self._keys))
        self._index_key = _decode_key(index_key, "DATA_INDEX_KEY")

    # Sealing -----------------------------------------------------------------

    def seal_json(self, document: Any) -> str:
        plaintext = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        nonce = os.urandom(12)
        aad = f"{FORMAT}:{self._current_id}".encode()
        ciphertext = AESGCM(self._keys[self._current_id]).encrypt(nonce, plaintext, aad)
        payload = base64.urlsafe_b64encode(nonce + ciphertext).decode()
        return f"{FORMAT}:{self._current_id}:{payload}"

    def open_json(self, sealed: str) -> Any:
        version, key_id, payload = _split(sealed)
        key = self._keys.get(key_id)
        if key is None:
            raise VaultError(f"Clé de chiffrement inconnue : {key_id}")
        try:
            raw = base64.urlsafe_b64decode(payload.encode())
            plaintext = AESGCM(key).decrypt(raw[:12], raw[12:], f"{version}:{key_id}".encode())
        except (InvalidTag, ValueError) as exc:
            raise VaultError("Texte chiffré illisible ou altéré") from exc
        return json.loads(plaintext.decode("utf-8"))

    def needs_reseal(self, sealed: str) -> bool:
        return _split(sealed)[1] != self._current_id

    def reseal(self, sealed: str) -> str:
        return self.seal_json(self.open_json(sealed))

    # Blind index -------------------------------------------------------------

    def blind(self, value: str, purpose: str) -> str:
        """Exact-match token for a value, e.g. a birthdate."""
        message = f"{purpose}:{normalize(value)}".encode("utf-8")
        return hmac.new(self._index_key, message, hashlib.sha256).hexdigest()

    def name_tokens(self, text: str) -> list[str]:
        """Tokens for every prefix of every word, so that 'kof' finds 'Koffi'."""
        tokens = set()
        for word in words(text):
            for length in range(MIN_TOKEN_LENGTH, min(len(word), MAX_TOKEN_LENGTH) + 1):
                tokens.add(self.blind(word[:length], "name"))
        return sorted(tokens)

    def query_tokens(self, query: str) -> list[str]:
        """One token per searched word; a record matches when it has all of them."""
        return [
            self.blind(word[:MAX_TOKEN_LENGTH], "name")
            for word in words(query)
            if len(word) >= MIN_TOKEN_LENGTH
        ]


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.strip().upper()


def words(text: str) -> list[str]:
    return [word for word in re.split(r"[^A-Z0-9]+", normalize(text)) if word]


def _split(sealed: str) -> tuple[str, str, str]:
    parts = str(sealed or "").split(":", 2)
    if len(parts) != 3 or parts[0] != FORMAT:
        raise VaultError("Format de texte chiffré inconnu")
    return parts[0], parts[1], parts[2]


def _decode_key(value: str, name: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(str(value or "").strip().encode())
    except ValueError as exc:
        raise VaultError(f"{name} n'est pas en base64") from exc
    if len(key) != 32:
        raise VaultError(f"{name} doit contenir une clé de 32 octets")
    return key


def _parse_keys(spec: str) -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    for entry in str(spec or "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        key_id, _, value = entry.partition(":")
        if not key_id or not value or not re.fullmatch(r"[A-Za-z0-9_-]+", key_id):
            raise VaultError("DATA_ENCRYPTION_KEYS attend des entrées kid:clé")
        keys[key_id] = _decode_key(value, f"DATA_ENCRYPTION_KEYS ({key_id})")
    if not keys:
        raise VaultError("DATA_ENCRYPTION_KEYS est vide")
    return keys


# Process-wide vault, installed at application start ------------------------

_installed: Vault | None = None


def install(vault: Vault) -> None:
    global _installed
    _installed = vault


def vault() -> Vault:
    if _installed is None:
        raise VaultError("Le coffre n'est pas configuré")
    return _installed


def generate_key() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


if __name__ == "__main__":
    print(f"DATA_ENCRYPTION_KEYS=k1:{generate_key()}")
    print(f"DATA_INDEX_KEY={generate_key()}")
