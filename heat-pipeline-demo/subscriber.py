# ~/heat-pipeline-demo/subscriber.py
import json
from datetime import datetime
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

cipher = Fernet(open('secret.key','rb').read())
BROKER   = '<EC2_PUBLIC_IP>'      # same as above
PORT     = 1883
TOPIC    = 'dc/temperature/masked_encrypted'
OVERHEAT = 30.0
night_ct = 0

def on_connect(c, u, flags, rc):
    print("[Subscriber] Connected, subscribing…")
    c.subscribe(TOPIC)

def on_message(c, u, msg):
    data = json.loads(cipher.decrypt(msg.payload))
    t = datetime.fromisoformat(data['timestamp'].replace('Z','+00:00'))
    temp = data['temperature']; anom = data['anomaly']
    print(f"[COOL] {t.time()} → {temp:.2f}°C (anom={anom})")
    if temp >= OVERHEAT:
        print("⚠️ OVERHEAT ALARM")
    if anom and (t.hour>=22 or t.hour<5):
        global night_ct; night_ct+=1
        print(f"🔒 Night open #{night_ct}")
        if night_ct>=3:
            print("🚨 VERY STRANGE!")

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()
