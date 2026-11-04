
from data_loader import load_all_data
from identity import resolve_identity

data = load_all_data()

identities = data["identities"]
audit_log = data["audit_log"]

email_history = audit_log[
    audit_log["field_name"].str.strip().str.lower() == "email"
]

tested = 0
passed = 0
failed = []

for _, row in email_history.iterrows():

    old_email = str(row["old_value"]).strip().lower()
    expected_user_id = str(row["user_id"]).strip()

    if not old_email:
        continue

    profile = resolve_identity(
        old_email,
        identities,
        audit_log
    )

    tested += 1

    if expected_user_id in profile["user_ids"]:
        passed += 1
    else:
        failed.append({
            "email": old_email,
            "expected": expected_user_id,
            "found": profile["user_ids"]
        })

print("\nOLD EMAIL MATCHING TEST")
print("-----------------------")
print("Emails tested:", tested)
print("Correct matches:", passed)
print("Failed matches:", len(failed))

if failed:
    print("Examples:", failed[:5])
