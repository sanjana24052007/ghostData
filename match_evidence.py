from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"

SNAPSHOT_FILE = (
    DATASET / "evidence" / "records" /
    "customer_data_snapshot_bundle_20260917.json"
)


def load_csv(filename):
    with open(
        DATASET / filename,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))


def find_user_by_email(email, identities):
    email = email.strip().lower()

    for identity in identities:
        if identity.get("email", "").strip().lower() == email:
            return identity.get("user_id")

    return None


def search_record(value, email, user_id, field_name=""):
    matches = []

    if isinstance(value, dict):
        for key, item in value.items():
            matches.extend(
                search_record(item, email, user_id, key)
            )

    elif isinstance(value, list):
        for item in value:
            matches.extend(
                search_record(item, email, user_id, field_name)
            )

    elif isinstance(value, str):
        normalized = value.strip().lower()

        if normalized == email:
            matches.append(field_name + " (email match)")

        elif normalized == user_id.lower():
            matches.append(field_name + " (user ID match)")

        elif (
            field_name in ["document", "message_text"]
            and email in normalized
        ):
            matches.append(field_name + " (email found in text)")

    return matches


def main():
    requests = load_csv("deletion_requests.csv")
    identities = load_csv("user_identities.csv")

    with open(SNAPSHOT_FILE, "r", encoding="utf-8") as file:
        snapshot_data = json.load(file)

    target_case = next(
        (
            request for request in requests
            if request.get("case_id") == "case_33"
        ),
        None
    )

    if target_case is None:
        print("Case case_33 was not found.")
        return

    email = target_case.get("email", "")
    user_id = find_user_by_email(email, identities)

    if not user_id:
        print("Could not match the user identity.")
        return

    print("EVIDENCE MATCHING REPORT")
    print("-----------------------")
    print("Case ID:", target_case["case_id"])
    print("User identity matched:", "Yes")
    print("\nSearching evidence snapshots...\n")

    total_matches = 0

    for snapshot in snapshot_data.get("snapshots", []):

        system = snapshot.get("data_store", "Unknown")
        collection = snapshot.get("collection", "Unknown")

        for record in snapshot.get("records", []):

            matches = search_record(record, email, user_id)
            matches = search_record(record, email, user_id)

            if isinstance(record, dict):
                print("Available resource ID:", "Yes" if record.get("resource_id") else "No")

            if matches:
                total_matches += 1

                print("MATCH FOUND")
                print("System:", system)
                print("Collection:", collection)
                print("Matched fields:", ", ".join(sorted(set(matches))))
                print()

    print("-----------------------")
    print("Total matching records:", total_matches)
    print("Inspection completed.")


if __name__ == "__main__":
    main()