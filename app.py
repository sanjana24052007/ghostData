
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


def read_csv(filename):
    file_path = ROOT / filename

    if not file_path.exists():
        return []

    with file_path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def get_value(row, names, default="Not available"):
    for name in names:
        for key, value in row.items():
            if key.strip().lower() == name.lower():
                return value if value else default

    return default


def normalize_case(row):
    return {
        "case_id": get_value(row, ["case_id", "case"]),
        "user_id": get_value(row, ["user_id", "matched_user_id"]),
        "risk": get_value(
            row, ["risk_level", "risk", "classification", "risk_classification"]
        ),
        "reason": get_value(
            row, ["reason", "risk_reason", "findings", "explanation"]
        ),
        "exports": get_value(
            row, ["post_deletion_exports", "export_count", "exports"]
        )
    }


def normalize_evidence(row):
    return {
        "case_id": get_value(row, ["case_id", "case"]),
        "user_id": get_value(row, ["user_id"]),
        "resource_id": get_value(row, ["resource_id"]),
        "timestamp": get_value(
            row, ["event_timestamp", "timestamp", "event_time", "captured_at"]
        ),
        "file": get_value(row, ["file_path", "evidence_file", "file"]),
        "line": get_value(
            row, ["evidence_line", "matched_line", "log_line", "details"]
        )
    }


@app.route("/")
def dashboard():
    audit_rows = read_csv("audit_results.csv")
    high_rows = read_csv("high_risk_report.csv")
    evidence_rows = read_csv("detailed_evidence_report.csv")

    cases = [normalize_case(row) for row in audit_rows]

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

    high_cases = [
        case for case in cases if "HIGH" in case["risk"].upper()
    ]

    # Use the separate high-risk report if the main report
    # does not contain a recognizable risk column.
    if not high_cases and high_rows:
        high_cases = [normalize_case(row) for row in high_rows]

    evidence = [
        normalize_evidence(row) for row in evidence_rows
    ]

    missing = not (ROOT / "audit_results.csv").exists()

    return render_template(
        "index.html",
        total=len(cases),
        counts=counts,
        high_cases=high_cases,
        evidence=evidence,
        missing=missing
    )


@app.route("/download/<filename>")
def download(filename):
    if filename not in REPORTS:
        abort(404)

    file_path = ROOT / filename

    if not file_path.exists():
        abort(404)

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
