
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
file_path = (
    ROOT / "dataset" / "evidence" / "records" /
    "customer_data_snapshot_bundle_20260917.json"
)

with open(file_path, "r", encoding="utf-8") as file:
    data = json.load(file)


def inspect_structure(value, level=0):
    indent = "  " * level

    if isinstance(value, dict):
        print(indent + "Object keys:", list(value.keys()))

        for key, item in value.items():
            print(indent + f"{key}: ", end="")

            if isinstance(item, (dict, list)):
                print()
                inspect_structure(item, level + 1)
            else:
                print(type(item).__name__)

    elif isinstance(value, list):
        print(indent + "List length:", len(value))

        if value:
            print(indent + "First item structure:")
            inspect_structure(value[0], level + 1)

    else:
        print(indent + type(value).__name__)


print("JSON EVIDENCE STRUCTURE")
print("-----------------------")
inspect_structure(data)
