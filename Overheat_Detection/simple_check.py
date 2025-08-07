import csv

count = 0
with open("overheat_detection_tableau.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if float(row["masked_temperature"]) <= 21.0:
            count += 1
print("Detected Undercools in log:", count)
