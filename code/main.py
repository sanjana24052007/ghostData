
import csv
import io
import re
from pathlib import Path
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"

EVIDENCE_CACHE = {}


# 1. LOAD CSV FILES
def load_csv(filename):
    path = DATASET / filename

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# 2. FIND USER IDENTITY
def find_user_by_email(email, identities):
    email = (email or "").strip().lower()

    for user in identities:
        if user.get("email", "").strip().lower() == email:
            return user

    return None


# 3. FIND RELATED SYSTEM ACTIVITIES
def find_activity_matches(user_id, email, activities):
    matches = []

    user_id = str(user_id or "").lower()
    email = str(email or "").lower()

    for activity in activities:
        activity_text = " ".join(
            str(value) for value in activity.values()
        ).lower()

        if user_id and user_id in activity_text:
            matches.append(activity)
        elif email and email in activity_text:
            matches.append(activity)

    return matches


# 4. READ AND CACHE EVIDENCE FILES
def get_evidence_content(file_path):
    if file_path in EVIDENCE_CACHE:
        return EVIDENCE_CACHE[file_path]

    possible_paths = [
        ROOT / file_path,
        DATASET / file_path
    ]

    content = ""

    for path in possible_paths:
        if path.is_file():
            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except OSError:
                content = ""
            break

    EVIDENCE_CACHE[file_path] = content
    return content


# 5. SEARCH EVIDENCE FILES FOR RESOURCE IDS
def find_resource_evidence(resource_id, evidence):
    matches = []

    if not resource_id:
        return matches

    for item in evidence:
        file_path = item.get("file_path", "")
        content = get_evidence_content(file_path)

        for line in content.splitlines():
            if resource_id in line:
                matches.append({
                    "file_path": file_path,
                    "line": line
                })

    return matches


# 6. DETECT POST-DELETION EXPORTS
def detect_post_deletion_exports(resource_ids, evidence, reported_at):
    findings = []

    if not reported_at:
        return findings

    for resource_id in resource_ids:

        evidence_matches = find_resource_evidence(
            resource_id,
            evidence
        )

        for match in evidence_matches:
            line = match["line"]

            timestamp_match = re.search(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                line
            )

            if not timestamp_match:
                continue

            event_time = timestamp_match.group(0)

            if (
                event_time > reported_at
                and "event=export_download_check_completed" in line
                and "available=true" in line
            ):
                findings.append({
                    "resource_id": resource_id,
                    "event_time": event_time,
                    "file_path": match["file_path"],
                    "evidence_line": line
                })

    return findings


# 7. INVESTIGATE ONE DELETION CASE
def audit_case(request, identities, audit_logs, activities, evidence):

    email = request.get("email", "")
    identity = find_user_by_email(email, identities)

    user_id = identity.get("user_id") if identity else ""

    audit_matches = []
    activity_matches = []
    resource_ids = []

    if user_id:

        for log in audit_logs:
            if log.get("user_id", "").strip() == str(user_id):
                audit_matches.append(log)

        activity_matches = find_activity_matches(
            user_id,
            email,
            activities
        )

        for activity in activity_matches:
            resource_id = activity.get("resource_id", "")

            if resource_id and resource_id not in resource_ids:
                resource_ids.append(resource_id)

    reported_at = request.get("reported_at", "")

    export_findings = detect_post_deletion_exports(
        resource_ids,
        evidence,
        reported_at
    )

    return {
        "identity_found": identity is not None,
        "user_id": user_id,
        "audit_events": len(audit_matches),
        "activity_references": len(activity_matches),
        "post_deletion_exports": len(export_findings),
        "export_findings": export_findings
    }


# 8. CLASSIFY RISK
def classify_risk(result):

    if not result["identity_found"]:
        return "REVIEW", "User identity could not be matched"

    elif result["post_deletion_exports"] > 0:
        return "HIGH", "Export availability detected after reported deletion"

    elif result["activity_references"] > 0:
        return "MEDIUM", "Related system activity requires investigation"

    else:
        return "LOW", "No suspicious activity found in checked evidence"


# 9. MAIN FUNCTION
def main():

    print("Ghost Data Still Exists - Audit Agent")
    print("--------------------------------------")

    requests = load_csv("deletion_requests.csv")
    identities = load_csv("user_identities.csv")
    audit_logs = load_csv("user_audit_log.csv")
    activities = load_csv("system_activity.csv")
    rules = load_csv("deletion_rules.csv")
    evidence = load_csv("evidence_files.csv")

    print("\nINPUT DATA SUMMARY")
    print("Identities:", len(identities))
    print("Deletion requests:", len(requests))
    print("Audit logs:", len(audit_logs))
    print("System activities:", len(activities))
    print("Deletion rules:", len(rules))
    print("Evidence files:", len(evidence))

    audit_results = []
    detailed_evidence = []

    high = 0
    medium = 0
    low = 0
    review = 0
    matched = 0
    activity_cases = 0
    export_cases = 0

    print("\n========== FULL AUDIT STARTED ==========")

    for request in requests:

        with redirect_stdout(io.StringIO()):
            result = audit_case(
                request,
                identities,
                audit_logs,
                activities,
                evidence
            )

        if result["identity_found"]:
            matched += 1

        if result["activity_references"] > 0:
            activity_cases += 1

        if result["post_deletion_exports"] > 0:
            export_cases += 1

        risk, reason = classify_risk(result)

        if risk == "HIGH":
            high += 1
        elif risk == "MEDIUM":
            medium += 1
        elif risk == "LOW":
            low += 1
        else:
            review += 1

        case_id = request.get("case_id", "")

        audit_results.append({
            "case_id": case_id,
            "risk_level": risk,
            "reason": reason,
            "identity_found": result["identity_found"],
            "activity_references": result["activity_references"],
            "post_deletion_exports": result["post_deletion_exports"]
        })

        # Collect detailed evidence for HIGH-risk cases
        if risk == "HIGH":

            for finding in result["export_findings"]:

                detailed_evidence.append({
                    "case_id": case_id,
                    "user_id": result["user_id"],
                    "risk_level": risk,
                    "reported_deletion_time": request.get("reported_at", ""),
                    "resource_id": finding["resource_id"],
                    "event_timestamp": finding["event_time"],
                    "evidence_file": finding["file_path"],
                    "evidence_line": finding["evidence_line"],
                    "reason": reason
                })

        if len(audit_results) % 50 == 0:
            print(
                "Progress:",
                len(audit_results),
                "/",
                len(requests)
            )

    # 10. SAVE COMPLETE AUDIT REPORT
    audit_fields = [
        "case_id",
        "risk_level",
        "reason",
        "identity_found",
        "activity_references",
        "post_deletion_exports"
    ]

    report_path = ROOT / "audit_results.csv"

    with open(report_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit_results)

    # 11. SAVE HIGH-RISK REPORT
    high_risk_cases = [
        case for case in audit_results
        if case["risk_level"] == "HIGH"
    ]

    high_report = ROOT / "high_risk_report.csv"

    with open(high_report, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(high_risk_cases)

    # 12. SAVE DETAILED EVIDENCE REPORT
    evidence_fields = [
        "case_id",
        "user_id",
        "risk_level",
        "reported_deletion_time",
        "resource_id",
        "event_timestamp",
        "evidence_file",
        "evidence_line",
        "reason"
    ]

    evidence_report = ROOT / "detailed_evidence_report.csv"

    with open(
        evidence_report,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=evidence_fields
        )

        writer.writeheader()
        writer.writerows(detailed_evidence)

    # 13. DISPLAY FINAL SUMMARY
    print("\n========== FULL AUDIT SUMMARY ==========")
    print("Total cases investigated:", len(audit_results))
    print("Users successfully matched:", matched)
    print("Cases with activity references:", activity_cases)
    print("Cases with post-deletion exports:", export_cases)

    print("\n========== RISK CLASSIFICATION ==========")
    print("HIGH:", high)
    print("MEDIUM:", medium)
    print("LOW:", low)
    print("REVIEW:", review)

    print("\n========== EVIDENCE SUMMARY ==========")
    print("Detailed evidence records:", len(detailed_evidence))

    print("\n========== REPORTS GENERATED ==========")
    print(report_path)
    print(high_report)
    print(evidence_report)

    print("\n========== AUDIT COMPLETED ==========")


if __name__ == "__main__":
    main()
