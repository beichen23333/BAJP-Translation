import argparse
import json
import os
import shutil
import zipfile

def extract_zip(zip_path: str, extract_to: str) -> None:
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_to)

def read_json(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_json_files(new_folder: str, old_folder: str, schema: dict) -> None:
    for file_name, keys in schema.items():
        new_file = os.path.join(new_folder, file_name)
        old_file = os.path.join(old_folder, file_name)

        if not os.path.exists(new_file) or not os.path.exists(old_file):
            print(f"The file {file_name} does not exist in either the new version or the old version, is skipped.")
            continue

        new_data = read_json(new_file)
        old_data = read_json(old_file)

        key = keys[0]
        old_keys = {item[key] for item in old_data}
        filtered = [item for item in new_data if item[key] not in old_keys]

        with open(new_file, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, ensure_ascii=False, indent=4)

        print(f"Processed {file_name}, removed {len(new_data) - len(filtered)} duplicate entries with key={key}.")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('new_version_path', required=True)
    parser.add_argument('old_version_path', required=True)
    parser.add_argument('out_path', required=True)
    parser.add_argument('config_path', required=True)
    args = parser.parse_args()

    config = read_json(args.config_path)
    db_schema = config.get("DBSchema", {})
    excel_table = config.get("ExcelTable", {})

    extracted_new = 'extracted_new'
    extracted_old = 'extracted_old'
    os.makedirs(extracted_new, exist_ok=True)
    os.makedirs(extracted_old, exist_ok=True)

    if not (os.path.exists(args.new_version_path) and os.path.exists(args.old_version_path)):
        print("The zip file is missing. Exit.")
        return

    extract_zip(args.new_version_path, extracted_new)
    extract_zip(args.old_version_path, extracted_old)

    db_new_folder = os.path.join(extracted_new, 'DBSchema')
    db_old_folder = os.path.join(extracted_old, 'DBSchema')
    compare_json_files(db_new_folder, db_old_folder, db_schema)

    excel_new_folder = os.path.join(extracted_new, 'ExcelTable')
    excel_old_folder = os.path.join(extracted_old, 'ExcelTable')
    compare_json_files(excel_new_folder, excel_old_folder, excel_table)

    os.makedirs(args.out_path, exist_ok=True)
    for folder, schema in [(db_new_folder, db_schema), (excel_new_folder, excel_table)]:
        for file_name in schema.keys():
            src = os.path.join(folder, file_name)
            dst = os.path.join(args.out_path, file_name)
            if os.path.exists(src):
                shutil.move(src, dst)
            else:
                print(f"{src} does not exist, skip.")

    shutil.rmtree(extracted_new, ignore_errors=True)
    shutil.rmtree(extracted_old, ignore_errors=True)
    print("End")

if __name__ == '__main__':
    main()
