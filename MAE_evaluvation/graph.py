import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

# Step 1: Read temperature data, ignoring comments
df = pd.read_csv(
    'temp_reading.csv',
    comment='#', 
    parse_dates=['timestamp'],
    skip_blank_lines=True
)

# Step 2: Train IsolationForest on the initial quiet period (first 10 seconds)
quiet_period = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet_df = df[df['timestamp'] <= quiet_period].copy()

model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet_df[['temperature_C']])

# Step 3: Apply masking logic
masked = []
for temp in df['temperature_C']:
    is_anom = (model.predict([[temp]])[0] == -1)

    if temp >= 30.0 or is_anom:
        masked_temp = 25.0 + np.random.normal(0, 0.1)
    else:
        masked_temp = temp + np.random.normal(0, 0.02)

    masked.append(masked_temp)

df['masked_temperature_C'] = masked

# Remove timezone information (fix for Excel export)
df['timestamp'] = df['timestamp'].dt.tz_localize(None)

# Step 4: Output results to Excel
output_file = 'masked_temperatures.xlsx'
df.to_excel(output_file, index=False)

print(f"✅ Masked data saved successfully to '{output_file}'")
