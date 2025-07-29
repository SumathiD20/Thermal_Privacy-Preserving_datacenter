import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# 1. Load the sample temperature data
df = pd.read_csv('temp_reading.csv', parse_dates=['timestamp'])
quiet = df[df['timestamp'] < df['timestamp'].iloc[0] +
           pd.Timedelta(seconds=10)]

# 2. Train the model
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet[['temperature_C']])

# 3. Save it
joblib.dump(model, 'iforest.joblib')
print("iforest.joblib created!")
