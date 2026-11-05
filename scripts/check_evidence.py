
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"

csv_path = DATASET / "evidence_files.csv"
actual_evidence_folder = DATASET / "evidence"

with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)
    evidence_records = list(reader)

print("Evidence CSV columns:", reader.fieldnames)
print("Total evidence records:", len(evidence_records))

found = 0
missing = 0

for record in evidence_records:
    relative_path = record.get("file_path", "").strip()

    if not relative_path:
        print("Missing file path in CSV record")
        missing += 1
        continue

    full_path = DATASET / relative_path

    if full_path.is_file():
        found += 1
    else:
        missing += 1
        print("NOT FOUND:", relative_path)

print("\n----- EVIDENCE PATH CHECK -----")
print("Files found:", found)
print("Files missing:", missing)
print("Total checked:", found + missing)
