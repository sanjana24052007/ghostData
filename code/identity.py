
import pandas as pd


def normalize_email(email):
    """Standardize an email address for matching."""
    if pd.isna(email):
        return ""

    return str(email).strip().lower()


def normalize_value(value):
    """Remove unnecessary spaces from a value."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def resolve_identity(request_email, identities, audit_log):
    """
    Find current and historical identifiers for a deletion request.

    Parameters:
        request_email: Email from deletion_requests.csv
        identities: DataFrame from user_identities.csv
        audit_log: DataFrame from user_audit_log.csv

    Returns:
        Dictionary containing the matched identity profile.
    """

    target_email = normalize_email(request_email)

    # Store identifiers discovered for this customer.
    user_ids = set()
    emails = set()
    names = set()
    phones = set()
    email_hashes = set()

    # 1. Find the email in current identity records.
    current_matches = identities[
        identities["email"].apply(normalize_email) == target_email
    ]

    for _, row in current_matches.iterrows():
        user_ids.add(normalize_value(row["user_id"]))

    # 2. Find the email in historical email changes.
    email_changes = audit_log[
        (audit_log["field_name"].str.strip().str.lower() == "email")
    ]

    for _, row in email_changes.iterrows():
        old_email = normalize_email(row["old_value"])
        new_email = normalize_email(row["new_value"])

        if target_email and target_email in (old_email, new_email):
            user_ids.add(normalize_value(row["user_id"]))

    user_ids.discard("")

    # 3. Expand historical user IDs if the audit log records ID changes.
    # Repeat in case an ID was changed more than once.
    changed = True

    while changed:
        changed = False

        for _, row in audit_log.iterrows():
            field = normalize_value(row["field_name"]).lower()

            if field == "user_id":
                audit_user_id = normalize_value(row["user_id"])

                if audit_user_id in user_ids:
                    for value in (row["old_value"], row["new_value"]):
                        value = normalize_value(value)

                        if value and value not in user_ids:
                            user_ids.add(value)
                            changed = True

    # 4. Collect all current identifiers for matched user IDs.
    matched_identities = identities[
        identities["user_id"].apply(normalize_value).isin(user_ids)
    ]

    for _, row in matched_identities.iterrows():
        for column, collection in [
            ("email", emails),
            ("name", names),
            ("phone", phones),
            ("email_hash", email_hashes)
        ]:
            if column in row.index:
                value = normalize_value(row[column])

                if value:
                    collection.add(value)

    # 5. Collect historical values for all matched user IDs.
    matched_history = audit_log[
        audit_log["user_id"].apply(normalize_value).isin(user_ids)
    ]

    for _, row in matched_history.iterrows():
        field = normalize_value(row["field_name"]).lower()

        old_value = normalize_value(row["old_value"])
        new_value = normalize_value(row["new_value"])

        if field == "email":
            if old_value:
                emails.add(old_value.lower())
            if new_value:
                emails.add(new_value.lower())

        elif field == "name":
            if old_value:
                names.add(old_value)
            if new_value:
                names.add(new_value)

        elif field == "phone":
            if old_value:
                phones.add(old_value)
            if new_value:
                phones.add(new_value)

        elif field == "email_hash":
            if old_value:
                email_hashes.add(old_value)
            if new_value:
                email_hashes.add(new_value)

    return {
        "requested_email": target_email,
        "user_ids": sorted(user_ids),
        "emails": sorted(emails),
        "names": sorted(names),
        "phones": sorted(phones),
        "email_hashes": sorted(email_hashes),
        "identity_found": bool(user_ids)
    }


if __name__ == "__main__":
    # Load the data using Module 1.
    from data_loader import load_all_data

    data = load_all_data()

    # Test using the first deletion request.
    first_request = data["requests"].iloc[0]

    profile = resolve_identity(
        first_request["email"],
        data["identities"],
        data["audit_log"]
    )

    print("\nIDENTITY RESOLUTION TEST")
    print("------------------------")
    print("Requested email:", profile["requested_email"])
    print("User IDs:", profile["user_ids"])
    print("Emails:", profile["emails"])
    print("Names:", profile["names"])
    print("Phones:", profile["phones"])
    print("Email hashes:", profile["email_hashes"])
    print("Identity found:", profile["identity_found"])
