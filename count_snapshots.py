from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

file_path = (
    ROOT / "dataset" / "evidence" / "records" /
    "customer_data_snapshot_bundle_20260917.json"
)

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

print("SNAPSHOT SUMMARY")
print("----------------")

total_records = 0

for index, snapshot in enumerate(data["snapshots"], start=1):

    records = snapshot.get("records", [])

    count = len(records)
    total_records += count

    print(f"\nSnapshot {index}")
    print("Captured at:", snapshot.get("captured_at"))
    print("Data store:", snapshot.get("data_store"))
    print("Collection:", snapshot.get("collection"))
    print("Number of records:", count)

print("\n----------------")
print("Total snapshots:", len(data["snapshots"]))
print("Total records:", total_records)