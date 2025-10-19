import json
import sys

json_file = "./JP/TableBundles/TableCatalog.json"

try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    print(f"Error: Could not read or parse {json_file}: {e}", file=sys.stderr)
    sys.exit(1)

table = data.get("Table")
if not table:
    print("Error: 'Table' key not found in TableCatalog.json", file=sys.stderr)
    sys.exit(1)

for filename in table.keys():
    print(filename)
