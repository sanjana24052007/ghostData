
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE / "dataset" / "evidence"

requests = pd.read_csv(BASE / "dataset" / "deletion_requests.csv")
identities = pd.read_csv(BASE / "dataset" / "user_identities.csv")

# Inspect only the cases we are currently investigating.
selected_cases = requests[
    requests["case_id"].astype(str).isin(
        [f"case_{i}" for i in range(538, 551)]
    )
]

extensions = {".sql", ".log", ".txt"}

for _, case in requests.iterrows():
    email = str(case["email"]).strip()
    case_id = str(case["case_id"])

    identity = identities[
        identities["email"].astype(str).str.strip().str.lower()
        == email.lower()
    ]

    user_ids = identity["user_id"].astype(str).tolist()

    targets = [email] + user_ids

    print("\n" + "=" * 65)
    print("CASE:", case_id)
    print("EMAIL:", email)
    print("USER IDS:", user_ids)
    print("=" * 65)

    total = 0

    for path in EVIDENCE_DIR.rglob("*"):

        if not path.is_file() or path.suffix.lower() not in extensions:
            continue

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore"
            ).splitlines()
        except Exception:
            continue

        for line_number, line in enumerate(lines, start=1):

            if any(
                target.lower() in line.lower()
                for target in targets
            ):

                total += 1

                print(f"\nFILE: {path.name}")
                print(f"LINE: {line_number}")
                print("MATCH:", line.strip())

                # Print nearby lines for context.
                start = max(0, line_number - 3)
                end = min(len(lines), line_number + 2)

                print("CONTEXT:")

                for i in range(start, end):
                    print(f"{i + 1}: {lines[i].strip()}")

    print("\nTOTAL MATCHING LINES:", total)
