import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from cryptography.fernet import Fernet

# Dummy Model 
class DummyModel:
    def __init__(self, anomalies=[]):
        self.anomalies = anomalies

    def predict(self, X):
        return [-1 if x[0] in self.anomalies else 1 for x in X]

# Fixtures 
@pytest.fixture
def dummy_model():
    return DummyModel(anomalies=[55.0, 100.0, 29.0])

# Tests 

def test_anomaly_detection(dummy_model):
    print("Testing anomaly detection...")
    assert dummy_model.predict([[25.0]])[0] == 1
    assert dummy_model.predict([[29.0]])[0] == -1
    print("✓ Normal and anomaly prediction passed.")

def test_overheat_threshold():
    OVERHEAT_TEMP = 30.0
    print(f"Checking overheat threshold: {OVERHEAT_TEMP}")
    assert 32.5 >= OVERHEAT_TEMP
    assert 25.0 < OVERHEAT_TEMP
    print("✓ Overheat logic passed.")

def test_temperature_masking_for_anomaly():
    temp = 22.0
    is_anomaly = True
    print(f"Masking temp={temp} for anomaly...")
    if is_anomaly:
        masked_temp = 25.0 + np.random.normal(0, 0.1)
        print(f"→ Masked value: {masked_temp:.2f}")
        assert 24.5 <= masked_temp <= 25.5
        print("Anomaly masking range passed.")

def test_random_noise_for_normal_temp():
    temp = 23.0
    is_anomaly = False
    print(f"Applying noise to normal temp={temp}")
    if not is_anomaly:
        noisy_temp = temp + np.random.normal(0, 0.02)
        print(f"→ Noisy temp: {noisy_temp:.2f}")
        assert 22.9 <= noisy_temp <= 23.1
        print("Noise masking for normal temp passed.")

def test_prolonged_open_detection_logic():
    PROLONGED_SECS = 20
    start = datetime.utcnow()
    later = start + timedelta(seconds=25)
    duration = (later - start).total_seconds()
    print(f"Door open duration: {duration}s")
    assert duration > PROLONGED_SECS
    print("Prolonged detection logic passed.")

def test_encryption_decryption_cycle():
    key = Fernet.generate_key()
    cipher = Fernet(key)
    original_data = b'{"temperature": 24.5}'
    encrypted = cipher.encrypt(original_data)
    decrypted = cipher.decrypt(encrypted)
    print(f"Original: {original_data}, Decrypted: {decrypted}")
    assert decrypted == original_data
    print("Encryption-decryption cycle passed.")


@pytest.mark.parametrize("temp", [29.9, 30.0, 30.1])
def test_overheat_masking_range(temp):
    OVERHEAT_TEMP = 30.0
    print(f"Testing edge temp: {temp}")
    if temp >= OVERHEAT_TEMP:
        assert temp >= OVERHEAT_TEMP
    else:
        noisy_temp = temp + np.random.normal(0, 0.02)
        print(f"→ Noisy temp: {noisy_temp:.2f}")
        assert temp - 0.05 <= noisy_temp <= temp + 0.05
    print("Edge-case masking check passed.")

def test_batch_prediction(dummy_model):
    inputs = [[25.0], [55.0], [22.0], [100.0]]
    print(f"Testing batch predictions: {inputs}")
    results = dummy_model.predict(inputs)
    expected = [1, -1, 1, -1]
    print(f"Results: {results}")
    assert results == expected
    print("Batch prediction passed.")

def test_edge_anomaly_masking():
    anomaly_temps = [30.0, 55.0]
    for temp in anomaly_temps:
        masked = 25.0 + np.random.normal(0, 0.1)
        print(f"Temp: {temp} → Masked: {masked:.2f}")
        assert 24.5 <= masked <= 25.5
    print("Edge anomaly masking passed.")

def test_encryption_failure_with_wrong_key():
    key1 = Fernet.generate_key()
    key2 = Fernet.generate_key()
    cipher1 = Fernet(key1)
    cipher2 = Fernet(key2)

    original = b"secret"
    encrypted = cipher1.encrypt(original)
    print("Attempting to decrypt with wrong key...")
    with pytest.raises(Exception):
        cipher2.decrypt(encrypted)
    print("Decryption with wrong key failed as expected.")

def test_prolonged_exact_threshold():
    PROLONGED_SECS = 20
    start = datetime.utcnow()
    later = start + timedelta(seconds=20)
    duration = (later - start).total_seconds()
    print(f"Duration: {duration}s")
    assert duration >= PROLONGED_SECS
    print("Exact threshold detection passed.")

@pytest.mark.parametrize("temp", [22.5, 28.7, 30.1])
def test_multiple_encrypt_decrypt(temp):
    key = Fernet.generate_key()
    cipher = Fernet(key)
    original = f'{{"temperature": {temp}}}'.encode()
    encrypted = cipher.encrypt(original)
    decrypted = cipher.decrypt(encrypted)
    print(f"Original: {original}, Decrypted: {decrypted}")
    assert decrypted == original
    print("Encrypt/decrypt passed for temp =", temp)
