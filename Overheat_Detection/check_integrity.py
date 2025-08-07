import csv

# Configuration
RAW_FILE = "temp_reading.csv"
LOG_FILE = "overheat_detection_tableau.csv"
OVERHEAT_THRESHOLD = 30.0
UNDERCOOL_THRESHOLD = 21.0

def get_actual_events():
    """Read raw temperature readings and count actual overheat/undercool events."""
    overheat_actual = 0
    undercool_actual = 0

    with open(RAW_FILE, 'r') as f:
        reader = csv.DictReader(
            row for row in f if not row.strip().startswith('#') and row.strip()
        )
        for row in reader:
            try:
                temp = float(row['temperature_C'])
                if temp >= OVERHEAT_THRESHOLD:
                    overheat_actual += 1
                elif temp <= UNDERCOOL_THRESHOLD:
                    undercool_actual += 1
            except Exception as e:
                print(f"[WARN] Skipped line: {row} – {e}")
                continue

    return overheat_actual, undercool_actual


def get_detected_events():
    """Read logged results and count detected overheat/undercool events."""
    overheat_detected = 0
    undercool_detected = 0

    with open(LOG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                temp = float(row['masked_temperature'])
                if temp >= OVERHEAT_THRESHOLD:
                    overheat_detected += 1
                elif temp <= UNDERCOOL_THRESHOLD:
                    undercool_detected += 1
            except Exception as e:
                print(f"[WARN] Skipped log line: {row} – {e}")
                continue

    return overheat_detected, undercool_detected


def main():
    overheat_actual, undercool_actual = get_actual_events()
    overheat_detected, undercool_detected = get_detected_events()

    GREEN = "\033[92m"
    RESET = "\033[0m"

    print("\n******** Integrity Check: Overheat & Undercool Detection ********")
    print("====================================================================")
    print(f"Actual Overheat Readings (≥ {OVERHEAT_THRESHOLD}°C):     {overheat_actual}")
    print(f"Detected Overheat in Log:                              {overheat_detected}")
    if overheat_actual:
        rate = overheat_detected / overheat_actual * 100
        print(f"→ Overheat Detection Rate:                             {GREEN}{rate:.2f}%{RESET}")

    print(f"\nActual Undercool Readings (≤ {UNDERCOOL_THRESHOLD}°C):   {undercool_actual}")
    print(f"Detected Undercool in Log:                            {undercool_detected}")
    if undercool_actual:
        rate = undercool_detected / undercool_actual * 100
        print(f"→ Undercool Detection Rate:                           {GREEN}{rate:.2f}%{RESET}")


if __name__ == "__main__":
    main()
