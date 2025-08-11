#!/usr/bin/env python3
import json, time
import numpy as np
import joblib
import pandas as pd                      # for sklearn feature-name consistency
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt
from datadog import initialize, statsd

# — Datadog setup —
options = {'statsd_host': '127.0.0.1', 'statsd_port': 8125}
initialize(**options)

# — Configuration —
BROKER          = 'localhost'
PORT            = 1883
RAW_TOPIC       = 'dc/temperature/raw_encrypted'
MASKED_TOPIC    = 'dc/temperature/masked_encrypted'
OVERHEAT_TEMP   = 30.0
UNDERCOOL_TEMP  = 21.0
PROLONGED_SECS  = 20

# — Load model and key —
model  = joblib.load('iforest.joblib')
cipher = Fernet(open('secret.key', 'rb').read())

# — State for prolonged-open detection —
door_open_start   = None
prolonged_alerted = False

def on_connect(client, userdata, flags, rc):
    print(f"[Processor] Connected to broker (rc={rc})")
    client.subscribe(RAW_TOPIC)
    print(f"[Processor] Subscribed to topic: {RAW_TOPIC}")

def on_message(client, userdata, msg):
    global door_open_start, prolonged_alerted
    t_proc_start = time.time()
    print(f"[Processor] Message received on {msg.topic}")

    statsd.increment('stream_processor.messages_received')

    # Decrypt & parse
    try:
        payload = cipher.decrypt(msg.payload)
        data    = json.loads(payload)
    except Exception as e:
        print(f"[Processor] Decrypt/parse error: {e}")
        statsd.increment('stream_processor.decrypt_errors')
        return

    t_str    = data.get('timestamp')
    temp     = data.get('temperature_C')
    t_pub_ms = data.get('t_pub_ms')   # carry-through for end-to-end latency
    t        = datetime.fromisoformat(t_str.replace('Z', '+00:00'))

    if isinstance(temp, (int, float)):
        statsd.histogram('stream_processor.temperature', temp)

    # Anomaly detection (use DataFrame to avoid sklearn warning)
    is_anomaly = model.predict(pd.DataFrame([[temp]], columns=["temperature_C"]))[0] == -1
    if is_anomaly:
        statsd.increment('stream_processor.anomalies_detected')

    # Prolonged‐open alarm logic
    if is_anomaly:
        if door_open_start is None:
            door_open_start   = t
            prolonged_alerted = False
        elif not prolonged_alerted and (t - door_open_start) >= timedelta(seconds=PROLONGED_SECS):
            print(f"\033[93m Prolonged door open since {door_open_start.time()}\033[0m")
            prolonged_alerted = True
            statsd.increment('stream_processor.prolonged_open_alerts')
    else:
        door_open_start   = None
        prolonged_alerted = False

    # Mask or pass-through
    if temp >= OVERHEAT_TEMP:
        out_temp = temp
        print(f"\033[91m[Processor] Overheat {temp:.2f}°C – passing real value\033[0m")
        statsd.increment('stream_processor.overheat_events')
    elif temp <= UNDERCOOL_TEMP:
        out_temp = temp
        print(f"\033[94m[Processor] Undercool {temp:.2f}°C – passing real value\033[0m")
        statsd.increment('stream_processor.undercool_events')
    elif is_anomaly:
        out_temp = 25.0 + np.random.normal(0, 0.1)
        print(f"[Processor] Anomaly {temp:.2f}→{out_temp:.2f} (masked)")
    else:
        out_temp = temp + np.random.normal(0, 0.02)

    # Build outgoing payload — keep t_pub_ms for the subscriber latency calc
    new_payload = {
        'timestamp':   t_str,
        'temperature': round(out_temp, 2),
        'anomaly':     bool(is_anomaly),
        't_pub_ms':    t_pub_ms
    }

    # Publish masked, encrypted
    client.publish(MASKED_TOPIC, cipher.encrypt(json.dumps(new_payload).encode()))
    print(f"[Processor] Published to {MASKED_TOPIC}")
    statsd.increment('stream_processor.published')

    # Timing metrics
    proc_ms = (time.time() - t_proc_start) * 1000.0
    statsd.gauge('stream_processor.proc_time_ms', proc_ms)

    # derive approx end-to-processor latency 
    if t_pub_ms is not None:
        try:
            approx_ms = int(time.time() * 1000) - int(t_pub_ms)
            statsd.histogram('stream_processor.approx_latency_ms', max(approx_ms, 0))
        except Exception:
            pass

# — MQTT Client Setup —
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"[Processor] Connecting to {BROKER}:{PORT} …")
client.connect(BROKER, PORT)
client.loop_forever()
