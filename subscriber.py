#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import paho.mqtt.client as mqtt

# ─── Load ENV & Config ──────────────────────────────────────────────────
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
COLD_ALERT    = 21.0
NIGHT_START   = 22
NIGHT_END     = 5
PROLONGED_SEC = int(os.getenv('PROLONGED_SEC', '20'))

# ─── Logging Setup ──────────────────────────────────────────────────────
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

# ─── PID Controller with anti-windup & clamp ────────────────────────────
class PID:
    def __init__(self, kp, ki, kd, dt, out_min=-5.0, out_max=5.0, deadband=0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.out_min = out_min
        self.out_max = out_max
        self.deadband = deadband
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error):
        # Deadband: ignore small errors
        if abs(error) < self.deadband:
            error = 0.0
        # Proportional term
        p = self.kp * error
        # Integral term with anti-windup: only integrate if not saturated
        potential_i = self.integral + error * self.dt
        i = self.ki * potential_i
        # Derivative term
        derivative = (error - self.prev_error) / self.dt
        d = self.kd * derivative
        # Unsaturated output
        u = p + i + d
        # Clamp output
        u_clamped = max(self.out_min, min(self.out_max, u))
        # Update integral only if not clamped
        if self.out_min < u < self.out_max:
            self.integral = potential_i
        # Store for next derivative
        self.prev_error = error
        return u_clamped

# ─── State & Init ───────────────────────────────────────────────────────
cipher     = Fernet(open(KEY_FILE, 'rb').read())
pid        = PID(kp=1.0, ki=0.05, kd=0.1, dt=DT)  # tuned gains
room_temp  = None
door_start = None
prolonged_fired = False

# ─── MQTT Callbacks ─────────────────────────────────────────────────────
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

    # Resync only on normal readings
    if (not is_anom) and (measured > COLD_ALERT) and (measured < OVERHEAT):
        room_temp = measured

    # Console: core status
    console.info(f"{t.date()} {t.time()}  Masked={measured:.2f}°C  Model={room_temp:.2f}°C")

    # Alerts on console
    if measured >= OVERHEAT:
        console.info(f"\033[91m OVERHEAT at {t.time()} – {measured:.2f}°C\033[0m")
    elif measured <= COLD_ALERT:
        console.info(f"\033[96m UNDERCOOL at {t.time()} – {measured:.2f}°C (Regulating...)\033[0m")

    if is_anom and (t.hour >= NIGHT_START or t.hour < NIGHT_END):
        console.info(f"\033[93m Night‐time door event at {t.time()}\033[0m")

    if is_anom:
        if door_start is None:
            door_start = t
            prolonged_fired = False
        elif not prolonged_fired and (t - door_start) >= timedelta(seconds=PROLONGED_SEC):
            console.info(f"\033[96m Prolonged‐open since {door_start.time()}\033[0m")
            prolonged_fired = True
    else:
        door_start = None
        prolonged_fired = False

    # Protected log: full details
    protected.debug('', extra={
        'measured': measured,
        'control':  control,
        'model':    room_temp,
        'is_anom':  is_anom
    })

# ─── Run MQTT Loop ─────────────────────────────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

console.info("[Subscriber] Starting HVAC loop…")
client.loop_forever()
