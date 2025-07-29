#!/usr/bin/env python3
import json
import numpy as np
import joblib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# — Configuration —
BROKER = 'localhost'
PORT = 1883
RAW_TOPIC = 'dc/temperature/raw_encrypted'
MASKED_TOPIC = 'dc/temperature/masked_encrypted'
OVERHEAT_TEMP = 30.0
PROLONGED_SECS = 20

# — Load model and key (files must be in the same directory) —
model = joblib.load('iforest.joblib')
cipher = Fernet(open('secret.key', 'rb').read())

# — State for prolonged-open detection —
door_open_start = None
prolonged_alerted = False


def on_connect(client, userdata, flags, rc):
    print(f"[Processor] Connected to broker (rc={rc})")
    client.subscribe(RAW_TOPIC)
    print(f"[Processor] Subscribed to topic: {RAW_TOPIC}")


def on_message(client, userdata, msg):
    global door_open_start, prolonged_alerted
    print(f"[Processor] Message received on {msg.topic}")

    # Decrypt & parse
    try:
        payload = cipher.decrypt(msg.payload)
        data = json.loads(payload)
    except Exception as e:
        print(f"[Processor] Decrypt/parse error: {e}")
        return

    t_str = data.get('timestamp')
    temp = data.get('temperature_C')
    t = datetime.fromisoformat(t_str.replace('Z', '+00:00'))

    # Anomaly detection
    is_anomaly = model.predict([[temp]])[0] == -1

    # Prolonged‐open alarm logic
    if is_anomaly:
        if door_open_start is None:
            door_open_start = t
            prolonged_alerted = False
        elif not prolonged_alerted and (t - door_open_start) >= timedelta(seconds=PROLONGED_SECS):
            print(f"\033[93m Prolonged door open since {door_open_start.time()}\033[0m")
            prolonged_alerted = True
    else:
        door_open_start = None
        prolonged_alerted = False

    # Mask or pass‐through
    if temp >= OVERHEAT_TEMP:
        out_temp = temp
        print(f"\033[91m[Processor] Overheat {temp:.2f}°C – passing real value\033[0m")
    elif is_anomaly:
        out_temp = 25.0 + np.random.normal(0, 0.1)
        print(f"[Processor] Anomaly {temp:.2f}→{out_temp:.2f} (masked)")
    else:
        out_temp = temp + np.random.normal(0, 0.02)

    # Encrypt & publish masked data
    new_payload = json.dumps({
        'timestamp': t_str,
        'temperature': round(out_temp, 2),
        'anomaly': bool(is_anomaly)
    }).encode()
    client.publish(MASKED_TOPIC, cipher.encrypt(new_payload))
    print(f"[Processor] Published to {MASKED_TOPIC}")


# — MQTT Client Setup (plain MQTT) —
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"[Processor] Connecting to {BROKER}:{PORT} …")
client.connect(BROKER, PORT)
client.loop_forever()
