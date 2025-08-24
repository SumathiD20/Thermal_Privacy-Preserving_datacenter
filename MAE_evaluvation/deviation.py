import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from io import StringIO

# ---------- Load & prepare data ----------
with open('temp_reading.csv', 'r', encoding='utf-8') as f:
    lines = [ln for ln in f if ln.strip() and not ln.lstrip().startswith('#')]
df = pd.read_csv(StringIO(''.join(lines)))
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp').reset_index(drop=True)

# ---------- Train Isolation Forest on "quiet" first 10s ----------
quiet_end = df['timestamp'].iloc[0] + pd.Timedelta(seconds=10)
quiet_df = df[df['timestamp'] < quiet_end]
model = IsolationForest(contamination=0.01, random_state=42)
model.fit(quiet_df[['temperature_C']])

# ---------- Masking logic (privacy + utility guardrails) ----------
masked = []
anom_flags = []
for temp in df['temperature_C']:
    is_anom = (model.predict(pd.DataFrame([[temp]], columns=['temperature_C']))[0] == -1)
    anom_flags.append(is_anom)
    if temp >= 30.0:
        out = temp                                 # don't mask overheating
    elif is_anom:
        out = 25.0 + np.random.normal(0, 0.1)      # hide door-dip pattern
    else:
        out = temp + np.random.normal(0, 0.02)     # gentle noise on normal data
    masked.append(out)

df['masked'] = masked
df['is_anom'] = anom_flags

# ---------- Error metrics ----------
diff = df['temperature_C'] - df['masked']          # original - masked
mae = np.mean(np.abs(diff))
std = np.std(diff)

print(f"Mean Absolute Error (MAE) between original and masked readings: {mae:.3f} °C")
print(f"Standard Deviation (diff): {std:.3f} °C")

# ---------- Build a dual-panel figure ----------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

# (Top) Original vs Masked
ax1.plot(df['timestamp'], df['temperature_C'], label='Original', linewidth=1.8)
ax1.plot(df['timestamp'], df['masked'], label='Masked', linewidth=1.5)

# Mark anomalies (door dips) on the original
ax1.scatter(
    df.loc[df['is_anom'], 'timestamp'],
    df.loc[df['is_anom'], 'temperature_C'],
    marker='x', s=50, label='Detected dips', zorder=3
)

# Visual guard: overheat threshold line
ax1.axhline(30.0, linestyle='--', linewidth=1, label='Overheat threshold (30°C)')

ax1.set_ylabel('Temperature (°C)')
ax1.set_title('Original vs Masked Temperature (anomalies marked, overheat unmasked)')
ax1.legend(loc='best')

# (Bottom) Difference with ±1σ band and MAE lines
ax2.plot(df['timestamp'], diff, linewidth=1.2, label='Original - Masked')

# Shaded ±1σ
ax2.fill_between(df['timestamp'], -std, std, alpha=0.15, label=f'±1σ ({std:.2f}°C)')

# MAE reference (±MAE)
ax2.axhline(mae, linestyle='--', linewidth=1, label=f'+MAE ({mae:.2f}°C)')
ax2.axhline(-mae, linestyle='--', linewidth=1, label=f'-MAE ({mae:.2f}°C)')

ax2.set_xlabel('Time')
ax2.set_ylabel('Difference (°C)')
ax2.set_title('Masking Error Over Time with ±1σ Band')
ax2.legend(loc='best')

plt.tight_layout()
plt.show()
