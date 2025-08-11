import pandas as pd
import matplotlib.pyplot as plt

# Load CSV
df = pd.read_csv('latency_results.csv')

# Separate by rate
df1 = df[df['rate_hz'] == 1]
df10 = df[df['rate_hz'] == 10]

plt.figure(figsize=(10,5))
plt.hist(df1['latency_ms'], bins=20, alpha=0.6, label='1 Hz', color='skyblue', edgecolor='black')
plt.hist(df10['latency_ms'], bins=20, alpha=0.6, label='10 Hz', color='orange', edgecolor='black')

plt.axvline(df1['latency_ms'].mean(), color='blue', linestyle='--', label=f"1Hz Mean = {df1['latency_ms'].mean():.1f} ms")
plt.axvline(df10['latency_ms'].mean(), color='red', linestyle='--', label=f"10Hz Mean = {df10['latency_ms'].mean():.1f} ms")

plt.title("End-to-End Latency Distribution (1Hz vs 10Hz)")
plt.xlabel("Latency (ms)")
plt.ylabel("Number of Messages")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
