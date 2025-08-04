import pytest
import json
import random
import time
from datetime import datetime
from cryptography.fernet import Fernet

# Import subscriber logic or constants
from subscriber import OVERHEAT, NIGHT_START, NIGHT_END, PROLONGED_SEC, on_message

class DummyClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, msg):
        self.published.append((topic,msg))

@pytest.fixture(scope="module")
def cipher():
    return Fernet(open('secret.key','rb').read())

def make_msg(temp, ts):
    data = json.dumps({'timestamp':ts,'temperature':temp,'anomaly':temp<24}).encode()
    return cipher.encrypt(data)

def test_overheat_alert(capsys, cipher):
    # Simulate an overheat message
    ts = '2025-07-24T13:00:00Z'
    msg = make_msg(OVERHEAT + 1.0, ts)
    # Call on_message directly
    from subscriber import client, on_message  # or your handler
    on_message(client, None, type("x",(object,),{'payload':msg,'topic':''}))
    captured = capsys.readouterr()
    assert "OVERHEAT" in captured.out

def test_night_door_alert(capsys, cipher):
    # Simulate an anomaly at 22:05
    ts = '2025-07-24T22:05:00Z'
    msg = make_msg(23.0, ts)
    on_message(client, None, type("x",(object,),{'payload':msg,'topic':''}))
    captured = capsys.readouterr()
    assert "Night‐time door event" in captured.out

def test_prolonged_open(capsys, cipher):
    # Send anomaly messages over PROLONGED_SEC+1 seconds
    base = datetime.fromisoformat('2025-07-24T12:00:00+00:00')
    for i in range(PROLONGED_SEC + 2):
        ts = (base + timedelta(seconds=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
        msg = make_msg(23.0, ts)
        on_message(client, None, type("x",(object,),{'payload':msg,'topic':''}))
    captured = capsys.readouterr()
    assert "Prolonged‐open" in captured.out
