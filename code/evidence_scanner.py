
import csv
import re
from pathlib import Path

from identity_resolver import read_csv, resolve_identity

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"
MANIFEST = DATASET / "evidence_files.csv"

TEXT_EXTENSIONS = {".log", ".txt", ".json", ".sql", ".csv"}


def load_manifest():
    with open(MANIFEST, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def collect_identifiers(identity):
    """Collect current and historical identifiers for one user."""

    identifiers = [
        identity.get("user_id", ""),
        identity.get("current_email", ""),
        identity.get("phone", ""),
        identity.get("email_hash", "")
    ]

    identifiers.extend(identity.get("historical_emails", []))
    identifiers.extend(identity.get("historical_phones", []))

    # Remove empty values and duplicates
    return list(dict.fromkeys(
        str(value).strip()
        for value in identifiers
        if value and str(value).strip()
    ))


def find_matches(file_path, identifiers, evidence_id, relative_path):
    matches = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as file:

            for line_number, line in enumerate(file, start=1):

                for identifier in identifiers:

                    pattern = r"(?<![A-Za-z0-9_])" + re.escape(identifier) + r"(?![A-Za-z0-9_])"

                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append({
                            "evidence_id": evidence_id,
                            "file_path": relative_path,
                            "identifier": identifier,
                            "line_number": line_number,
                            "content": line.strip()[:300]
                        })

    except OSError as error:
        print("File reading error:", error)

    return matches


def scan_evidence(identity):
    identifiers = collect_identifiers(identity)

    results = []
    skipped_files = []

    for item in load_manifest():

        evidence_id = item["file_id"]
        relative_path = item["file_path"]
        full_path = DATASET / relative_path

        if not full_path.exists():
            continue

        if full_path.suffix.lower() not in TEXT_EXTENSIONS:
            skipped_files.append(evidence_id)
            continue

        matches = find_matches(
            full_path,
            identifiers,
            evidence_id,
            relative_path
        )

        results.extend(matches)

    return results, skipped_files


if __name__ == "__main__":

    requests = read_csv("deletion_requests.csv")

    # Test using the first deletion request
    request = requests[0]

    print("\nCASE:", request["case_id"])
    print("REQUEST EMAIL:", request["email"])

    identities = resolve_identity(
        request["email"],
        request["audit_at"]
    )

    if not identities:
        print("No identity found.")
    else:
        for identity in identities:

            print("\nUSER ID:", identity["user_id"])

            identifiers = collect_identifiers(identity)
            print("Identifiers being searched:", identifiers)

            results, skipped = scan_evidence(identity)

            print("\nEVIDENCE MATCHES:")

            for result in results:
                print(
                    result["evidence_id"],
                    "|",
                    result["identifier"],
                    "| Line:",
                    result["line_number"]
                )

            print("\nTotal matches:", len(results))
            print("Skipped image/PDF files:", len(skipped))

