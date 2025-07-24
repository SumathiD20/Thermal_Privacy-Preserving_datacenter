#!/usr/bin/env python3
import json
import time
from datetime import datetime
import numpy as np
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# — MQTT & Encryption Config —
BROKER = '54.90.99.53'    # EC2’s IP
PORT   = 1883
TOPIC  = 'dc/temperature/masked_encrypted'
KEY    = 'secret.key'

# — HVAC & Simulation Params —
SETPOINT = 25.0    # desired temp
AMBIENT  = 22.0    # outside temp
R        = 10.0    # thermal resistance
C        = 5.0     # thermal capacitance
DT       = 1.0     # loop interval (sec)
OVERHEAT = 30.0    # overheat threshold

# — Simple PID Controller — 
class PID:
    def __init__(self, kp, ki, kd, dt):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.dt = dt
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error):
        self.integral += error * self.dt
        derivative = (error - self.prev_error) / self.dt
        output = (self.kp * error +
                  self.ki * self.integral +
                  self.kd * derivative)
        self.prev_error = error
        return output

# — Load key & set up MQTT — 
cipher = Fernet(open(KEY,'rb').read())
pid = PID(kp=2.0, ki=0.1, kd=0.05, dt=DT)
room_temp = None    # will initialize on first message

def on_connect(client, userdata, flags, rc):
    print(f"[Subscriber] Connected (rc={rc}), subscribing to {TOPIC}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global room_temp

    # 1. Decrypt & parse
    try:
        decrypted = cipher.decrypt(msg.payload)
        data = json.loads(decrypted)
    except Exception as e:
        print(f"[Subscriber] Decrypt error: {e}")
        return

    t_str = data['timestamp']
    measured = data['temperature']
    is_anom = data.get('anomaly', False)
    t = datetime.fromisoformat(t_str.replace('Z','+00:00'))

    # Initialize model state
    if room_temp is None:
        room_temp = measured

    # 2. Compute control
    error = SETPOINT - measured
    control = pid.update(error)

    # 3. RC thermal model: dT = (−(T−Ta)/(R*C) + control/C)⋅dt
    dT = (-(room_temp - AMBIENT)/(R*C) + control/C) * DT
    room_temp += dT

    # 4. Print status
    print(f"[HVAC] {t.time()}  Measured={measured:.2f}°C  "
          f"Control={control:.2f}  Model={room_temp:.2f}°C  Anom={is_anom}")

    # 5. Alerts
    if measured >= OVERHEAT:
        print("⚠️  OVERHEAT ALARM!")
    if is_anom and (t.hour >= 22 or t.hour < 5):
        print("🔒  Night-time door event")

# — MQTT Client Setup — 
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("[Subscriber] Starting HVAC simulation loop…")
client.loop_forever()
