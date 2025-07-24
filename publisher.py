#!/usr/bin/env python3
import time
import json
import pandas as pd
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# — Configuration —
BROKER = '54.90.99.53'      # EC2 public IP
PORT   = 1883
TOPIC  = 'dc/temperature/raw_encrypted'
CSV_FILE = 'temp_reading.csv'  # or your 350-row sample file

# — Load encryption key —
with open('secret.key', 'rb') as f:
    cipher = Fernet(f.read())

# — Read temperature data —
df = pd.read_csv(CSV_FILE, parse_dates=['timestamp'])

# — Set up MQTT client —
client = mqtt.Client()
client.connect(BROKER, PORT)
client.loop_start()

# — Publish encrypted readings in real time —
for _, row in df.iterrows():
    t_str = row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
    message = json.dumps({
        'timestamp':       t_str,
        'temperature_C':   row['temperature_C']
    }).encode()
    encrypted = cipher.encrypt(message)
    client.publish(TOPIC, encrypted)
    print(f"[Publisher] Sent encrypted raw → {TOPIC} @ {t_str}")
    time.sleep(1)

# — Clean up —
client.loop_stop()
client.disconnect()
