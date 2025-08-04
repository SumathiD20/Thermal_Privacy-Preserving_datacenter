#!/usr/bin/env python3
from io import StringIO
import time
import json
import pandas as pd
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt
from dotenv import load_dotenv
import os

# --- Load environment variables from .env ---
load_dotenv()

# --- Configuration ---
BROKER = os.getenv('MQTT_BROKER', 'localhost')
PORT = int(os.getenv('MQTT_PORT', '1883'))
TOPIC = os.getenv('MQTT_PUB_TOPIC', 'dc/temperature/raw_encrypted')
CSV_FILE = os.getenv('CSV_FILE', 'temp_reading.csv')
SECRET_KEY_FILE = os.getenv('SECRET_KEY_FILE', 'secret.key')


# --- Utility: Encrypt a single payload (testable) ---
def encrypt_payload(data: dict, fernet: Fernet) -> bytes:
    return fernet.encrypt(json.dumps(data).encode())


# --- Utility: Load cleaned data ---
def load_clean_csv(csv_file: str) -> pd.DataFrame:
    with open(csv_file, 'r') as file:
        lines = [line for line in file if line.strip() and not line.strip().startswith('#')]
    df = pd.read_csv(StringIO(''.join(lines)))
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


# --- Main publishing function ---
def main():
    # Load Fernet key
    with open(SECRET_KEY_FILE, 'rb') as f:
        cipher = Fernet(f.read())

    # Load data
    df = load_clean_csv(CSV_FILE)

    # Setup MQTT
    client = mqtt.Client()
    print(f"[Publisher] Connecting to {BROKER}:{PORT}")
    client.connect(BROKER, PORT)
    client.loop_start()

    # Publish encrypted messages
    for _, row in df.iterrows():
        t_str = row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
        message = {
            'timestamp': t_str,
            'temperature_C': row['temperature_C']
        }

        encrypted = encrypt_payload(message, cipher)
        client.publish(TOPIC, encrypted)
        print(f"[Publisher] Sent encrypted raw → {TOPIC} @ {t_str}")
        time.sleep(1)

    client.loop_stop()
    client.disconnect()


# --- Only run if executed directly ---
if __name__ == "__main__":
    main()
