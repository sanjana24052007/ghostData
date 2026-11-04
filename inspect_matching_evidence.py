
import json
from pathlib import Path
import pandas as pd
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE / "dataset" / "evidence"

requests = pd.read_csv(BASE / "dataset" / "deletion_requests.csv")
identities = pd.read_csv(BASE / "dataset" / "user_identities.csv")


# --------------------------------------------------
# 1. Check whether a JSON record contains a customer
# --------------------------------------------------

def contains_target(record, targets):

    if isinstance(record, dict):
        for value in record.values():

            if isinstance(value, (dict, list)):
                if contains_target(value, targets):
                    return True

            elif value is not None:
                text = str(value).lower()

                if any(target in text for target in targets):
                    return True

    elif isinstance(record, list):
        for item in record:
            if contains_target(item, targets):
                return True

    return False


def inspect_json_records(data, targets, filename):

    if isinstance(data, dict):

        if "resource_id" in data and contains_target(data, targets):
            print("\nJSON MATCH:", filename)
            print(json.dumps(data, indent=2, ensure_ascii=False))

        for value in data.values():
            if isinstance(value, (dict, list)):
                inspect_json_records(value, targets, filename)

    elif isinstance(data, list):
        for item in data:
            inspect_json_records(item, targets, filename)


def count_json_records(obj, targets):

    count = 0

    if isinstance(obj, dict):

        if "resource_id" in obj and contains_target(obj, targets):
            count += 1

        for value in obj.values():
            if isinstance(value, (dict, list)):
                count += count_json_records(value, targets)

    elif isinstance(obj, list):
        for item in obj:
            count += count_json_records(item, targets)

    return count


# --------------------------------------------------
# 2. Search SQL, LOG and TXT files
# --------------------------------------------------

def search_text_file(path, targets):

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return 0

    lower_content = content.lower()
    matches = []

    for target in targets:

        if not target:
            continue

        start = 0

        while True:
            position = lower_content.find(target, start)

            if position == -1:
                break

            matches.append(position)
            start = position + len(target)

    if not matches:
        return 0

    # Remove nearby duplicate matches
    matches = sorted(set(matches))
    selected = []

    for position in matches:
        if not selected or position - selected[-1] > 300:
            selected.append(position)

    print("\nTEXT MATCH:", path.name)
    print("MATCHING OCCURRENCES:", len(matches))

    # Display up to 10 useful excerpts per file
    for position in selected[:10]:

        start = max(0, position - 200)
        end = min(len(content), position + 350)

        print("\n--- Matching evidence ---")
        print(content[start:end])

    if len(selected) > 10:
        print("Additional excerpts omitted to keep output manageable.")

    return len(matches)


# --------------------------------------------------
# 3. Inspect every deletion case
# --------------------------------------------------

for _, case in requests.iterrows():

    email = str(case["email"]).strip().lower()
    case_id = str(case["case_id"]).strip()

    identity_rows = identities[
        identities["email"].astype(str).str.strip().str.lower() == email
    ]

    user_ids = set(
        identity_rows["user_id"].dropna().astype(str).str.strip().str.lower()
    )

    targets = {email} | user_ids
    targets.discard("")

    print("\n" + "=" * 75)
    print("CASE:", case_id)
    print("EMAIL:", email)
    print("USER IDS:", user_ids)
    print("=" * 75)

    json_total = 0
    sql_total = 0
    log_total = 0
    txt_total = 0

    # Inspect JSON files
    for path in EVIDENCE_DIR.rglob("*.json"):

        try:
            data = json.loads(
                path.read_text(encoding="utf-8", errors="ignore")
            )
        except Exception:
            continue

        matches = count_json_records(data, targets)

        if matches > 0:
            json_total += matches
            inspect_json_records(data, targets, path.name)

    # Inspect SQL, LOG and TXT files
    for extension in [".sql", ".log", ".txt"]:

        for path in EVIDENCE_DIR.rglob("*" + extension):

            matches = search_text_file(path, targets)

            if extension == ".sql":
                sql_total += matches

            elif extension == ".log":
                log_total += matches

            elif extension == ".txt":
                txt_total += matches

    print("\n" + "-" * 50)
    print("CASE SUMMARY:", case_id)
    print("JSON MATCHING RECORDS:", json_total)
    print("SQL MATCHES:", sql_total)
    print("LOG MATCHES:", log_total)
    print("TXT MATCHES:", txt_total)
    print("-" * 50)


print("\nEVIDENCE INSPECTION COMPLETED")
