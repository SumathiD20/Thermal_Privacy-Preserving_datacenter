import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load data
df = pd.read_csv(
    'temp_reading_copy.csv',
    comment='#',
    skip_blank_lines=True,
    parse_dates=['timestamp']
)

# Sort by timestamp to avoid messy lines
df.sort_values('timestamp', inplace=True)
df.reset_index(drop=True, inplace=True)

# Train IsolationForest on first 10 seconds as “quiet” period
quiet_end = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet_df = df[df['timestamp'] < quiet_end].copy()

model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet_df[['temperature_C']])

# Generate masked values
masked = []
for temp in df['temperature_C']:
    is_anom = (model.predict([[temp]])[0] == -1)
    if temp >= 30.0:
        out = temp  # Keep high temps untouched
    elif is_anom:
        out = 25.0 + np.random.normal(0, 0.1)  # Mask anomalies
    else:
        out = temp + np.random.normal(0, 0.02)  # Slight noise
    masked.append(out)

# Create masked series aligned with df
masked_series = pd.Series(masked, index=df.index)

# Detect anomalies on original data
anomalies = model.predict(df[['temperature_C']]) == -1

# Define door open window
door_open_start = pd.to_datetime('2025-07-24T12:00:00Z')
door_open_end = pd.to_datetime('2025-07-24T12:01:05Z')

# ----------------------------- PLOT -----------------------------
plt.figure(figsize=(12, 6), dpi=100)

# Plot original temperature
plt.plot(df['timestamp'], df['temperature_C'],
         color='lightgray', linewidth=2, label='Original')

# Plot masked temperature
plt.plot(df['timestamp'], masked_series,
         color='blue', linewidth=1.5, label='Masked')

# Highlight original anomalies
plt.scatter(df['timestamp'][anomalies],
            df['temperature_C'][anomalies],
            color='red', marker='x', s=80, label='Detected Dips')

# Optional: Highlight masked anomalies (can be useful)
# plt.scatter(df['timestamp'][anomalies],
#             masked_series[anomalies],
#             color='green', marker='o', s=40, label='Masked Anomalies')

# Shade door open interval
plt.axvspan(door_open_start, door_open_end,
            color='orange', alpha=0.2, label='Door Open Window')

# Vertical lines for door event start/end
plt.axvline(door_open_start, color='orange', linestyle='--', alpha=0.6)
plt.axvline(door_open_end, color='orange', linestyle='--', alpha=0.6)

# Improve x-axis: 2-second ticks and formatting
ax = plt.gca()
ax.xaxis.set_major_locator(mdates.SecondLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.5)

# Zoom in to region of interest (optional)
plt.xlim(door_open_start - pd.Timedelta(seconds=5),
         door_open_end + pd.Timedelta(seconds=5))

# Labels, title, legend
plt.title('Original vs. Masked Temperature Readings\nRed X’s mark detected door-opening dips')
plt.xlabel('Time')
plt.ylabel('Temperature (°C)')
plt.legend(loc='upper right')
plt.tight_layout()
plt.show()
