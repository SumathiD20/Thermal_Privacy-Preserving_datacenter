# ~/heat-pipeline-demo/publisher.py
import time, json
import pandas as pd
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# 1. Load key (for local dev, copy this from SSM to secret.key in this folder)
cipher = Fernet(open('secret.key','rb').read())

# 2. Read sample data
df = pd.read_csv('temp_reading.csv', parse_dates=['timestamp'])

# 3. MQTT settings
BROKER   = '<EC2_PUBLIC_IP>'      # fill in after Terraform
PORT     = 1883
TOPIC    = 'dc/temperature/raw_encrypted'

client = mqtt.Client()
client.connect(BROKER, PORT)
client.loop_start()

for _, row in df.iterrows():
    payload = json.dumps({
        'timestamp': row['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ'),
        'temperature_C': row['temperature_C']
    }).encode()
    client.publish(TOPIC, cipher.encrypt(payload))
    print(f"[Publisher] Sent encrypted raw → {TOPIC}")
    time.sleep(1)

client.loop_stop()
client.disconnect()
