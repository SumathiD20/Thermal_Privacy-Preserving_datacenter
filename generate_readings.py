import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Settings
np.random.seed(42)
baseline_sigma = 0.05
total = 350
start = datetime(2025, 7, 1, 21, 58, 0)

# Generate timestamps and baseline temperatures
timestamps = [start + timedelta(seconds=i) for i in range(total)]
temps = np.random.normal(25, baseline_sigma, size=total)

# Define anomaly events
door_events = [10, 45, 100, 200, 300]  # start indices for door openings
for idx in door_events:
    if idx < total:
        temps[idx] -= 1.2
    if idx+1 < total:
        temps[idx+1] -= 1.5
    if idx+2 < total:
        temps[idx+2] -= 0.8

# Overheat event
overheat_idx = 150
if overheat_idx < total:
    temps[overheat_idx] = 30.5

# Write to CSV with comments
file_path = '\Downloads\temp_reading_350.csv'
with open(file_path, 'w') as f:
    f.write("# timestamp,temperature_C\n")
    for i, (ts, temp) in enumerate(zip(timestamps, temps)):
        # Comment anomalies
        if i in door_events:
            f.write(f"# Door event start at {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        if i == overheat_idx:
            f.write(f"# Overheat event at {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        # Write data row
        f.write(f"{ts.strftime('%Y-%m-%dT%H:%M:%SZ')},{temp:.2f}\n")

# Display first 15 lines as preview
preview = []
with open(file_path) as f:
    for _ in range(15):
        preview.append(f.readline().strip())

import ace_tools as tools; tools.display_dataframe_to_user(name="Preview of 350-point CSV with Comments", dataframe=pd.DataFrame(preview, columns=["Line Preview"]))

file_path