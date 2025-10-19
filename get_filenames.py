import json
import sys

def extract_filenames(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Could not read or parse {json_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if "Table" in data or "TablePack" in data:
        table = data.get("Table", {})
        tablepack = data.get("TablePack", {})
        filenames = set(table.keys()).union(set(tablepack.keys()))
        for filename in filenames:
            print(filename)
    elif "MediaResources" in data:
        for resource in data["MediaResources"].values():
            path = resource["path"].replace("\\", "/")
            print(path)
    else:
        print(f"Error: Unknown JSON format in {json_file}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 get_filenames.py <json_file>", file=sys.stderr)
        sys.exit(1)

    json_file = sys.argv[1]
    extract_filenames(json_file)
