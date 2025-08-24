# Privacy-Preserving Sensor Data Pipeline for Datacentres
Mitigating Thermal Side-Channel Attacks in Data Centres: A Secure Operational Pipeline Framework for Privacy-Preserving Environmental Sensor Data

Protect temperature data from thermal side‑channel attacks without breaking HVAC monitoring.
Pipeline: Publisher → (Encrypted MQTT) → Stream Processor → (Encrypted MQTT) → Subscriber/HVAC
Core methods: Isolation Forest (anomaly), Gaussian noise (masking), Fernet (AES+HMAC) (encryption).
DevOps: Terraform (EC2), Datadog (metrics).

## Prerequisites

Python 3.10+ on (publisher & subscriber) system
pip (Python packages)
Mosquitto MQTT broker on EC2 (or local for quick test)
Open TCP 1883 on EC2 Security Group (from publisher & subscriber IP)

Git Clone:
git clone (https://github.com/SumathiD20/Thermal_Privacy-Preserving_datacenter.git)
cd Thermal_Privacy-Preserving_datacenter

## Generate Encryption Key (Fernet)
python - << 'PY'
from cryptography.fernet import Fernet
open('secret.key','wb').write(Fernet.generate_key())
print("secret.key written")
PY

* Keep secret.key private 
Copy the same key to every component that needs to decrypt:
Publisher (local system), Stream Processor (EC2), Subscriber (local system).

## Create .env files
### publisher .env
MQTT_BROKER=<EC2_PUBLIC_IP>
MQTT_PORT=1883
MQTT_PUB_TOPIC=dc/temperature/raw_encrypted
CSV_FILE=temp_reading.csv
FERNET_KEY_FILE=secret.key

### subscriber/HVAC .env
MQTT_BROKER=<EC2_PUBLIC_IP>
MQTT_PORT=1883
MQTT_TOPIC=dc/temperature/masked_encrypted
FERNET_KEY_FILE=secret.key
PROLONGED_SEC=20
RATE_HZ=1       # set to 1 for 1Hz test; 10 for 10Hz test

### stream processor .env
BROKER=localhost
PORT=1883
RAW_TOPIC=dc/temperature/raw_encrypted
MASKED_TOPIC=dc/temperature/masked_encrypted

## Prepare Data & Model
Put the CSV (e.g., temp_reading.csv) in repo root.
### Train Isolation Forest (creates iforest.joblib):
python train_model.py

## Copy secret.key and iforest.joblib to EC2:
scp secret.key iforest.joblib ubuntu@<EC2_PUBLIC_IP>:~

## Start the System (should be in order) On EC2
sudo apt update && sudo apt install -y mosquitto
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto

## EC2: run Stream Processor
python3 stream_processor.py

## run Subscriber / HVAC (System)
python subscriber.py

## run Publisher
python publisher.py

## Troubleshooting

ConnectionRefusedError
- Broker not running or wrong IP/port.
- Check sudo systemctl status mosquitto on EC2.
- Security Group must allow 1883 from Local system IP.

Decrypt/parse error
- Keys mismatch. Ensure the same secret.key on publisher, processor, subscriber.
- Don’t edit ciphertext payloads.

sklearn feature-name warning
- Use DataFrame for predict:
- model.predict(pd.DataFrame([[temp]], columns=["temperature_C"]))

No subscriber output
- Ensure processor is publishing to dc/temperature/masked_encrypted.
- Verify topics match .env.

