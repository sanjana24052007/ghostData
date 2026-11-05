
import csv
import re
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"

EVIDENCE_CACHE = {}

TEXT_EXTENSIONS = {
    ".log", ".txt", ".json", ".csv", ".sql", ".xml"
}


# --------------------------------------------------
# 1. LOAD CSV FILES
# --------------------------------------------------

def load_csv(filename):
    path = DATASET / filename

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# 2. TIMESTAMP HELPERS
# --------------------------------------------------

def parse_timestamp(value):
    if not value:
        return None

    try:
        value = str(value).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None


def is_after(event_time, reference_time):
    event = parse_timestamp(event_time)
    reference = parse_timestamp(reference_time)

    return (
        event is not None
        and reference is not None
        and event > reference
    )


# --------------------------------------------------
# 3. EXACT IDENTIFIER MATCHING
# --------------------------------------------------

def contains_exact_identifier(text, identifier, is_email=False):
    if not text or not identifier:
        return False

    if is_email:
        # Prevent matching g.silva76@gmail.com
        # inside g.silva76.jr@gmail.com.
        pattern = (
            r"(?<![a-z0-9._%+\-])"
            + re.escape(identifier)
            + r"(?![a-z0-9._%+\-])"
        )
    else:
        pattern = (
            r"(?<![a-z0-9_])"
            + re.escape(identifier)
            + r"(?![a-z0-9_])"
        )

    return re.search(pattern, str(text), re.IGNORECASE) is not None


def activity_contains_identity(activity, user_id, email):
    activity_text = " ".join(
        str(value) for value in activity.values()
    )

    user_match = contains_exact_identifier(
        activity_text, user_id
    )

    email_match = contains_exact_identifier(
        activity_text, email, is_email=True
    )

    return user_match or email_match


# --------------------------------------------------
# 4. FIND USER IDENTITY
# --------------------------------------------------

def find_user_by_email(email, identities):
    email = (email or "").strip().lower()

    for user in identities:
        identity_email = (
            user.get("email", "").strip().lower()
        )

        if identity_email == email:
            return user

    return None


# --------------------------------------------------
# 5. FIND ACTIVITIES LINKED TO A USER
# --------------------------------------------------

def find_activity_matches(user_id, email, activities):
    """
    First identify activities containing the exact user ID/email.
    Then collect other activities connected to the resources
    identified by those activities.
    """

    direct_matches = []

    for activity in activities:

        if activity_contains_identity(
            activity, user_id, email
        ):
            direct_matches.append(activity)

    linked_resource_ids = {
        activity.get("resource_id", "").strip()
        for activity in direct_matches
        if activity.get("resource_id", "").strip()
    }

    matches = []
    seen_activity_ids = set()

    for activity in activities:

        activity_id = activity.get("activity_id", "").strip()
        resource_id = activity.get("resource_id", "").strip()

        directly_linked = activity_contains_identity(
            activity, user_id, email
        )

        resource_linked = (
            resource_id in linked_resource_ids
            and bool(resource_id)
        )

        if directly_linked or resource_linked:

            unique_key = activity_id or repr(sorted(activity.items()))

            if unique_key not in seen_activity_ids:
                matches.append(activity)
                seen_activity_ids.add(unique_key)

    return matches


# --------------------------------------------------
# 6. READ AND CACHE EVIDENCE FILES
# --------------------------------------------------

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
                    encoding="utf-8-sig",
                    errors="ignore"
                )

            except OSError:
                content = ""

            break

    EVIDENCE_CACHE[file_path] = content

    return content


# --------------------------------------------------
# 7. FIND RESOURCE EVIDENCE
# --------------------------------------------------

def find_resource_evidence(resource_id, evidence):

    matches = []

    if not resource_id:
        return matches

    for item in evidence:

        file_path = item.get("file_path", "").strip()

        if not file_path:
            continue

        content = get_evidence_content(file_path)

        for line_number, line in enumerate(
            content.splitlines(), start=1
        ):

            if contains_exact_identifier(line, resource_id):

                matches.append({
                    "file_path": file_path,
                    "line": line,
                    "line_number": line_number
                })

    return matches


# --------------------------------------------------
# 8. DETECT POST-DELETION EXPORTS
# --------------------------------------------------

def detect_post_deletion_exports(
    resource_ids,
    evidence,
    reported_at
):

    findings = []
    seen_events = set()

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

            if not is_after(event_time, reported_at):
                continue

            if (
                "event=export_download_check_completed" not in line
                or "available=true" not in line
            ):
                continue

            unique_key = (
                resource_id,
                event_time,
                line
            )

            if unique_key in seen_events:
                continue

            seen_events.add(unique_key)

            findings.append({
                "resource_id": resource_id,
                "event_time": event_time,
                "file_path": match["file_path"],
                "evidence_line": line,
                "evidence_type": "EXPORT_AVAILABLE"
            })

    return findings


# --------------------------------------------------
# 9. DETECT SUSPICIOUS POST-DELETION ACTIVITIES
# --------------------------------------------------

def detect_suspicious_activities(
    activity_matches,
    reported_at
):

    findings = []

    for activity in activity_matches:

        event_time = activity.get("event_time", "")

        # Ignore activities before or at reported deletion time.
        if not is_after(event_time, reported_at):
            continue

        event_type = (
            activity.get("event_type", "").strip().upper()
        )

        reported_result = (
            activity.get("reported_result", "").strip().upper()
        )

        details = activity.get("details", "")

        resource_id = activity.get("resource_id", "")

        reason = ""
        severity = ""

        # Failed or partial deletion after reported completion.
        if (
            event_type == "DELETE_RECORD"
            and reported_result in {"FAILED", "PARTIAL"}
        ):

            reason = (
                "Deletion operation failed or was partial "
                "after the reported deletion date"
            )

            severity = "HIGH"

        # Successful downstream data repopulation.
        elif (
            event_type == "SYNC_RECORD"
            and reported_result == "SUCCESS"
            and re.search(
                r"\b(repopulat\w*|restor\w*|recreat\w*)\b",
                details,
                re.IGNORECASE
            )
        ):

            reason = (
                "Successful synchronization may have "
                "repopulated a downstream resource"
            )

            severity = "HIGH"

        # Identity linkage after reported deletion.
        elif event_type == "LINK_RESOURCE_IDENTITY":

            reason = (
                "Resource identity linkage persisted "
                "after the reported deletion date"
            )

            severity = "MEDIUM"

        if severity:

            findings.append({
                "activity_id": activity.get("activity_id", ""),
                "resource_id": resource_id,
                "event_time": event_time,
                "event_type": event_type,
                "reported_result": reported_result,
                "reason": reason,
                "severity": severity,
                "evidence_line": (
                    f"activity_id={activity.get('activity_id', '')} "
                    f"event_time={event_time} "
                    f"event_type={event_type} "
                    f"resource_id={resource_id} "
                    f"reported_result={reported_result} "
                    f"details={details}"
                )
            })

    return findings


# --------------------------------------------------
# 10. FIND RELEVANT EVIDENCE SOURCES
# --------------------------------------------------

def find_relevant_evidence_sources(
    request,
    user_id,
    activity_matches,
    evidence,
    verified_findings
):

    email = request.get("email", "").strip()

    identifiers = set()

    if email:
        identifiers.add(email)

    if user_id:
        identifiers.add(str(user_id).strip())

    for activity in activity_matches:

        resource_id = activity.get("resource_id", "").strip()

        if resource_id:
            identifiers.add(resource_id)

    matched_sources = []

    for item in evidence:

        relative_path = item.get("file_path", "").strip()

        if not relative_path:
            continue

        if Path(relative_path).suffix.lower() not in TEXT_EXTENSIONS:
            continue

        content = get_evidence_content(relative_path)

        if not content:
            continue

        found = False

        for identifier in identifiers:

            is_email = (
                "@" in identifier
            )

            if contains_exact_identifier(
                content,
                identifier,
                is_email=is_email
            ):
                found = True
                break

        if found and relative_path not in matched_sources:
            matched_sources.append(relative_path)

    # Add files that contain verified findings.
    for finding in verified_findings:

        source = finding.get("file_path", "")

        if source and source not in matched_sources:
            matched_sources.append(source)

    # The activity dataset is also a source when
    # suspicious linked activity has been verified.
    if verified_findings:
        source = "dataset/system_activity.csv"

        if source not in matched_sources:
            matched_sources.append(source)

    return matched_sources


# --------------------------------------------------
# 11. CLASSIFY RISK
# --------------------------------------------------


def classify_risk(result):

    if not result["identity_found"]:
        return (
            "REVIEW",
            "User identity could not be matched"
        )

    findings = result["verified_findings"]

    # Export availability is always HIGH priority.
    high_findings = [
        finding for finding in findings
        if (
            finding.get("severity") == "HIGH"
            or finding.get("evidence_type") == "EXPORT_AVAILABLE"
        )
    ]

    if high_findings:

        reasons = sorted({
            finding.get(
                "reason",
                "Export availability detected after reported deletion"
            )
            for finding in high_findings
        })

        return (
            "HIGH",
            "; ".join(reasons)
        )

    medium_findings = [
        finding for finding in findings
        if finding.get("severity") == "MEDIUM"
    ]

    if medium_findings:
        return (
            "MEDIUM",
            "Identity linkage or related resource activity "
            "persisted after reported deletion"
        )

    return (
        "LOW",
        "No verified suspicious post-deletion evidence "
        "found in the checked records"
    )


# --------------------------------------------------
# 12. CALCULATE RISK SCORE
# --------------------------------------------------

def calculate_case_score(result):

    if not result["identity_found"]:
        return None

    findings = result["verified_findings"]

    if result["post_deletion_exports"] > 0:
        return 95

    if any(
        finding["severity"] == "HIGH"
        for finding in findings
    ):
        return 85

    if any(
        finding["severity"] == "MEDIUM"
        for finding in findings
    ):
        return 55

    return 10


# --------------------------------------------------
# 13. INVESTIGATE ONE DELETION CASE
# --------------------------------------------------

def audit_case(
    request,
    identities,
    audit_logs,
    activities,
    evidence
):

    email = request.get("email", "").strip()

    identity = find_user_by_email(
        email,
        identities
    )

    user_id = (
        identity.get("user_id", "")
        if identity else ""
    )

    audit_matches = []
    activity_matches = []

    if user_id:

        for log in audit_logs:

            log_user_id = (
                log.get("user_id", "").strip()
            )

            if log_user_id.lower() == str(user_id).lower():
                audit_matches.append(log)

        activity_matches = find_activity_matches(
            user_id,
            email,
            activities
        )

    reported_at = request.get("reported_at", "")

    # Collect resources from identity-linked activities.
    resource_ids = list(dict.fromkeys(
        activity.get("resource_id", "").strip()
        for activity in activity_matches
        if activity.get("resource_id", "").strip()
    ))

    # Find post-deletion export availability.
    export_findings = detect_post_deletion_exports(
        resource_ids,
        evidence,
        reported_at
    )

    # Find suspicious system activities.
    activity_findings = detect_suspicious_activities(
        activity_matches,
        reported_at
    )

    verified_findings = []

    verified_findings.extend(export_findings)
    verified_findings.extend(activity_findings)

    # Remove duplicate findings.
    unique_findings = []
    seen_findings = set()

    for finding in verified_findings:

        key = (
            finding.get("resource_id", ""),
            finding.get("event_time", ""),
            finding.get("evidence_type", finding.get("event_type", ""))
        )

        if key not in seen_findings:
            unique_findings.append(finding)
            seen_findings.add(key)

    verified_findings = unique_findings

    evidence_sources = find_relevant_evidence_sources(
        request,
        user_id,
        activity_matches,
        evidence,
        verified_findings
    )

    return {
        "identity_found": identity is not None,
        "user_id": user_id,
        "audit_events": len(audit_matches),

        # Total linked activity is retained for transparency.
        "activity_references": len(activity_matches),

        "activity_matches": activity_matches,

        "post_deletion_exports": len(export_findings),

        "export_findings": export_findings,

        "activity_findings": activity_findings,

        "verified_findings": verified_findings,

        "evidence_sources": evidence_sources
    }


# --------------------------------------------------
# 14. MAIN FUNCTION
# --------------------------------------------------

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

        risk_score = calculate_case_score(result)

        if risk == "HIGH":
            high += 1
        elif risk == "MEDIUM":
            medium += 1
        elif risk == "LOW":
            low += 1
        else:
            review += 1

        case_id = request.get("case_id", "")

        findings = result["verified_findings"]

        # Prioritize export findings, then other high findings.
        prioritized_findings = sorted(
            findings,
            key=lambda finding: (
                finding.get("evidence_type") != "EXPORT_AVAILABLE",
                finding.get("severity") != "HIGH",
                finding.get("event_time", "")
            )
        )

        primary_finding = (
            prioritized_findings[0]
            if prioritized_findings else {}
        )

        resource_id = primary_finding.get("resource_id", "")

        if not resource_id and result["activity_matches"]:
            resource_id = result["activity_matches"][0].get(
                "resource_id", ""
            )

        if resource_id.startswith("export_"):
            resource_type = "Export"
        elif resource_id.startswith("search_"):
            resource_type = "Search resource"
        elif resource_id.startswith("data_flow_"):
            resource_type = "Data flow"
        elif resource_id.startswith("account_"):
            resource_type = "Account resource"
        elif resource_id:
            resource_type = "Other resource"
        else:
            resource_type = "Not available"

        detection_date = primary_finding.get("event_time", "")

        evidence_sources = result["evidence_sources"]

        evidence_source = (
            ", ".join(evidence_sources)
            if evidence_sources
            else "No matching evidence found"
        )

        if risk == "HIGH":
            action = (
                "Immediately investigate the retained or "
                "repopulated resource, verify deletion, and "
                "restrict access where appropriate."
            )

        elif risk == "MEDIUM":
            action = (
                "Investigate the remaining identity linkage "
                "and confirm whether the associated resource "
                "still contains personal data."
            )

        elif risk == "REVIEW":
            action = (
                "Verify the user's identity before proceeding "
                "with the deletion audit."
            )

        else:
            action = (
                "No suspicious post-deletion evidence was found "
                "in the checked records. Continue routine monitoring."
            )

        audit_results.append({

            "case_id": case_id,

            "user_id": (
                result["user_id"]
                or "Not available"
            ),

            "deletion_request_date": request.get(
                "requested_at", ""
            ),

            "reported_deletion_date": request.get(
                "reported_at", ""
            ),

            "detection_date": (
                detection_date or "Not available"
            ),

            "resource_id": (
                resource_id or "Not available"
            ),

            "resource_type": resource_type,

            "risk_level": risk,

            "risk_score": (
                risk_score
                if risk_score is not None
                else "N/A"
            ),

            "reason": reason,

            "identity_found": result["identity_found"],

            "activity_references": result["activity_references"],

            "post_deletion_exports": result["post_deletion_exports"],

            "evidence_source": evidence_source,

            "recommended_action": action
        })

        # Save all verified HIGH-risk evidence,
        # including activity-based findings.
        if risk == "HIGH":

            for finding in findings:

                if finding.get("evidence_type") == "EXPORT_AVAILABLE":

                    evidence_file = finding["file_path"]
                    evidence_line = finding["evidence_line"]

                else:

                    evidence_file = "dataset/system_activity.csv"
                    evidence_line = finding["evidence_line"]

                detailed_evidence.append({

                    "case_id": case_id,

                    "user_id": result["user_id"],

                    "risk_level": risk,

                    "reported_deletion_time": request.get(
                        "reported_at", ""
                    ),

                    "resource_id": finding.get(
                        "resource_id", ""
                    ),

                    "event_timestamp": finding.get(
                        "event_time", ""
                    ),

                    "evidence_file": evidence_file,

                    "evidence_line": evidence_line,

                    "reason": finding.get(
                        "reason", reason
                    )
                })

        if len(audit_results) % 50 == 0:

            print(
                "Progress:",
                len(audit_results),
                "/",
                len(requests)
            )

    # --------------------------------------------------
    # 15. SAVE COMPLETE AUDIT REPORT
    # --------------------------------------------------

    audit_fields = [
        "case_id",
        "user_id",
        "deletion_request_date",
        "reported_deletion_date",
        "detection_date",
        "resource_id",
        "resource_type",
        "risk_level",
        "risk_score",
        "reason",
        "identity_found",
        "activity_references",
        "post_deletion_exports",
        "evidence_source",
        "recommended_action"
    ]
    RESULTS_DIR = ROOT / "results"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "audit_results.csv"

    with open(
        report_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=audit_fields
        )

        writer.writeheader()
        writer.writerows(audit_results)

    # --------------------------------------------------
    # 16. SAVE HIGH-RISK REPORT
    # --------------------------------------------------

    high_risk_cases = [
        case for case in audit_results
        if case["risk_level"] == "HIGH"
    ]

    high_report = ROOT / "results" / "high_risk_report.csv"

    with open(
        high_report,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=audit_fields
        )

        writer.writeheader()
        writer.writerows(high_risk_cases)

    # --------------------------------------------------
    # 17. SAVE DETAILED EVIDENCE REPORT
    # --------------------------------------------------

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

    evidence_report = ROOT / "results" / "detailed_evidence_report.csv"

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

    # --------------------------------------------------
    # 18. DISPLAY FINAL SUMMARY
    # --------------------------------------------------

    print("\n========== FULL AUDIT SUMMARY ==========")

    print("Total cases investigated:", len(audit_results))
    print("Users successfully matched:", matched)
    print("Cases with linked activity:", activity_cases)
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


# --------------------------------------------------
# 19. RUN AUDIT
# --------------------------------------------------

if __name__ == "__main__":
    main()
