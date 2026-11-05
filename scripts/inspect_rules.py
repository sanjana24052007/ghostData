
import pandas as pd

rules = pd.read_csv("dataset/deletion_rules.csv")

print("TOTAL RULES:", len(rules))
print("\nALL DELETION RULES:\n")

for _, rule in rules.iterrows():
    print("Rule ID:", rule["rule_id"])
    print("Category:", rule["data_category"])
    print("Condition:", rule["condition"])
    print("Action:", rule["required_action"])
    print("-" * 50)
