#!/usr/bin/env python3
from io import StringIO
import time
import json
import pandas as pd
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os
# Load from .env in the current directory
load_dotenv()

# — Configuration —
# BROKER = '54.91.39.188'      # EC2 public IP
# PORT   = 1883
# TOPIC  = 'dc/temperature/raw_encrypted'
# CSV_FILE = 'temp_reading.csv'
BROKER = os.getenv('MQTT_BROKER', 'localhost')
PORT = int(os.getenv('MQTT_PORT', '1883'))
TOPIC = os.getenv('MQTT_PUB_TOPIC', 'dc/temperature/raw_encrypted')
CSV_FILE = os.getenv('CSV_FILE', 'temp_reading.csv')

# — Load encryption key —
with open('secret.key', 'rb') as f:
    cipher = Fernet(f.read())

# — Read temperature data, skipping blank lines or comments —
with open(CSV_FILE, 'r') as file:
    lines = [line for line in file if line.strip(
    ) and not line.strip().startswith('#')]

# Read the cleaned data into DataFrame and parse timestamp column
df = pd.read_csv(StringIO(''.join(lines)))
df['timestamp'] = pd.to_datetime(df['timestamp'])

# — Set up MQTT client —
client = mqtt.Client()
client.connect(BROKER, PORT)
client.loop_start()

# — Publish encrypted readings in real time —
for _, row in df.iterrows():
    t_str = row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
    message = json.dumps({
        'timestamp': t_str,
        'temperature_C': row['temperature_C']
    }).encode()

    encrypted = cipher.encrypt(message)
    client.publish(TOPIC, encrypted)
    print(f"[Publisher] Sent encrypted raw → {TOPIC} @ {t_str}")
    time.sleep(1)

# — Clean up —
client.loop_stop()
client.disconnect()
