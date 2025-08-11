import pandas as pd
df = pd.read_csv('latency_results.csv')
print("Samples:", len(df))
print("Mean latency (ms):", df['latency_ms'].mean())
print("p95 latency (ms):", df['latency_ms'].quantile(0.95))
print("Max latency (ms):", df['latency_ms'].max())
