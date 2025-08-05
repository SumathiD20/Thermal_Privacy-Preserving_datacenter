# Re-run code after environment reset
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from io import StringIO

# Load the CSV again
# 1) Load and clean CSV
with open('temp_reading.csv', 'r') as f:
    lines = [line for line in f if line.strip() and not line.strip().startswith('#')]
df = pd.read_csv(StringIO(''.join(lines)))

# 2) Parse timestamps
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Train model on quiet period
quiet_end = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet_df = df[df['timestamp'] < quiet_end]
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet_df[['temperature_C']])

# Generate masked values
masked = []
for temp in df['temperature_C']:
    if temp >= 30.0:
        out = temp
    else:
        is_anom = (model.predict([[temp]])[0] == -1)
        if is_anom:
            out = 25.0 + np.random.normal(0, 0.1)
        else:
            out = temp + np.random.normal(0, 0.02)
    masked.append(out)

df['masked'] = masked

# Group into bins for k-anonymity
bin_width = 2
df['bin'] = (df['masked'] // bin_width) * bin_width
bin_counts = df['bin'].value_counts().sort_index()
k = bin_counts.min()

# Plot bin counts
plt.figure(figsize=(10, 4))
bin_counts.plot(kind='bar')
plt.axhline(y=k, color='red', linestyle='--', label=f'Min bin size = {k}')
plt.xlabel('Masked Temperature Bin (°C)')
plt.ylabel('Sample Count')
plt.title('Bin Counts for k-Anonymity Check')
plt.legend()
plt.suptitle('Masked Temperature Bin Distribution for k-Anonymity', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.show()

k
