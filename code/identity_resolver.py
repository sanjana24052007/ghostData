
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET = PROJECT_ROOT / "dataset"


def read_csv(filename):
    path = DATASET / filename

    with open(path, "r", encoding="utf-8-sig",
              newline="") as file:
        return list(csv.DictReader(file))


def resolve_identity(email, audit_at):

    identities = read_csv("user_identities.csv")
    audit_logs = read_csv("user_audit_log.csv")

    email = email.strip().lower()

    matched_users = {}

    # Search current identities
    for user in identities:
        if user["email"].strip().lower() == email:
            matched_users[user["user_id"]] = user

    # Search historical email changes
    for audit in audit_logs:
        if audit["field_name"] != "email":
            continue

        if audit["event_time"] > audit_at:
            continue

        old_email = audit["old_value"].strip().lower()
        new_email = audit["new_value"].strip().lower()

        if email == old_email or email == new_email:
            user_id = audit["user_id"]

            if user_id not in matched_users:
                matched_users[user_id] = {
                    "user_id": user_id,
                    "email": email
                }

    results = []

    for user_id, user in matched_users.items():

        identifiers = {
            "user_id": user_id,
            "current_email": user.get("email", ""),
            "name": user.get("name", ""),
            "phone": user.get("phone", ""),
            "email_hash": user.get("email_hash", ""),
            "historical_emails": [],
            "historical_phones": [],
            "audit_ids": []
        }

        # Collect historical identifiers
        for audit in audit_logs:

            if audit["user_id"] != user_id:
                continue

            if audit["event_time"] > audit_at:
                continue

            field = audit["field_name"]
            old = audit["old_value"]
            new = audit["new_value"]

            identifiers["audit_ids"].append(audit["audit_id"])

            if field == "email":
                identifiers["historical_emails"].extend(
                    [old, new]
                )

            elif field == "phone":
                identifiers["historical_phones"].extend(
                    [old, new]
                )

        # Remove duplicate identifiers
        identifiers["historical_emails"] = list(
            dict.fromkeys(identifiers["historical_emails"])
        )

        identifiers["historical_phones"] = list(
            dict.fromkeys(identifiers["historical_phones"])
        )

        results.append(identifiers)

    return results


if __name__ == "__main__":

    requests = read_csv("deletion_requests.csv")

    # Test the first three deletion requests
    for request in requests[:3]:

        print("\n" + "=" * 50)
        print("CASE:", request["case_id"])
        print("EMAIL:", request["email"])

        result = resolve_identity(
            request["email"],
            request["audit_at"]
        )

        if result:
            for user in result:
                print("\nIDENTITY FOUND:")
                print(user)
        else:
            print("No matching identity found.")

