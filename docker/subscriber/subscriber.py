import json
from datetime import datetime
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# Config
KEY_PATH  = 'secret.key'
BROKER    = 'processor'
PORT      = 1883
TOPIC     = 'dc/temperature/masked_encrypted'
OVERHEAT  = 30.0
night_ct  = 0

cipher = Fernet(open(KEY_PATH,'rb').read())

def on_connect(c, u, flags, rc):
    print("[Subscriber] Connected")
    c.subscribe(TOPIC)

def on_message(c, u, msg):
    print(f"[Subscriber] Msg on {msg.topic}")
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        print("Decrypt error:", e)
        return

    t = datetime.fromisoformat(data['timestamp'].replace('Z','+00:00'))
    temp = data['temperature']
    anom = data.get('anomaly', False)

    print(f"[COOLING] {t.time()} → {temp:.2f}°C (anom={anom})")
    if temp >= OVERHEAT:
        print("⚠️ OVERHEAT!")
    if anom and (t.hour>=22 or t.hour<5):
        global night_ct
        night_ct+=1
        print(f"🔒 Night open #{night_ct}")
        if night_ct>=3:
            print("🚨 VERY STRANGE!")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_forever()
