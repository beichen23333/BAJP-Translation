import argparse
import zipfile
import tempfile
import shutil
import json
from pathlib import Path

def process_revise_data(original_data, modify_data):
    result = original_data.copy()
    modify_data_by_id = {}
    for modify_item in modify_data:
        id_key = list(modify_item.keys())[0]
        id_value = modify_item[id_key]
        if id_value not in modify_data_by_id:
            modify_data_by_id[id_value] = []
        modify_data_by_id[id_value].append(modify_item)
    for id_value, modify_items in modify_data_by_id.items():
        matching_indices = []
        for i, original_item in enumerate(result):
            id_key = list(original_item.keys())[0]
            if original_item.get(id_key) == id_value:
                matching_indices.append(i)
        if not matching_indices:
            continue
        for i, modify_item in enumerate(modify_items):
            if i >= len(matching_indices):
                continue
            if 'Count' in modify_item:
                count_value = modify_item.pop('Count')
                if 1 <= count_value <= len(matching_indices):
                    target_index = matching_indices[count_value - 1]
                    result[target_index].update(modify_item)
                else:
                    continue
            else:
                target_index = matching_indices[i]
                result[target_index].update(modify_item)
    return result


def process_cover_data(original_data, modify_data):
    result = []
    processed_ids = set()
    for modify_item in modify_data:
        id_key = list(modify_item.keys())[0]
        id_value = modify_item[id_key]
        result.append(modify_item)
        processed_ids.add((id_key, id_value))
    for original_item in original_data:
        id_key = list(original_item.keys())[0]
        id_value = original_item[id_key]
        if (id_key, id_value) not in processed_ids:
            result.append(original_item)
    return result


def apply_modifications(original_data, modify_dir, filename, mode):
    modify_file = modify_dir / filename
    if not modify_file.exists():
        return original_data
    with open(modify_file, 'r', encoding='utf-8') as f:
        try:
            modify_data = json.load(f)
        except json.JSONDecodeError:
            return original_data
    if not isinstance(modify_data, list):
        return original_data
    original_data_list = original_data if isinstance(original_data, list) else []
    if not isinstance(original_data_list, list):
        return original_data_list
    result = original_data_list.copy()
    if mode == 'revise':
        revised_data = original_data_list.copy()
        for modify_item in modify_data:
            if not isinstance(modify_item, dict) or not modify_item:
                continue
            match_key = next(iter(modify_item.keys()), None)
            if not match_key:
                continue
            if match_key not in modify_item:
                continue
            try:
                match_value = modify_item[match_key]
            except KeyError:
                continue
            matched_indices = []
            for idx, item in enumerate(revised_data):
                if isinstance(item, dict) and match_key in item and item[match_key] == match_value:
                    matched_indices.append(idx)
            if not matched_indices:
                continue
            if 'Count' in modify_item:
                count = modify_item['Count']
                if not isinstance(count, int) or count < 1 or count > len(matched_indices):
                    continue
                target_idx = matched_indices[count - 1]
                revised_data[target_idx].update({k: v for k, v in modify_item.items() if k != 'Count'})
            else:
                if matched_indices:
                    target_idx = matched_indices[0]
                    revised_data[target_idx].update({k: v for k, v in modify_item.items() if k != 'Count'})
        return revised_data
    elif mode == 'cover':
        cover_data = []
        original_remaining = []
        matched_set = set()
        for modify_item in modify_data:
            if not isinstance(modify_item, dict) or not modify_item:
                continue
            match_key = next(iter(modify_item.keys()), None)
            if not match_key:
                continue
            if match_key not in modify_item:
                continue
            try:
                match_value = modify_item[match_key]
            except KeyError:
                continue
            cover_data.append(modify_item)
            matched_set.add((match_key, match_value))
        for item in original_data_list:
            if not isinstance(item, dict):
                original_remaining.append(item)
                continue
            if len(item) == 0:
                original_remaining.append(item)
                continue
            keys = list(item.keys())
            if not keys:
                original_remaining.append(item)
                continue
            id_key = keys[0]
            id_value = item[id_key]
            if (id_key, id_value) in matched_set:
                continue
            original_remaining.append(item)
        return cover_data + original_remaining
    return original_data


def main():
    parser = argparse.ArgumentParser(description="Process Modify.zip with Revise and Cover folders")
    parser.add_argument("modify_zip", type=Path, help="Modify zip file containing JSON files")
    parser.add_argument("revise_cover_zip", type=Path, help="Zip file containing Revise and Cover folders with modification JSONs")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    args = parser.parse_args()

    modify_extract_dir = Path("modify_extract")
    modify_extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.modify_zip, "r") as modify_zip:
        modify_zip.extractall(path=modify_extract_dir)

    revise_cover_extract_dir = Path("revise_cover_extract")
    revise_cover_extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(args.revise_cover_zip, "r") as rc_zip:
        rc_zip.extractall(path=revise_cover_extract_dir)

    revise_excel_table_dir = revise_cover_extract_dir / "Revise" / "ExcelTable"
    revise_db_schema_dir = revise_cover_extract_dir / "Revise" / "DBSchema"
    cover_excel_table_dir = revise_cover_extract_dir / "Cover" / "ExcelTable"
    cover_db_schema_dir = revise_cover_extract_dir / "Cover" / "DBSchema"

    excel_table_dir = modify_extract_dir / "ExcelTable"
    if excel_table_dir.exists():
        for json_file in excel_table_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            filename = json_file.name
            revised_data = original_data
            if revise_excel_table_dir.exists():
                revised_data = apply_modifications(revised_data, revise_excel_table_dir, filename, 'revise')
            if cover_excel_table_dir.exists():
                revised_data = apply_modifications(revised_data, cover_excel_table_dir, filename, 'cover')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(revised_data, f, ensure_ascii=False, indent=2)

    db_schema_dir = modify_extract_dir / "DBSchema"
    if db_schema_dir.exists():
        for json_file in db_schema_dir.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            filename = json_file.name
            revised_data = original_data
            if revise_db_schema_dir.exists():
                revised_data = apply_modifications(revised_data, revise_db_schema_dir, filename, 'revise')
            if cover_db_schema_dir.exists():
                revised_data = apply_modifications(revised_data, cover_db_schema_dir, filename, 'cover')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(revised_data, f, ensure_ascii=False, indent=2)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    final_modify_zip = args.output_dir / "Modify.zip"

    with zipfile.ZipFile(final_modify_zip, 'w', zipfile.ZIP_DEFLATED) as final_zip:
        for file in modify_extract_dir.rglob('*.json'):
            if file.is_file():
                arcname = file.relative_to(modify_extract_dir)
                final_zip.write(file, arcname)

    shutil.rmtree(modify_extract_dir)
    shutil.rmtree(revise_cover_extract_dir)


if __name__ == "__main__":
    main()