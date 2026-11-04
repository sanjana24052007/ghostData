
import pandas as pd


def detect_risks(case, identity, activities):

    if isinstance(case, pd.Series):
        case = case.to_dict()

    if isinstance(identity, pd.Series):
        identity = identity.to_dict()

    if isinstance(activities, pd.DataFrame):
        activities = activities.to_dict(orient="records")

    email = str(identity.get("email", "")).strip().lower()
    user_id = str(identity.get("user_id", "")).strip()

    risks = []

    # Find resources belonging to this customer.
    linked_resources = set()

    for activity in activities:

        if activity.get("event_type") != "LINK_RESOURCE_IDENTITY":
            continue

        details = str(activity.get("details", "")).lower()

        if email in details or user_id.lower() in details:
            resource = str(activity.get("resource_id", "")).strip()

            if resource:
                linked_resources.add(resource)

    if not linked_resources:
        return risks

    audit_at = pd.to_datetime(
        case.get("audit_at"), utc=True, errors="coerce"
    )

    # Inspect all activities linked to this customer.
    for activity in activities:

        resource = str(activity.get("resource_id", "")).strip()
        details = str(activity.get("details", ""))
        event_type = str(activity.get("event_type", "")).upper()
        result = str(activity.get("reported_result", "")).upper()

        matched_resource = next(
            (
                item for item in linked_resources
                if item == resource or item in details
            ),
            None
        )

        if not matched_resource:
            continue

        event_time = pd.to_datetime(
            activity.get("event_time"), utc=True, errors="coerce"
        )

        if pd.isna(event_time):
            continue

        # Determine whether the activity happened before or after audit.
        if pd.notna(audit_at):
            period = (
                "HISTORICAL"
                if event_time <= audit_at
                else "POST_AUDIT"
            )
        else:
            period = "AUDIT_DATE_UNKNOWN"

        risk_type = None
        severity = "MEDIUM"
        reason = ""

        if event_type in [
            "DELETE_RECORD",
            "REDACT_RECORD",
            "ANONYMIZE_RECORD"
        ] and result in ["FAILED", "PARTIAL"]:

            risk_type = "INCOMPLETE_DELETION"
            severity = "HIGH"
            reason = f"{event_type} returned {result}."

        elif event_type == "SYNC_RECORD" and result in [
            "SUCCESS", "PARTIAL"
        ]:

            risk_type = "DATA_RESYNCHRONIZATION"
            severity = "HIGH"
            reason = "Synchronization may repopulate deleted data."

        elif event_type == "RESTORE_BACKUP" and result == "SUCCESS":

            risk_type = "BACKUP_RESTORATION"
            severity = "HIGH"
            reason = "Backup restoration may recreate deleted data."

        elif event_type == "CREATE_EXPORT" and result == "SUCCESS":

            risk_type = "EXPORTED_COPY"
            severity = "MEDIUM"
            reason = "An export was created for this resource."

        if risk_type:
            risks.append({
                "risk_type": risk_type,
                "severity": severity,
                "period": period,
                "activity_id": activity.get("activity_id"),
                "resource_id": matched_resource,
                "event_type": event_type,
                "reported_result": result,
                "event_time": str(activity.get("event_time")),
                "reason": reason
            })

    return risks
