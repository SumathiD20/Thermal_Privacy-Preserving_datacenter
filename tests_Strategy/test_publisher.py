import pytest
import json
from cryptography.fernet import Fernet

# Import your publisher encryption function
from publisher import encrypt_payload

@pytest.fixture(scope="module")
def cipher():
    return Fernet(open('secret.key','rb').read())

def test_encrypt_decrypt_roundtrip(cipher):
    sample = {'timestamp': '2025-07-24T12:00:00Z', 'temperature_C': 25.0}
    encrypted = encrypt_payload(sample, cipher)
    decrypted = json.loads(cipher.decrypt(encrypted))
    assert decrypted == sample
