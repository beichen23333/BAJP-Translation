import argparse
import json
import os
import shutil
import zipfile
import concurrent.futures
import sys
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Tuple

from utils.util import ZipUtils

def read_json(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(data: List[Dict[str, Any]], file_path: str) -> None:
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def filter_json_data(data: List[Dict[str, Any]], keys_to_keep: List[str]) -> List[Dict[str, Any]]:
    return [{k: item[k] for k in keys_to_keep if k in item} for item in data]

def process_duplicates_task(args: Tuple[Path, Path, List[str]]) -> Tuple[str, bool]:
    new_file, old_file, keys_to_keep = args
    if not new_file.exists() or not old_file.exists():
        return (new_file.name, False)
    
    try:
        new_data = filter_json_data(read_json(new_file), keys_to_keep)
        old_data = filter_json_data(read_json(old_file), keys_to_keep)
        
        compare_key = keys_to_keep[0]
        old_keys = {item[compare_key] for item in old_data if compare_key in item}
        
        filtered = [item for item in new_data 
                   if compare_key in item and item[compare_key] not in old_keys]
        
        if filtered:
            write_json(filtered, new_file)
            return (new_file.name, True)
        else:
            new_file.unlink()
            return (new_file.name, False)
    except Exception as e:
        print(f"Error processing {new_file.name}: {e}")
        return (new_file.name, False)

def find_changes_task(args: Tuple[Path, Path, List[str]]) -> Tuple[str, List[Dict[str, Any]]]:
    new_file, old_file, keys_to_keep = args
    if not new_file.exists() or not old_file.exists():
        return (new_file.name, [])
    
    try:
        new_data = filter_json_data(read_json(new_file), keys_to_keep)
        old_data = filter_json_data(read_json(old_file), keys_to_keep)
        
        compare_key = keys_to_keep[0]
        old_keys = {item[compare_key] for item in old_data if compare_key in item}
        
        old_by_id = defaultdict(list)
        new_by_id = defaultdict(list)
        
        for idx, item in enumerate(old_data):
            if compare_key in item:
                old_by_id[item[compare_key]].append((idx, item))
        
        for idx, item in enumerate(new_data):
            if compare_key in item and item[compare_key] in old_keys:
                new_by_id[item[compare_key]].append((idx, item))
        
        changed_entries = []

        for id_value in old_keys:
            if id_value in new_by_id:
                for i, (new_idx, new_item) in enumerate(new_by_id[id_value]):
                    if i < len(old_by_id[id_value]):
                        old_idx, old_item = old_by_id[id_value][i]
                        if any(new_item.get(k) != old_item.get(k) for k in keys_to_keep):
                            changed_entry = new_item.copy()
                            changed_entry['Count'] = i + 1
                            changed_entries.append(changed_entry)
        
        return (new_file.name, changed_entries)
    except Exception as e:
        print(f"Error processing changes for {new_file.name}: {e}")
        return (new_file.name, [])

def process_files_concurrently(file_tasks: List[Tuple], task_function, max_workers: int, task_name: str) -> Dict:
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(task_function, task): task[0].name for task in file_tasks}

        for future in concurrent.futures.as_completed(future_to_file):
            file_name = future_to_file[future]
            try:
                result = future.result()
                if isinstance(result, tuple) and len(result) == 2:
                    results[result[0]] = result[1]
            except Exception as e:
                print(f"Error processing {file_name} in {task_name}: {e}")
    
    return results

def create_file_tasks(new_folder: Path, old_folder: Path, schema: Dict[str, List[str]]) -> List[Tuple]:
    tasks = []
    for file_name, keys in schema.items():
        new_file = new_folder / file_name
        old_file = old_folder / file_name
        tasks.append((new_file, old_file, keys))
    return tasks

def main() -> None:
    parser = argparse.ArgumentParser(description="Compare JSON files between two versions with multithreading")
    parser.add_argument('new_version_path')
    parser.add_argument('old_version_path')
    parser.add_argument('out_path')
    parser.add_argument('config_path')
    parser.add_argument('--threads', '-t', type=int, default=4)
    args = parser.parse_args()

    print(f"Using {args.threads} threads for processing")

    config = read_json(args.config_path)
    db_schema = config.get("DBSchema", {})
    excel_table = config.get("ExcelTable", {})

    temp_dirs = ['extracted_new', 'extracted_old', 'extracted_new_backup']
    for dir_name in temp_dirs:
        Path(dir_name).mkdir(exist_ok=True)

    print("Extracting zip files...")
    ZipUtils.extract_zip(args.new_version_path, 'extracted_new', progress_bar=True)
    ZipUtils.extract_zip(args.old_version_path, 'extracted_old', progress_bar=True)
    shutil.copytree('extracted_new', 'extracted_new_backup', dirs_exist_ok=True)

    schema_paths = {
        'DBSchema': (Path('extracted_new')/'DBSchema', Path('extracted_old')/'DBSchema', db_schema),
        'ExcelTable': (Path('extracted_new')/'ExcelTable', Path('extracted_old')/'ExcelTable', excel_table)
    }

    print("Processing duplicates with multithreading...")
    duplicate_results = {}
    for schema_name, (new_path, old_path, schema) in schema_paths.items():
        tasks = create_file_tasks(new_path, old_path, schema)
        results = process_files_concurrently(tasks, process_duplicates_task, args.threads, f"duplicates_{schema_name}")
        duplicate_results[schema_name] = results
        print(f"Processed {len(results)} files in {schema_name}")

    print("Finding changes with multithreading...")
    changes = {}
    for schema_name, (new_path, old_path, schema) in schema_paths.items():
        backup_path = Path('extracted_new_backup') / schema_name
        tasks = create_file_tasks(backup_path, old_path, schema)
        results = process_files_concurrently(tasks, find_changes_task, args.threads, f"changes_{schema_name}")
        changes[schema_name] = results
        print(f"Found changes in {len([v for v in results.values() if v])} files in {schema_name}")

    print("Creating output directories...")
    output_dirs = {
        'New/DBSchema': Path(args.out_path)/'New'/'DBSchema',
        'New/ExcelTable': Path(args.out_path)/'New'/'ExcelTable',
        'Revise/DBSchema': Path(args.out_path)/'Revise'/'DBSchema',
        'Revise/ExcelTable': Path(args.out_path)/'Revise'/'ExcelTable'
    }
    
    for dir_path in output_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    print("Moving files to output directories...")
    for schema_type, (new_path, _, schema) in schema_paths.items():
        for file_name in schema.keys():
            src_file = new_path / file_name
            dst_file = output_dirs[f'New/{schema_type}'] / file_name
            if src_file.exists():
                shutil.move(src_file, dst_file)
                print(f"Moved {file_name} to New/{schema_type}")

    print("Saving changed entries...")
    for schema_type, change_data in changes.items():
        for file_name, changed_entries in change_data.items():
            if changed_entries:
                output_file = output_dirs[f'Revise/{schema_type}'] / file_name
                write_json(changed_entries, output_file)
                print(f"Saved {len(changed_entries)} changes to Revise/{schema_type}/{file_name}")

    print("Cleaning up temporary files...")
    for dir_name in temp_dirs:
        shutil.rmtree(dir_name, ignore_errors=True)
    
    print("Processing completed successfully!")

if __name__ == '__main__':
    main()
