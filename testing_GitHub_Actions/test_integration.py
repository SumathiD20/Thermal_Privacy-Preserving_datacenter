import pytest
import paho.mqtt.client as mqtt
import time
from cryptography.fernet import Fernet
import json

TOPIC_RAW = 'dc/temperature/raw_encrypted'
TOPIC_MASKED = 'dc/temperature/masked_encrypted'
TEST_TEMP = 55.0

# Load encryption key and create cipher
cipher = Fernet(open('secret.key', 'rb').read())

received = []

def on_message(client, userdata, msg):
    payload = cipher.decrypt(msg.payload)
    data = json.loads(payload)
    received.append(data)

@pytest.mark.integration
def test_publish_and_receive():
    # Setup MQTT client
    client = mqtt.Client()
    client.on_message = on_message
    client.connect('localhost', 1883)
    client.subscribe(TOPIC_MASKED)
    client.loop_start()

    # Send encrypted message
    message = {
        "timestamp": "2024-01-01T00:00:00Z",
        "temperature_C": TEST_TEMP
    }
    payload = cipher.encrypt(json.dumps(message).encode())
    client.publish(TOPIC_RAW, payload)

    # Wait for processor to respond
    time.sleep(3)  # give it time to process

    client.loop_stop()

    assert len(received) > 0, "No message received on masked topic"
    assert isinstance(received[0]['temperature'], float)
    assert 'anomaly' in received[0]
