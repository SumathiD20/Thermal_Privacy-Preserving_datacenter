import json
import numpy as np
import joblib
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta

# Config
MODEL_PATH    = 'iforest.joblib'
KEY_PATH      = 'secret.key'
BROKER        = '0.0.0.0'
PORT          = 1883
RAW_TOPIC     = 'dc/temperature/raw_encrypted'
MASKED_TOPIC  = 'dc/temperature/masked_encrypted'
OVERHEAT_TEMP = 30.0
PROLONGED_SECS= 60

# Load model & key
model  = joblib.load(MODEL_PATH)
cipher = Fernet(open(KEY_PATH,'rb').read())

# State for prolonged-open
door_start = None
alerted    = False

def on_connect(c, u, flags, rc):
    print(f"[Processor] Connected (rc={rc})")
    c.subscribe(RAW_TOPIC)
    print(f"[Processor] Subscribed to {RAW_TOPIC}")

def on_message(c, u, msg):
    global door_start, alerted

    print(f"[Processor] Message on {msg.topic}")
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        print("Decryption error:", e)
        return

    t_str = data['timestamp']
    temp  = data['temperature_C']
    t     = datetime.fromisoformat(t_str.replace('Z','+00:00'))

    is_anom = (model.predict([[temp]]) == -1)

    # Prolonged-open logic
    if is_anom:
        if door_start is None:
            door_start = t
            alerted = False
        elif not alerted and (t - door_start) >= timedelta(seconds=PROLONGED_SECS):
            print(f"🚨 Prolonged open since {door_start.time()}")
            alerted = True
    else:
        door_start = None
        alerted    = False

    # Mask or pass-through
    if temp >= OVERHEAT_TEMP:
        out = temp
        print(f"[Processor] Overheat {temp:.2f}°C at {t_str}")
    elif is_anom:
        out = 25 + np.random.normal(0,0.1)
        print(f"[Processor] Anomaly {temp:.2f}→{out:.2f}")
    else:
        out = temp + np.random.normal(0,0.02)

    payload = {'timestamp': t_str,
               'temperature': round(out,2),
               'anomaly': bool(is_anom)}
    encrypted = cipher.encrypt(json.dumps(payload).encode())
    c.publish(MASKED_TOPIC, encrypted)
    print(f"[Processor] Published to {MASKED_TOPIC}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
print("[Processor] Starting loop…")
client.loop_forever()
