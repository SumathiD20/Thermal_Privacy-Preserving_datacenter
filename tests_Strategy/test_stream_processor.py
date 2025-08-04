import pytest
import numpy as np
import joblib
from cryptography.fernet import Fernet

# Import the masking function and model from stream_processor.py
# Need to pull out mask_temperature() from the script into a function.
from stream_processor import mask_temperature, PROLONGED_SECS, OVERHEAT_TEMP, model as processor_model

@pytest.fixture(scope="module")
def model_and_cipher():
    m = processor_model  # already loaded in the module
    key = open('secret.key','rb').read()
    c = Fernet(key)
    return m, c

def test_anomaly_flagging(model_and_cipher):
    model, _ = model_and_cipher
    # A “quiet” reading should NOT be flagged as anomaly
    assert model.predict([[25.0]])[0] == 1
    # A dip reading should be flagged
    assert model.predict([[23.0]])[0] == -1

@pytest.mark.parametrize("temp,expected", [
    # Overheat should pass through unchanged
    (OVERHEAT_TEMP + 1.0, True),
    (OVERHEAT_TEMP + 5.0, True),
])
def test_overheat_passthrough(model_and_cipher, temp, expected):
    model, _ = model_and_cipher
    out = mask_temperature(temp, model)
    # if expected=True, out must equal temp exactly
    assert out == pytest.approx(temp)

def test_masking_under_threshold(model_and_cipher):
    model, _ = model_and_cipher
    temp = 24.5  # normal reading
    out = mask_temperature(temp, model)
    # should not equal exactly (noise injected)
    assert out != pytest.approx(temp)

def test_masking_anomaly(model_and_cipher):
    model, _ = model_and_cipher
    temp = 23.0  # anomaly dip
    out = mask_temperature(temp, model)
    # should be around baseline + large noise: near 25 ±0.3
    assert 24.7 < out < 25.3
