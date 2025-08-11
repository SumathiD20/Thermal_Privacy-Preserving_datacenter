#!/usr/bin/env python3
import json
import os
from cryptography.fernet import Fernet
import paho.mqtt.publish as publish

# --- Load key ---
with open('secret.key', 'rb') as f:
    cipher = Fernet(f.read())

# --- Create a valid payload ---
payload = {
    'timestamp': '2025-07-01T12:00:00Z',
    'temperature_C': 25.0
}
message = json.dumps(payload).encode()
encrypted = cipher.encrypt(message)

# --- Corrupt the message (flip a bit) ---
tampered = bytearray(encrypted)
tampered[10] ^= 0xFF  # flip a single byte
tampered_msg = bytes(tampered)

# --- Send the tampered message ---
publish.single(
    topic='dc/temperature/raw_encrypted',
    payload=tampered_msg,
    hostname='localhost',  
    port=1883
)

print("Tampered message sent.")
