
import json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE / "dataset" / "evidence"

requests = pd.read_csv(BASE / "dataset" / "deletion_requests.csv")
identities = pd.read_csv(BASE / "dataset" / "user_identities.csv")


def contains_target(record, targets):
    """Check whether this record contains the email or user ID."""
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, (dict, list)):
                if contains_target(value, targets):
                    return True
            elif value is not None:
                if str(value).strip().lower() in targets:
                    return True

    elif isinstance(record, list):
        for item in record:
            if contains_target(item, targets):
                return True

    return False


def inspect_records(data, targets, filename):
    """Find individual dictionaries containing a matching identity."""

    if isinstance(data, dict):
        if (
            "resource_id" in data
            and contains_target(data, targets)
        ):
            print(f"\nFILE: {filename}")
            print(json.dumps(data, indent=2))

        for value in data.values():
            if isinstance(value, (dict, list)):
                inspect_records(value, targets, filename)

    elif isinstance(data, list):
        for item in data:
            inspect_records(item, targets, filename)


for _, case in requests.iterrows():

    email = str(case["email"]).strip().lower()
    case_id = case["case_id"]

    identity_rows = identities[
        identities["email"].astype(str).str.strip().str.lower() == email
    ]

    user_ids = set(
        identity_rows["user_id"].astype(str).str.strip().str.lower()
    )

    targets = {email} | user_ids

    print("\n" + "=" * 65)
    print("CASE:", case_id)
    print("EMAIL:", email)
    print("USER IDS:", user_ids)
    print("=" * 65)

    total = 0

    for path in EVIDENCE_DIR.rglob("*.json"):

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        before = total

        # Count matching resource records in this file.
        def count_matches(obj):
            count = 0

            if isinstance(obj, dict):
                if (
                    "resource_id" in obj
                    and contains_target(obj, targets)
                ):
                    count += 1

                for value in obj.values():
                    if isinstance(value, (dict, list)):
                        count += count_matches(value)

            elif isinstance(obj, list):
                for item in obj:
                    count += count_matches(item)

            return count

        total += count_matches(data)

        if total > before:
            inspect_records(data, targets, path.name)

    print("\nTOTAL MATCHING RECORDS:", total)

