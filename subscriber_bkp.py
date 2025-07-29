#!/usr/bin/env python3
import json
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import numpy as np
import paho.mqtt.client as mqtt
load_dotenv()  # this will look for a .env

# — MQTT & Encryption Config via ENV VARS —
BROKER = os.getenv('MQTT_BROKER', 'localhost')
PORT = int(os.getenv('MQTT_PORT', '1883'))
TOPIC = os.getenv('MQTT_TOPIC', 'dc/temperature/masked_encrypted')
KEY = os.getenv('FERNET_KEY_FILE', 'secret.key')


# — HVAC & Simulation Params —
SETPOINT = 25.0    # °C
AMBIENT = 22.0    # °C
R = 10.0    # thermal resistance
C = 5.0     # thermal capacitance
DT = 1.0     # loop interval (s)
OVERHEAT = 30.0    # °C
NIGHT_START = 22      # 22:00
NIGHT_END = 5       # 05:00
PROLONGED_SEC = 20      # s

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


# — Load key & init objects —
cipher = Fernet(open(KEY, 'rb').read())
pid = PID(kp=2.0, ki=0.1, kd=0.05, dt=DT)
room_temp = None

# — State for prolonged-open —
door_start = None
prolonged_fired = False


def on_connect(client, userdata, flags, rc):
    print(f"[Subscriber] Connected (rc={rc}) – subscribing to {TOPIC}")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    global room_temp, door_start, prolonged_fired

    # 1. Decrypt & parse
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        print(f"[Subscriber] Decrypt error: {e}")
        return

    t_str = data['timestamp']
    measured = data['temperature']
    is_anom = data.get('anomaly', False)
    t = datetime.fromisoformat(t_str.replace('Z', '+00:00'))

    # Initialize model state
    if room_temp is None:
        room_temp = measured

    # 2. PID control
    error = SETPOINT - measured
    control = pid.update(error)

    # 3. RC thermal model
    dT = (-(room_temp - AMBIENT) / (R * C) + control / C) * DT
    room_temp += dT

    # 4. Alerts

    # Overheat
    if measured >= OVERHEAT:
        print(
            f"\033[91m OVERHEAT at {
                t.time()} – measured {
                measured:.2f}°C\033[0m")

    # Night-time door
    if is_anom and (t.hour >= NIGHT_START or t.hour < NIGHT_END):
        print(f"\033[93m Night-door at {t.time()}\033[0m")

    # Prolonged-open
    if is_anom:
        if door_start is None:
            door_start = t
            prolonged_fired = False
        elif not prolonged_fired and (t - door_start) >= timedelta(seconds=PROLONGED_SEC):
            print(f"\033[96m Prolonged-open since {door_start.time()}\033[0m")
            prolonged_fired = True
    else:
        door_start = None
        prolonged_fired = False

    # 5. Full status line
    print(
        f"[HVAC] {
            t.time()}  Measured={
            measured:.2f}°C  Controlled={
                control:.2f}  " f"Model={
                    room_temp:.2f}°C  Anomaly_Detected={is_anom}")


# — MQTT Client Setup —
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("[Subscriber] Starting HVAC loop…")
client.loop_forever()
