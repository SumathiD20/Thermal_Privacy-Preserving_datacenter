# Mitigating Thermal Side-Channel Attacks in Data Centres: A Secure Operational Pipeline Framework for Privacy-Preserving Environmental Sensor Data

Welcome!
This repository contains the prototype code, datasets, and documentation that support the research  “Mitigating Thermal Side-Channel Attacks in Data-Centre Environments.”

## What this project does
Masks fine-grained temperature data by injecting Gaussian noise + rolling averages.

Detects tampering or unusual heat bursts using an Isolation-Forest-based anomaly detector.

Encrypts and streams sensor data over MQTT-TLS (mqtts://) so raw readings stay confidential in transit.

Runs end-to-end in a DevOps pipeline that follows ISO/IEC/IEEE 32675 practices (CI, CD, IaC, dashboards).

Maps controls to NIST SP 800-53 Rev. 5 and ISO 27001:2022 so operators can show audit compliance.

## Technology stack
Code base: Python
Machine learning: sklearn library , Algorithm: IsolationForest
Data Masking: Gaussian Noise - Numpy Library

## Quick start
1. Clone
git clone https://github.com/SumathiD20/Thermal_Privacy-Preserving_datacenter.git

## CI/CD pipeline
Push → GitHub Actions runs lint + unit tests in < 30 s.

Pull request → risk-based integration tests replay door-dip + overheating traces.

On pass → images are built, signed, and pushed to GitHub Packages.
