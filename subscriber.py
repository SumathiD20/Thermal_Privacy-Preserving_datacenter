#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import numpy as np
import paho.mqtt.client as mqtt

# ─── Load ENV & Config ─────────────────────────────────────────────────────────
load_dotenv()

BROKER        = os.getenv('MQTT_BROKER', 'localhost')
PORT          = int(os.getenv('MQTT_PORT', '1883'))
TOPIC         = os.getenv('MQTT_TOPIC', 'dc/temperature/masked_encrypted')
KEY_FILE      = os.getenv('FERNET_KEY_FILE', 'secret.key')

SETPOINT      = 25.0
AMBIENT       = 22.0
R             = 10.0
C             = 5.0
DT            = 1.0
OVERHEAT      = 30.0
NIGHT_START   = 22
NIGHT_END     = 5
PROLONGED_SEC = int(os.getenv('PROLONGED_SEC', '20'))

# ─── Logging Setup ──────────────────────────────────────────────────────────────
console = logging.getLogger('console')
console.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('%(message)s'))
console.addHandler(ch)

protected = logging.getLogger('protected')
protected.setLevel(logging.DEBUG)
fh = logging.FileHandler('protected.log', encoding='utf-8')
fh.setFormatter(logging.Formatter(
    '%(asctime)s | Meas=%(measured).2f | Ctrl=%(control).2f | '
    'Model=%(model).2f | Anom=%(is_anom)s'
))
protected.addHandler(fh)

# ─── PID Controller ────────────────────────────────────────────────────────────
class PID:
    def __init__(self, kp, ki, kd, dt):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.dt = dt
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error):
        self.integral += error * self.dt
        derivative = (error - self.prev_error) / self.dt
        out = (self.kp * error + self.ki * self.integral + self.kd * derivative)
        self.prev_error = error
        return out

# ─── State & Init ─────────────────────────────────────────────────────────────
cipher     = Fernet(open(KEY_FILE, 'rb').read())
pid        = PID(kp=2.0, ki=0.1, kd=0.05, dt=DT)
room_temp  = None
door_start      = None
prolonged_fired = False

# ─── MQTT Callbacks ───────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    console.info(f"[Subscriber] Connected (rc={rc}) – subscribing to {TOPIC}")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global room_temp, door_start, prolonged_fired

    # Decrypt & parse
    try:
        data = json.loads(cipher.decrypt(msg.payload))
    except Exception as e:
        console.error(f"[Subscriber] Decrypt error: {e}")
        return

    t_str    = data['timestamp']
    measured = data['temperature']
    is_anom  = data.get('anomaly', False)
    t        = datetime.fromisoformat(t_str.replace('Z','+00:00'))

    # Initialize model state
    if room_temp is None:
        room_temp = measured

    # PID control & thermal model
    error   = SETPOINT - measured
    control = pid.update(error)
    dT      = (-(room_temp - AMBIENT)/(R*C) + control/C) * DT
    room_temp += dT

    # If not an anomaly, re-sync model to the masked reading
    if not is_anom:
        room_temp = measured

    # Console: core status
    console.info(f"{t.date()} {t.time()}  Masked={measured:.2f}°C  Model={room_temp:.2f}°C")

    # Alerts on console
    if measured >= OVERHEAT:
        console.info(f"\033[91m OVERHEAT at {t.time()} – {measured:.2f}°C\033[0m")

    if is_anom and (t.hour >= NIGHT_START or t.hour < NIGHT_END):
        console.info(f"\033[93m Night‐time door event at {t.time()}\033[0m")

    if is_anom:
        if door_start is None:
            door_start      = t
            prolonged_fired = False
        elif not prolonged_fired and (t - door_start) >= timedelta(seconds=PROLONGED_SEC):
            console.info(f"\033[96m Prolonged‐open since {door_start.time()}\033[0m")
            prolonged_fired = True
    else:
        door_start      = None
        prolonged_fired = False

    # Protected log: full details
    protected.debug('', extra={
        'measured': measured,
        'control':  control,
        'model':    room_temp,
        'is_anom':  is_anom
    })

# ─── Run MQTT Loop ──────────────────────────────────────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

console.info("[Subscriber] Starting HVAC loop…")
client.loop_forever()
