import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = ROOT / "code"
DATASET_DIR = ROOT / "dataset"
RESULTS_DIR = ROOT / "results"

# Allow this script to import modules from code/
sys.path.insert(0, str(CODE_DIR))

from identity_resolver import read_csv, resolve_identity
from evidence_scanner import scan_evidence


RESULTS_DIR.mkdir(parents=True, exist_ok=True)

requests = read_csv("deletion_requests.csv")
all_results = []

for request in requests:
    case_id = request["case_id"]

    print("Scanning:", case_id)

    identities = resolve_identity(
        request["email"],
        request["audit_at"]
    )

    for identity in identities:
        matches, skipped = scan_evidence(identity)

        for match in matches:
            match["case_id"] = case_id
            all_results.append(match)


output = RESULTS_DIR / "all_evidence_matches.csv"

fields = [
    "case_id",
    "evidence_id",
    "file_path",
    "identifier",
    "line_number",
    "content"
]

with open(output, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(all_results)

print("\nAll cases scanned!")
print("Total matches:", len(all_results))
print("Report:", output)