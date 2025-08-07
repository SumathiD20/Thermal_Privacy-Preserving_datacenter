import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
from io import StringIO

# 1. Load and clean the sample temperature data
with open('temp_reading.csv', 'r') as f:
    lines = [line for line in f if line.strip() and not line.strip().startswith('#')]

df = pd.read_csv(StringIO(''.join(lines)), parse_dates=['timestamp'])

# 2. Train on the first 10 seconds of data
quiet_end = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet = df[df['timestamp'] < quiet_end]

# 3. Train the Isolation Forest
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet[['temperature_C']])

# 4. Save the model
joblib.dump(model, 'iforest.joblib')
print("✅ iforest.joblib created!")
