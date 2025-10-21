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
    """Read JSON file and return as list of dictionaries"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(data: List[Dict[str, Any]], file_path: str) -> None:
    """Write list of dictionaries to JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def overwrite_entries_task(args: Tuple[Path, Path, List[str]]) -> Tuple[str, bool]:
    """
    Overwrite original entries with new data while preserving order for same-ID entries
    Args:
        args: (modified_file, original_file, keys_to_keep)
    Returns:
        Tuple[filename, success_flag]
    """
    modified_file, original_file, keys_to_keep = args
    if not modified_file.exists():
        print(f"New file not found: {modified_file}")
        return (modified_file.name, False)
    
    try:
        # Read new data (array of objects)
        new_data = read_json(modified_file)
        if not new_data:
            print(f"No data found in {modified_file.name}")
            return (modified_file.name, False)
        
        print(f"Found {len(new_data)} entries in {modified_file.name}")
            
        # Create original file if not exists
        if not original_file.exists():
            print(f"Original file not found, creating: {original_file}")
            write_json(new_data, original_file)
            return (modified_file.name, True)
            
        # Read original data (array of objects)
        original_data = read_json(original_file)
        print(f"Found {len(original_data)} entries in original {original_file.name}")
        
        compare_key = keys_to_keep[0]  # Use first key in config as compare key
        print(f"Using compare key: {compare_key}")
        
        # Create mapping of new data by compare_key
        new_data_map = defaultdict(list)
        for item in new_data:
            if compare_key in item:
                new_data_map[item[compare_key]].append(item)
        
        changed = False
        
        # Process original data in order
        for original_item in original_data:
            if compare_key not in original_item:
                continue
                
            key_value = original_item[compare_key]
            
            if key_value in new_data_map and new_data_map[key_value]:
                # Get the next available new item for this key
                new_item = new_data_map[key_value].pop(0)
                
                # Update all specified keys
                for key in keys_to_keep:
                    if key in new_item:
                        if original_item.get(key) != new_item[key]:
                            original_item[key] = new_item[key]
                            changed = True
        
        if changed:
            write_json(original_data, original_file)
            print(f"Successfully updated entries in {original_file.name}")
            return (modified_file.name, True)
            
        print(f"No changes needed for {original_file.name}")
        return (modified_file.name, False)
        
    except Exception as e:
        print(f"Error overwriting {modified_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return (modified_file.name, False)


def apply_changes_task(args: Tuple[Path, Path, List[str]]) -> Tuple[str, bool]:
    """
    Apply changes to original file (with Count parameter support)
    Args:
        args: (changes_file, original_file, keys_to_keep)
    Returns:
        Tuple[filename, success_flag]
    """
    changes_file, original_file, keys_to_keep = args
    if not changes_file.exists():
        return (changes_file.name, False)
    
    try:
        changes_data = read_json(changes_file)
        
        if not original_file.exists():
            return (changes_file.name, False)
            
        original_data = read_json(original_file)
        
        compare_key = keys_to_keep[0]
        original_by_id = defaultdict(list)
        
        for idx, item in enumerate(original_data):
            if compare_key in item:
                original_by_id[item[compare_key]].append((idx, item))
        
        changed_count = 0
        
        for change_entry in changes_data:
            if compare_key not in change_entry:
                continue
                
            id_value = change_entry[compare_key]
            count = change_entry.get('Count', 1) - 1  # Convert to 0-based index
            
            if id_value in original_by_id and count < len(original_by_id[id_value]):
                idx, original_item = original_by_id[id_value][count]
                # Update only the specified keys
                for key in keys_to_keep:
                    if key in change_entry:
                        original_item[key] = change_entry[key]
                changed_count += 1
        
        if changed_count > 0:
            write_json(original_data, original_file)
            return (changes_file.name, True)
        return (changes_file.name, False)
    except Exception as e:
        print(f"Error applying changes in {changes_file.name}: {e}")
        return (changes_file.name, False)

def process_files_concurrently(file_tasks: List[Tuple], task_function, max_workers: int, task_name: str) -> Dict:
    """Process files concurrently using ThreadPoolExecutor"""
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

def create_file_tasks(modified_folder: Path, original_folder: Path, schema: Dict[str, List[str]]) -> List[Tuple]:
    """Create task tuples for processing"""
    tasks = []
    for file_name, keys in schema.items():
        modified_file = modified_folder / file_name
        original_file = original_folder / file_name
        tasks.append((modified_file, original_file, keys))
    return tasks

def main() -> None:
    """Main function to handle file overwrites and changes"""
    parser = argparse.ArgumentParser(description="Overwrite original JSON files with modified versions")
    parser.add_argument('modified_dir', help="Directory containing the modified files")
    parser.add_argument('target_zip', help="Target zip file to update (will be overwritten)")
    parser.add_argument('config_file', help="Path to the config JSON file")
    parser.add_argument('threads', type=int)
    args = parser.parse_args()

    print(f"Using {args.threads} threads for processing")

    config = read_json(args.config_file)
    db_schema = config.get("DBSchema", {})
    excel_table = config.get("ExcelTable", {})

    temp_dir = 'extracted_temp'
    Path(temp_dir).mkdir(exist_ok=True)

    print(f"Extracting target zip file: {args.target_zip}")
    ZipUtils.extract_zip(args.target_zip, temp_dir, progress_bar=True)

    schema_paths = {
        'DBSchema': {
            'new': Path(args.modified_dir)/'NewBack'/'DBSchema',
            'revise': Path(args.modified_dir)/'ReviseBack'/'DBSchema',
            'original': Path(temp_dir)/'DBSchema',
            'schema': db_schema
        },
        'ExcelTable': {
            'new': Path(args.modified_dir)/'NewBack'/'ExcelTable',
            'revise': Path(args.modified_dir)/'ReviseBack'/'ExcelTable',
            'original': Path(temp_dir)/'ExcelTable',
            'schema': excel_table
        }
    }

    # Process overwrites (New files)
    print("\nProcessing OVERWRITE entries...")
    for schema_name, paths in schema_paths.items():
        print(f"\nProcessing {schema_name} overwrites:")
        tasks = create_file_tasks(paths['new'], paths['original'], paths['schema'])
        results = process_files_concurrently(tasks, overwrite_entries_task, args.threads, f"overwrite_{schema_name}")
        
        success_count = sum(1 for v in results.values() if v)
        total_files = len(results)
        print(f"Successfully overwritten entries in {success_count}/{total_files} files")
        
        for file_name, success in results.items():
            status = "SUCCESS" if success else "SKIPPED (no changes or file not found)"
            print(f"- {file_name}: {status}")

    # Process changes (Revise files)
    print("\nProcessing REVISE entries...")
    for schema_name, paths in schema_paths.items():
        print(f"\nProcessing {schema_name} changes:")
        tasks = create_file_tasks(paths['revise'], paths['original'], paths['schema'])
        results = process_files_concurrently(tasks, apply_changes_task, args.threads, f"apply_changes_{schema_name}")
        
        success_count = sum(1 for v in results.values() if v)
        total_files = len(results)
        print(f"Successfully applied changes in {success_count}/{total_files} files")
        
        for file_name, success in results.items():
            status = "SUCCESS" if success else "SKIPPED (no changes or file not found)"
            print(f"- {file_name}: {status}")

    print(f"\nOverwriting original zip file: {args.target_zip}")
    with zipfile.ZipFile(args.target_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    print("Cleaning up temporary files...")
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"\nSuccessfully updated {args.target_zip}")

if __name__ == '__main__':
    main()
