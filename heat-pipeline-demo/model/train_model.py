# train_model.py

import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# 1. Load the CSV, skipping any comment lines (if present)
df = pd.read_csv(
    'temp_reading.csv',
    comment='#',
    names=['timestamp','temperature_C'],
    header=0,
    parse_dates=['timestamp']
)

# 2. Use only the first 10 seconds of data as “quiet” (no door opens)
start_time = df['timestamp'].iloc[0]
quiet = df[df['timestamp'] < start_time + pd.Timedelta(seconds=10)]

# 3. Train the Isolation Forest on the baseline temperatures
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet[['temperature_C']])

# 4. Save the trained model
joblib.dump(model, 'iforest.joblib')
print("✅ Model trained and saved to iforest.joblib")
