import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from io import StringIO

# 1) Load and clean CSV (ignore comments and blank lines)
with open('temp_reading.csv', 'r') as f:
    lines = [line for line in f if line.strip() and not line.strip().startswith('#')]
df = pd.read_csv(StringIO(''.join(lines)))

# 2) Parse timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 3) Train Isolation Forest on the first 10 seconds as quiet period
quiet_end = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet_df = df[df['timestamp'] < quiet_end]
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet_df[['temperature_C']])

# 4) Apply masking logic
masked = []
for temp in df['temperature_C']:
    is_anom = (model.predict(pd.DataFrame([[temp]], columns=['temperature_C']))[0] == -1)

    if temp >= 30.0 or is_anom:
        out = 25.0 + np.random.normal(0, 0.1)  # Mask anomaly  # small, realistic noise
    else:
        out = temp + np.random.normal(0, 0.02)  # Slight noise for normal data  

    masked.append(out)


df['masked'] = masked

# 5) Compute MAE
mae = np.mean(np.abs(df['temperature_C'] - df['masked']))
print(f"Mean Absolute Error (MAE) between original and masked readings: {mae:.3f} °C")

