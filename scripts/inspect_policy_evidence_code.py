
import json
import os

folder = "dataset/evidence/records"

for filename in os.listdir(folder):

    if filename.endswith(".json"):

        path = os.path.join(folder, filename)

        print("\n" + "=" * 70)
        print("FILE:", filename)
        print("=" * 70)

        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)

            print(json.dumps(data, indent=2)[:2500])

        except Exception as error:
            print("Error:", error)
