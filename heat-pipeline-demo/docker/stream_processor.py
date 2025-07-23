import os
import json
import numpy as np
import joblib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# — Configuration (via environment or defaults) —
BROKER = os.getenv('BROKER_HOST', 'broker')
PORT = int(os.getenv('BROKER_PORT', '1883'))
RAW_TOPIC = 'dc/temperature/raw_encrypted'
MASKED_TOPIC = 'dc/temperature/masked_encrypted'
OVERHEAT_TEMP = 30.0
PROLONGED_SECS = 60

# — Load model and key from mounted files —
model = joblib.load('iforest.joblib')
cipher = Fernet(open('secret.key', 'rb').read())

# — State for prolonged-open detection —
door_open_start = None
prolonged_alert_sent = False

# — MQTT Callbacks —
def on_connect(client, userdata, flags, reasonCode, properties=None):
    print(f"[Processor] Connected to {BROKER}:{PORT} (rc={reasonCode})")
    client.subscribe(RAW_TOPIC)
    print(f"[Processor] Subscribed to topic: {RAW_TOPIC}")

def on_message(client, userdata, msg):
    global door_open_start, prolonged_alert_sent
    print(f"[Processor] Message received on {msg.topic}")
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        print(f"[Processor] Decrypt/JSON error: {e}")
        return

    t_str = data.get('timestamp')
    temp = data.get('temperature_C')
    t = datetime.fromisoformat(t_str.replace('Z','+00:00'))

    # Anomaly detection
    is_anomaly = (model.predict([[temp]]) == -1)

    # Prolonged door-open logic
    if is_anomaly:
        if door_open_start is None:
            door_open_start = t
            prolonged_alert_sent = False
        elif not prolonged_alert_sent and (t - door_open_start) >= timedelta(seconds=PROLONGED_SECS):
            print(f"🚨 Prolonged door-open alarm! Open since {door_open_start.time()}")
            prolonged_alert_sent = True
    else:
        door_open_start = None
        prolonged_alert_sent = False

    # Masking or pass-through
    if temp >= OVERHEAT_TEMP:
        out_temp = temp
        print(f"[Processor] Overheat {temp:.2f}°C at {t_str} — passing real value")
    elif is_anomaly:
        out_temp = 25 + np.random.normal(0, 0.1)
        print(f"[Processor] Anomaly {temp:.2f}→{out_temp:.2f}")
    else:
        out_temp = temp + np.random.normal(0, 0.02)

    # Encrypt and publish masked data
    payload = {
        'timestamp': t_str,
        'temperature': round(out_temp, 2),
        'anomaly': bool(is_anomaly)
    }
    encrypted = cipher.encrypt(json.dumps(payload).encode())
    client.publish(MASKED_TOPIC, encrypted)
    print(f"[Processor] Published to {MASKED_TOPIC}")

# — MQTT Client Setup (using MQTT v5) —
client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message

print(f"[Processor] Connecting to broker {BROKER}:{PORT} …")
client.connect(BROKER, PORT)
client.loop_forever()