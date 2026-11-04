
from data_loader import load_all_data
from identity import resolve_identity

# Load all dataset files
data = load_all_data()

requests = data["requests"]
identities = data["identities"]
audit_log = data["audit_log"]

found_count = 0
missing_count = 0
multiple_match_count = 0

missing_cases = []

# Test every deletion request
for _, request in requests.iterrows():

    profile = resolve_identity(
        request["email"],
        identities,
        audit_log
    )

    if profile["identity_found"]:
        found_count += 1
    else:
        missing_count += 1
        missing_cases.append(request["case_id"])

    if len(profile["user_ids"]) > 1:
        multiple_match_count += 1

# Display results
print("\nIDENTITY RESOLUTION TEST REPORT")
print("--------------------------------")
print("Total requests:", len(requests))
print("Identities found:", found_count)
print("Identities not found:", missing_count)
print("Requests with multiple user IDs:", multiple_match_count)

if missing_cases:
    print("\nCases with no identity match:")
    print(missing_cases)

print("\nTesting completed!")
