#!/usr/bin/env python3
import os
import time
import json
from io import StringIO

import pandas as pd
import paho.mqtt.client as mqtt
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
BROKER     = os.getenv('MQTT_BROKER', 'localhost')
PORT       = int(os.getenv('MQTT_PORT', '1883'))
TOPIC      = os.getenv('MQTT_PUB_TOPIC', 'dc/temperature/raw_encrypted')
CSV_FILE   = os.getenv('CSV_FILE', 'temp_reading.csv')
PUBLISH_HZ = float(os.getenv('PUBLISH_HZ', '1'))
QOS        = int(os.getenv('MQTT_QOS', '0'))
DELAY      = 1.0 / max(PUBLISH_HZ, 0.0001)

# ── Load encryption key ──────────────────────────────────────────────────────
with open('secret.key', 'rb') as f:
    cipher = Fernet(f.read())

# ── Load CSV (ignore #comments and blank lines) ──────────────────────────────
# Easiest: let pandas skip comments/blanks for us.
df = pd.read_csv(
    CSV_FILE,
    comment='#',
    skip_blank_lines=True,
    dtype={'temperature_C': float}
)

# Ensure required columns exist
required_cols = {'timestamp', 'temperature_C'}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"CSV is missing required columns: {missing}. Found: {list(df.columns)}")

# Parse timestamps and drop any bad rows
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
df = df.dropna(subset=['timestamp']).reset_index(drop=True)

if df.empty:
    raise ValueError("No valid rows after parsing timestamps. Check your CSV formatting.")

# ── MQTT client ──────────────────────────────────────────────────────────────
client = mqtt.Client()
client.connect(BROKER, PORT)
client.loop_start()

print(f"[Publisher] Broker={BROKER}:{PORT}  Topic={TOPIC}  Rate={PUBLISH_HZ} Hz  Rows={len(df)}")

# ── Publish encrypted readings ───────────────────────────────────────────────
for _, row in df.iterrows():
    t_str = row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
    t_pub_ms = int(time.time() * 1000)

    payload = {
        'timestamp':     t_str,
        'temperature_C': float(row['temperature_C']),
        't_pub_ms':      t_pub_ms
    }

    encrypted = cipher.encrypt(json.dumps(payload).encode('utf-8'))
    client.publish(TOPIC, encrypted, qos=QOS)
    print(f"[Publisher] → {TOPIC} @ {t_str}  temp={row['temperature_C']:.2f} (qos={QOS})")

    time.sleep(DELAY)

# ── Clean up ─────────────────────────────────────────────────────────────────
client.loop_stop()
client.disconnect()
print("[Publisher] Done.")
