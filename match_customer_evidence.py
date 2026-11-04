
import os
import json
import pandas as pd

# Load customer requests and identities
requests = pd.read_csv("dataset/deletion_requests.csv")
identities = pd.read_csv("dataset/user_identities.csv")

evidence_folder = "dataset/evidence/records"


def contains_value(data, target):
    """Search nested dictionaries and lists for a customer value."""

    if isinstance(data, dict):
        return any(
            contains_value(value, target)
            for value in data.values()
        )

    if isinstance(data, list):
        return any(
            contains_value(item, target)
            for item in data
        )

    if isinstance(data, str):
        return data.strip().lower() == target.strip().lower()

    return False


for _, request in requests.iterrows():

    email = str(request["email"]).strip().lower()

    identity_rows = identities[
        identities["email"].astype(str).str.lower() == email
    ]

    if identity_rows.empty:
        print("\nNo identity found for:", email)
        continue

    user_id = str(identity_rows.iloc[0]["user_id"]).strip()

    print("\n" + "=" * 75)
    print("CASE:", request["case_id"])
    print("EMAIL:", email)
    print("USER ID:", user_id)
    print("=" * 75)

    found = 0

    for filename in sorted(os.listdir(evidence_folder)):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(evidence_folder, filename)

        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        def search_records(obj, location="root"):

            nonlocal_found = 0

            if isinstance(obj, dict):

                # Check whether this complete record belongs
                # to the requested customer.
                email_match = contains_value(obj, email)
                user_match = contains_value(obj, user_id)

                if email_match or user_match:
                    print("\nFILE:", filename)
                    print("LOCATION:", location)
                    print(json.dumps(obj, indent=2))
                    return 1

                for key, value in obj.items():
                    nonlocal_found += search_records(
                        value, location + "/" + key
                    )

            elif isinstance(obj, list):

                for index, item in enumerate(obj):
                    nonlocal_found += search_records(
                        item, location + f"[{index}]"
                    )

            return nonlocal_found

        found += search_records(data)

    print("\nTOTAL MATCHING RECORDS:", found)
