
import pandas as pd
from pathlib import Path

# Find the project folder
BASE_DIR = Path(__file__).resolve().parent.parent

# Dataset folder location
DATASET_DIR = BASE_DIR / "dataset"


def load_all_data():

    files = {
        "requests": "deletion_requests.csv",
        "identities": "user_identities.csv",
        "audit_log": "user_audit_log.csv",
        "activity": "system_activity.csv",
        "rules": "deletion_rules.csv",
        "evidence": "evidence_files.csv"
    }

    data = {}

    for key, filename in files.items():

        file_path = DATASET_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found: {file_path}"
            )

        data[key] = pd.read_csv(
            file_path,
            dtype=str,
            keep_default_na=False
        )

        print(f"Loaded {filename}: {len(data[key])} rows")

    # Normalize email addresses
    if "email" in data["requests"].columns:
        data["requests"]["email"] = (
            data["requests"]["email"]
            .str.strip()
            .str.lower()
        )

    return data


if __name__ == "__main__":

    dataset = load_all_data()

    print("\nDataset loading successful!")

    print("\nDeletion request columns:")
    print(dataset["requests"].columns.tolist())

    print("\nTotal deletion requests:")
    print(len(dataset["requests"]))
