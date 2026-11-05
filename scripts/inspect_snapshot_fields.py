from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

file_path = (
    ROOT / "dataset" / "evidence" / "records" /
    "customer_data_snapshot_bundle_20260917.json"
)

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)

print("DETAILED SNAPSHOT FIELD INSPECTION")
print("----------------------------------")

for index, snapshot in enumerate(data["snapshots"], start=1):

    records = snapshot.get("records", [])

    print(f"\nSnapshot {index}")
    print("System:", snapshot.get("data_store"))
    print("Collection:", snapshot.get("collection"))
    print("Records:", len(records))

    all_fields = set()

    for record in records:
        if isinstance(record, dict):
            all_fields.update(record.keys())

    print("Fields found:", ", ".join(sorted(all_fields)))

    # Count records containing potentially identifying fields.
    identifier_fields = [
        "user_id",
        "resource_id",
        "customer_reference",
        "email",
        "phone",
        "full_name"
    ]

    print("Identifier field counts:")

    for field in identifier_fields:
        count = sum(
            1 for record in records
            if isinstance(record, dict) and field in record
        )

        if count > 0:
            print(f"  {field}: present in {count} record(s)")

print("\n----------------------------------")
print("Inspection completed.")