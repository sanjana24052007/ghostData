
from pathlib import Path
import json
from collections import Counter

evidence_folder = Path("dataset/evidence")

files = [f for f in evidence_folder.rglob("*") if f.is_file()]

print("\n========== EVIDENCE INVENTORY ==========")
print("Total evidence files:", len(files))

extension_counts = Counter(
    file.suffix.lower() for file in files
)

print("\nFile types:")
for extension, count in extension_counts.items():
    print(extension or "(no extension)", ":", count)

print("\n========== FILE NAMES ==========")

for file in sorted(files):
    print(file)


print("\n========== JSON STRUCTURE ==========")

for file in sorted(files):

    if file.suffix.lower() != ".json":
        continue

    print("\n" + "=" * 60)
    print("FILE:", file.name)
    print("=" * 60)

    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("Top-level keys:", list(data.keys()))

        if "service_exports" in data:
            for service, sections in data["service_exports"].items():

                print("\nSERVICE:", service)

                if isinstance(sections, dict):
                    for section, records in sections.items():

                        print("  Section:", section)

                        if isinstance(records, list):
                            print("  Number of records:", len(records))

                            if records and isinstance(records[0], dict):
                                print(
                                    "  Record fields:",
                                    list(records[0].keys())
                                )

                        elif isinstance(records, dict):
                            print("  Fields:", list(records.keys()))

        else:
            print("Other JSON structure. Top-level data type:", type(data).__name__)

    except Exception as error:
        print("Could not inspect:", error)
