
import json
import os

folder = "dataset/evidence/records"

for filename in sorted(os.listdir(folder)):

    if not filename.endswith(".json"):
        continue

    path = os.path.join(folder, filename)

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    print("\n" + "=" * 75)
    print("FILE:", filename)
    print("=" * 75)

    services = data.get("service_exports", {})

    for service_name, service_data in services.items():

        print("\nSERVICE:", service_name)

        for record_type, records in service_data.items():

            print("\nRECORD TYPE:", record_type)
            print("TOTAL RECORDS:", len(records))

            if records:
                print("AVAILABLE FIELDS:")
                print(list(records[0].keys()))

                print("SAMPLE RECORD:")
                print(records[0])

