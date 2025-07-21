import time, json
import pandas as pd
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# Load encryption key
cipher = Fernet(open('secret.key','rb').read())

# Read temperature data
df = pd.read_csv('temp_reading.csv', parse_dates=['timestamp'])

# MQTT settings
BROKER   = 'processor'     # docker-compose service name
PORT     = 1883
TOPIC    = 'dc/temperature/raw_encrypted'
USERNAME = ''              # if you set auth, fill in
PASSWORD = ''

# Set up client
client = mqtt.Client()
if USERNAME:
    client.username_pw_set(USERNAME, PASSWORD)
client.connect(BROKER, PORT)
client.loop_start()

# Publish loop
for _, row in df.iterrows():
    payload = json.dumps({
        'timestamp': row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ'),
        'temperature_C': row['temperature_C']
    }).encode()
    encrypted = cipher.encrypt(payload)
    client.publish(TOPIC, encrypted)
    print(f"[Publisher] Sent to {TOPIC}")
    time.sleep(1)

client.loop_stop()
client.disconnect()
