
import pandas as pd


def apply_policy(records, rules):
    """
    Evaluate user data against official deletion rules.

    records: User data records
    rules: Rules from deletion_rules.csv

    Returns:
        List of recommended actions
    """

    actions = []

    # Convert DataFrame into dictionaries
    if isinstance(records, pd.DataFrame):
        records = records.to_dict(orient="records")

    if isinstance(rules, pd.DataFrame):
        rules = rules.to_dict(orient="records")

    # Check every user data record
    for record in records:

        category = record.get("data_category")

        if not category:
            actions.append({
                "data_category": None,
                "action": "REVIEW",
                "reason": "Data category is missing"
            })
            continue

        # Find matching deletion rule
        matching_rules = [
            rule for rule in rules
            if rule["data_category"].upper() == category.upper()
        ]

        if not matching_rules:
            actions.append({
                "data_category": category,
                "action": "REVIEW",
                "reason": "No matching rule found"
            })
            continue

        # Apply the matching rule
        for rule in matching_rules:

            condition = str(rule["condition"]).strip()
            required_action = str(rule["required_action"]).strip().upper()

            if condition.lower() == "always":

                action = required_action
                reason = "Rule condition is Always"

            else:

                # Conditional rules need additional evidence.
                action = "REVIEW"
                reason = (
                    "Conditional rule requires checking "
                    "the record evidence"
                )

            actions.append({
                "data_category": category,
                "rule_id": rule["rule_id"],
                "condition": condition,
                "action": action,
                "reason": reason
            })

    return actions
