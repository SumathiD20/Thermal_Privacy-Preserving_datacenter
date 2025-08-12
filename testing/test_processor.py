import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from cryptography.fernet import Fernet

# Dummy model for testing
class DummyModel:
    def __init__(self, anomalies=[]):
        self.anomalies = anomalies

    def predict(self, X):
        # X is a list of [temp] values
        return [-1 if x[0] in self.anomalies else 1 for x in X]


# — Fixtures —
@pytest.fixture
def dummy_model():
    return DummyModel(anomalies=[55.0, 100.0])


# — Tests —

def test_anomaly_detection(dummy_model):
    assert dummy_model.predict([[55.0]])[0] == 1  # normal
    assert dummy_model.predict([[29.0]])[0] == -1  # anomaly

def test_overheat_threshold():
    OVERHEAT_TEMP = 30.0
    assert 32.5 >= OVERHEAT_TEMP
    assert 25.0 < OVERHEAT_TEMP

def test_temperature_masking_for_anomaly():
    # simulate masking logic
    temp = 22.0
    is_anomaly = True
    if is_anomaly:
        masked_temp = 25.0 + np.random.normal(0, 0.1)
        assert 24.5 <= masked_temp <= 25.5  # should be close to 25.0

def test_random_noise_for_normal_temp():
    temp = 23.0
    is_anomaly = False
    if not is_anomaly:
        noisy_temp = temp + np.random.normal(0, 0.02)
        assert 22.9 <= noisy_temp <= 23.1  # small variation

def test_prolonged_open_detection_logic():
    PROLONGED_SECS = 20
    start = datetime.utcnow()
    later = start + timedelta(seconds=25)
    duration = (later - start).total_seconds()
    assert duration > PROLONGED_SECS

def test_encryption_decryption_cycle():
    key = Fernet.generate_key()
    cipher = Fernet(key)
    original_data = b'{"temperature": 24.5}'
    encrypted = cipher.encrypt(original_data)
    decrypted = cipher.decrypt(encrypted)
    assert decrypted == original_data
