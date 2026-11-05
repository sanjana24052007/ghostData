
import pandas as pd
import sys

# Allow Python to find risk_analyzer.py inside code/
sys.path.insert(0, "code")

from risk_analyzer import detect_risks

# Load the actual dataset files
cases = pd.read_csv("dataset/deletion_requests.csv")
identities = pd.read_csv("dataset/user_identities.csv")
activities = pd.read_csv("dataset/system_activity.csv")

# Customers we want to test
test_emails = [
    "haruka.s1838@zoho.com",
    "g.silva76@gmail.com",
    "jain.aditi@gmail.com",
    "darwish.omar@icloud.com",
    "ingrid.dahl@outlook.com",
    "kagyeman8947@fastmail.com",
    "areed1433@gmail.com"
]

for email in test_emails:

    case_rows = cases[
        cases["email"].str.lower() == email.lower()
    ]

    identity_rows = identities[
        identities["email"].str.lower() == email.lower()
    ]

    print("\n==============================")
    print("CUSTOMER:", email)
    print("==============================")

    if case_rows.empty or identity_rows.empty:
        print("Case or identity not found.")
        continue

    case = case_rows.iloc[0]
    identity = identity_rows.iloc[0]

    result = detect_risks(case, identity, activities)

    if result:
        for risk in result:
            print(risk)
    else:
        print("No linked risks detected.")

print("\n========== DEBUGGING LINKED ACTIVITIES ==========")

debug_emails = [
    "jain.aditi@gmail.com",
    "darwish.omar@icloud.com",
    "ingrid.dahl@outlook.com",
    "kagyeman8947@fastmail.com",
    "areed1433@gmail.com"
]

for email in debug_emails:

    identity_row = identities[
        identities["email"].str.lower() == email.lower()
    ]

    if identity_row.empty:
        continue

    user_id = identity_row.iloc[0]["user_id"]

    print("\nCUSTOMER:", email)
    print("USER ID:", user_id)

    linked = activities[
        (activities["event_type"] == "LINK_RESOURCE_IDENTITY") &
        (activities["details"].str.contains(
            user_id, case=False, na=False
        ))
    ]

    print("LINKED RESOURCES:")

    for _, row in linked.iterrows():
        print(row["resource_id"])

    for resource in linked["resource_id"].dropna().unique():

        related = activities[
            (activities["resource_id"] == resource) |
            (activities["details"].str.contains(
                resource, case=False, na=False
            ))
        ]

        print("\nACTIVITIES FOR:", resource)

        print(related[[
            "activity_id",
            "event_type",
            "reported_result",
            "resource_id",
            "details"
        ]].to_string(index=False))

print("\n========== CHECKING AUDIT TIMESTAMPS ==========")

for email in debug_emails:

    case_row = cases[
        cases["email"].str.lower() == email.lower()
    ]

    identity_row = identities[
        identities["email"].str.lower() == email.lower()
    ]

    if case_row.empty or identity_row.empty:
        continue

    case = case_row.iloc[0]
    user_id = identity_row.iloc[0]["user_id"]

    print("\nCUSTOMER:", email)
    print("AUDIT DATE:", case["audit_at"])

    linked = activities[
        (activities["event_type"] == "LINK_RESOURCE_IDENTITY") &
        (activities["details"].str.contains(
            user_id, case=False, na=False
        ))
    ]

    resources = linked["resource_id"].dropna().unique()

    related = activities[
        activities["resource_id"].isin(resources)
    ]

    print(related[[
        "activity_id",
        "event_time",
        "event_type",
        "reported_result",
        "resource_id"
    ]].to_string(index=False))

print("\n========== FINAL AUDIT VALIDATION ==========")

for email in test_emails:

    case = cases[
        cases["email"].str.lower() == email.lower()
    ]

    identity = identities[
        identities["email"].str.lower() == email.lower()
    ]

    if case.empty or identity.empty:
        continue

    result = detect_risks(
        case.iloc[0],
        identity.iloc[0],
        activities
    )

    print("\nCustomer:", email)
    print("Risks detected:", len(result))

    for risk in result:
        print(
            risk["risk_type"],
            "|",
            risk["severity"],
            "|",
            risk["activity_id"]
        )
