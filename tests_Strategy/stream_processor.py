#!/usr/bin/env python3
import json
import numpy as np
import joblib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# — Configuration —
BROKER         = 'localhost'
PORT           = 1883
RAW_TOPIC      = 'dc/temperature/raw_encrypted'
MASKED_TOPIC   = 'dc/temperature/masked_encrypted'
OVERHEAT_TEMP  = 30.0
PROLONGED_SECS = 20

# — Load model & key —
model  = joblib.load('iforest.joblib')
cipher = Fernet(open('secret.key', 'rb').read())

# — State for prolonged-open detection —
door_open_start   = None
prolonged_alerted = False

def mask_temperature(temp: float, model) -> float:
    """
    Apply privacy masking:
     - If temp >= OVERHEAT_TEMP: pass through unchanged
     - If anomaly (IsolationForest): return 25 + Gaussian(0,0.1)
     - Else: return temp + Gaussian(0,0.02)
    """
    if temp >= OVERHEAT_TEMP:
        return temp
    is_anom = (model.predict([[temp]])[0] == -1)
    if is_anom:
        return 25.0 + np.random.normal(0, 0.1)
    else:
        return temp + np.random.normal(0, 0.02)

def on_connect(client, userdata, flags, rc):
    print(f"[Processor] Connected to broker (rc={rc})")
    client.subscribe(RAW_TOPIC)
    print(f"[Processor] Subscribed to topic: {RAW_TOPIC}")

def on_message(client, userdata, msg):
    global door_open_start, prolonged_alerted

    print(f"[Processor] Message received on {msg.topic}")

    # 1) Decrypt & parse
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        print(f"[Processor] Decrypt/parse error: {e}")
        return

    t_str = data.get('timestamp')
    temp  = data.get('temperature_C')
    t     = datetime.fromisoformat(t_str.replace('Z','+00:00'))

    # 2) Anomaly detection
    is_anom = (model.predict([[temp]])[0] == -1)

    # 3) Prolonged‐open alarm logic
    if is_anom:
        if door_open_start is None:
            door_open_start   = t
            prolonged_alerted = False
        elif not prolonged_alerted and (t - door_open_start) >= timedelta(seconds=PROLONGED_SECS):
            print(f"🚨 Prolonged door open since {door_open_start.time()}")
            prolonged_alerted = True
    else:
        door_open_start   = None
        prolonged_alerted = False

    # 4) Mask or pass‐through
    out_temp = mask_temperature(temp, model)
    if temp >= OVERHEAT_TEMP:
        print(f"[Processor] Overheat {temp:.2f}°C – passing real value")
    elif is_anom:
        print(f"[Processor] Anomaly {temp:.2f}→{out_temp:.2f} (masked)")

    # 5) Encrypt & publish
    new_payload = json.dumps({
        'timestamp':   t_str,
        'temperature': round(out_temp, 2),
        'anomaly':     bool(is_anom)
    }).encode()
    client.publish(MASKED_TOPIC, cipher.encrypt(new_payload))
    print(f"[Processor] Published to {MASKED_TOPIC}")

# — MQTT Client Setup —
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"[Processor] Connecting to {BROKER}:{PORT} …")
client.connect(BROKER, PORT)
client.loop_forever()
