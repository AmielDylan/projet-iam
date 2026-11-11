"""Signature and stamp: transparent PNGs in the prescriber's account, frozen at issuance, shown on the PDF only."""
import base64
import struct
import zlib
from unittest.mock import patch

import pytest

from app.services.database import DatabasePool
from app.services.ordonnance import OrdonnanceService
from app.services.prescriber_assets import AssetError, PrescriberAssets
from tests.integration.test_issue import ready_draft


def png(width=4, height=2):
    """A tiny valid RGBA PNG."""
    raw = b''.join(b'\x00' + b'\x00\x00\x00\xff' * width for _ in range(height))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def user(uid):
    return {'id': uid, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0}


def test_save_read_and_delete_a_signature(prescriber):
    PrescriberAssets.save(prescriber, 'signature', png())
    assert PrescriberAssets.status(prescriber) == {'signature': True, 'stamp': False}
    assert PrescriberAssets.get(prescriber, 'signature') == png()
    stored = DatabasePool.execute_query('SELECT content FROM prescriber_assets')[0][0]
    assert stored.startswith('v1:')  # sealed, never raw image bytes
    PrescriberAssets.delete(prescriber, 'signature')
    assert PrescriberAssets.get(prescriber, 'signature') is None


@pytest.mark.parametrize('content', [b'not an image', b'\xff\xd8\xff\xe0 jpeg', b'\x89PNG\r\n\x1a\n' + b'0' * 600_000])
def test_only_reasonable_png_files_are_accepted(prescriber, content):
    with pytest.raises(AssetError):
        PrescriberAssets.save(prescriber, 'stamp', content)


def test_unknown_kind_is_refused(prescriber):
    with pytest.raises(AssetError):
        PrescriberAssets.save(prescriber, 'photo', png())


def test_assets_are_frozen_at_issuance_and_shown_on_the_pdf_only(client, prescriber):
    PrescriberAssets.save(prescriber, 'signature', png())
    PrescriberAssets.save(prescriber, 'stamp', png(6, 3))
    draft = ready_draft(prescriber)
    issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
    PrescriberAssets.delete(prescriber, 'signature')  # later change must not alter the frozen document

    with patch('app.web.routes.AuthService.current_user', return_value=user(prescriber)):
        printed = client.get(f"/ordonnances/{issued['id']}/impression").get_data(as_text=True)
        pdf = client.get(f"/ordonnances/{issued['id']}/impression?pdf=1").get_data(as_text=True)

    signature = base64.b64encode(png()).decode()
    assert signature not in printed and 'rx-signature' not in printed
    assert signature in pdf and 'rx-stamp-image' in pdf


def test_api_upload_status_image_and_isolation(client, prescriber, other_prescriber):
    with patch('app.api.routes.AuthService.current_user', return_value=user(prescriber)):
        up = client.post('/api/v1/prescriber/assets/signature', data=png(), content_type='image/png')
        status = client.get('/api/v1/prescriber/assets').get_json()
        image = client.get('/api/v1/prescriber/assets/signature')
        bad = client.post('/api/v1/prescriber/assets/signature', data=b'nope', content_type='image/png')
    with patch('app.api.routes.AuthService.current_user', return_value=user(other_prescriber)):
        foreign = client.get('/api/v1/prescriber/assets/signature')

    assert up.status_code == 200
    assert status['assets'] == {'signature': True, 'stamp': False}
    assert image.mimetype == 'image/png' and image.data == png()
    assert bad.status_code == 400
    assert foreign.status_code == 404
