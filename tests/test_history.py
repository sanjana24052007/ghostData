
from data_loader import load_all_data
from identity import resolve_identity

data = load_all_data()

identities = data["identities"]
audit_log = data["audit_log"]
requests = data["requests"]

checked = 0
missing_history = []

for _, request in requests.iterrows():

    profile = resolve_identity(
        request["email"],
        identities,
        audit_log
    )

    for user_id in profile["user_ids"]:

        history = audit_log[
            audit_log["user_id"].astype(str).str.strip() == user_id
        ]

        for _, row in history.iterrows():

            field = str(row["field_name"]).strip().lower()

            if field == "email":
                recovered = set(profile["emails"])
            elif field == "phone":
                recovered = set(profile["phones"])
            elif field == "email_hash":
                recovered = set(profile["email_hashes"])
            else:
                continue

            for value in [row["old_value"], row["new_value"]]:
                value = str(value).strip()

                if field == "email":
                    value = value.lower()

                if value and value not in recovered:
                    missing_history.append(
                        (user_id, field, value)
                    )

            checked += 1

print("\nHISTORICAL IDENTITY TEST")
print("------------------------")
print("History records checked:", checked)
print("Missing historical values:", len(missing_history))

if missing_history:
    print("Examples:", missing_history[:10])
else:
    print("All checked historical values were recovered!")
