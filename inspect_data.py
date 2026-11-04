
import pandas as pd

activities = pd.read_csv("dataset/system_activity.csv")
rules = pd.read_csv("dataset/deletion_rules.csv")

# 1. Display all 15 deletion rules
print("\n========== ALL DELETION RULES ==========")
print(rules.to_string(index=False))

# 2. Inspect important risk-related events
important_events = [
    "SYNC_RECORD",
    "RESTORE_BACKUP",
    "CREATE_EXPORT",
    "INDEX_RECORD",
    "REFRESH_CACHE",
    "LINK_RESOURCE_IDENTITY",
    "CHECK_DATA_FLOW",
    "DISABLE_DATA_FLOW",
    "BLOCK_RESTORE",
    "CHECK_RESTORE_ACCESS"
]

for event in important_events:

    print("\n======================================")
    print("EVENT TYPE:", event)
    print("======================================")

    selected = activities[
        activities["event_type"] == event
    ]

    print("Total records:", len(selected))

    print(
        selected.head(10).to_string(index=False)
    )

# 3. Inspect unsuccessful activities
print("\n========== FAILED AND PARTIAL EVENTS ==========")

problem_events = activities[
    activities["reported_result"].isin(["FAILED", "PARTIAL"])
]

print(problem_events.head(30).to_string(index=False))

# 4. Inspect latest activities
print("\n========== LATEST 20 ACTIVITIES ==========")

activities["event_time"] = pd.to_datetime(
    activities["event_time"], utc=True
)

print(
    activities.sort_values("event_time")
    .tail(20)
    .to_string(index=False)
)
print("\n========== ACTIVITIES LINKED TO CUSTOMERS ==========")

import pandas as pd

activities = pd.read_csv("dataset/system_activity.csv")
links = activities[
    activities["event_type"] == "LINK_RESOURCE_IDENTITY"
]

for _, link in links.iterrows():
    resource = str(link["resource_id"])

    print("\nCustomer link:")
    print(link["details"])

    related = activities[
        (activities["resource_id"] == resource) |
        (activities["details"].str.contains(
            resource, case=False, na=False
        ))
    ]

    print(related[
        [
            "activity_id",
            "event_time",
            "event_type",
            "resource_id",
            "reported_result",
            "details"
        ]
    ].to_string(index=False))