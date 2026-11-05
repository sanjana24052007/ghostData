
import csv
from pathlib import Path
from flask import Flask, render_template, send_file, abort

app = Flask(__name__)

ROOT = Path(__file__).resolve().parent

REPORTS = [
    "audit_results.csv",
    "high_risk_report.csv",
    "detailed_evidence_report.csv"
]


# --------------------------------------------------
# 1. READ CSV FILES
# --------------------------------------------------

def read_csv(filename):
    file_path = ROOT / filename

    if not file_path.exists():
        return []

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# 2. GET VALUES FROM CSV ROWS
# --------------------------------------------------

def get_value(row, names, default="Not available"):
    for name in names:
        for key, value in row.items():
            if key.strip().lower() == name.strip().lower():
                return value if value else default

    return default


# --------------------------------------------------
# 3. NORMALIZE AUDIT CASES
# --------------------------------------------------

def normalize_case(row):
    return {
        "case_id": get_value(row, ["case_id"]),
        "user_id": get_value(row, ["user_id", "matched_user_id"]),

        "deletion_date": get_value(row, ["deletion_request_date"]),
        "detection_date": get_value(row, ["detection_date"]),
        "resource_type": get_value(row, ["resource_type"]),

        "risk": get_value(row, ["risk_level", "risk"]),
        "risk_score": get_value(
            row, ["risk_score"], "Not calculated"
        ),

        "reason": get_value(row, ["reason"]),
        "evidence_source": get_value(row, ["evidence_source"]),
        "recommended_action": get_value(
            row, ["recommended_action"]
        ),

        "exports": get_value(
            row, ["post_deletion_exports"], "0"
        ),

        "identity_found": get_value(row, ["identity_found"]),
        "activity_references": get_value(
            row, ["activity_references"]
        )
    }


# --------------------------------------------------
# 4. NORMALIZE EVIDENCE RECORDS
# --------------------------------------------------

def normalize_evidence(row):
    return {
        "case_id": get_value(row, ["case_id"]),
        "user_id": get_value(row, ["user_id"]),
        "deletion_date": get_value(
            row, ["reported_deletion_time"]
        ),
        "resource_id": get_value(row, ["resource_id"]),
        "timestamp": get_value(row, ["event_timestamp"]),
        "file": get_value(row, ["evidence_file"]),
        "line": get_value(row, ["evidence_line"]),
        "reason": get_value(row, ["reason"])
    }


# --------------------------------------------------
# 5. DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    # Read source reports
    audit_rows = read_csv("audit_results.csv")
    high_rows = read_csv("high_risk_report.csv")
    evidence_rows = read_csv("detailed_evidence_report.csv")

    deletion_rows = read_csv(
        "dataset/deletion_requests.csv"
    )

    # Normalize audit cases
    cases = [
        normalize_case(row) for row in audit_rows
    ]

    # Calculate risk counts
    counts = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "REVIEW": 0
    }

    for case in cases:
        risk = case["risk"].upper()

        for level in counts:
            if level in risk:
                counts[level] += 1
                break

    # Identify high-risk cases
    high_cases = [
        case for case in cases
        if "HIGH" in case["risk"].upper()
    ]

    if not high_cases and high_rows:
        high_cases = [
            normalize_case(row) for row in high_rows
        ]

    # Normalize evidence
    evidence = [
        normalize_evidence(row)
        for row in evidence_rows
    ]

    # Match evidence with cases
    evidence_by_case = {}

    for item in evidence:
        case_id = item["case_id"]

        evidence_by_case.setdefault(
            case_id, []
        ).append(item)

    for case in cases:

        matches = evidence_by_case.get(
            case["case_id"], []
        )

        if matches:
            item = matches[0]

            case["user_id"] = item["user_id"]
            case["detection_date"] = item["timestamp"]

            resource_id = item["resource_id"]

            if resource_id.startswith("export_"):
                case["resource_type"] = "Export"
            else:
                case["resource_type"] = resource_id

            case["evidence_source"] = item["file"]

            # Recommended action based on actual finding
            if (
                case["risk"].upper() == "HIGH"
                and "export availability" in case["reason"].lower()
            ):
                case["recommended_action"] = (
                    "Investigate export retention, verify deletion "
                    "completion, and restrict access to the export."
                )

    # Match deletion requests with cases
    deletion_by_case = {
        row["case_id"]: row
        for row in deletion_rows
    }

    for case in cases:

        deletion = deletion_by_case.get(
            case["case_id"]
        )

        if deletion:
            case["deletion_date"] = deletion["requested_at"]

    # Check whether main report exists
    missing = not (
        ROOT / "audit_results.csv"
    ).exists()

    # Render dashboard
    return render_template(
        "index.html",
        total=len(cases),
        counts=counts,
        cases=cases,
        high_cases=high_cases,
        evidence=evidence,
        missing=missing
    )


# --------------------------------------------------
# 6. DOWNLOAD REPORTS
# --------------------------------------------------

@app.route("/download/<filename>")
def download(filename):

    if filename not in REPORTS:
        abort(404)

    file_path = ROOT / filename

    if not file_path.exists():
        abort(404)

    return send_file(
        file_path,
        as_attachment=True
    )


# --------------------------------------------------
# 7. RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
