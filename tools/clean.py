import argparse
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import tempfile

def read_json(file_path: str) -> List[Dict[str, Any]]:
    """Read JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(data: List[Dict[str, Any]], file_path: str) -> None:
    """Write JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def filter_json_data(data: List[Dict[str, Any]], keys_to_keep: List[str]) -> List[Dict[str, Any]]:
    """Filter JSON data to keep only specified keys"""
    return [{k: item[k] for k in keys_to_keep if k in item} for item in data]

def extract_zip(zip_path: str, extract_to: str) -> None:
    """Extract ZIP file"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def create_zip(source_dir: str, output_zip: str) -> None:
    """Create ZIP file from directory"""
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)

def process_config_files(input_dir: str, output_dir: str, config: Dict[str, Dict[str, List[str]]]) -> None:
    """
    Process only DBSchema and ExcelTable files specified in config
    Skips all other files and directories
    """
    # Create output directories if they don't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for folder in ['DBSchema', 'ExcelTable']:
        if folder not in config:
            continue
            
        input_folder = Path(input_dir) / folder
        output_folder = Path(output_dir) / folder
        output_folder.mkdir(parents=True, exist_ok=True)

        for file_name, keys_to_keep in config[folder].items():
            input_file = input_folder / file_name
            if not input_file.exists():
                print(f"Warning: File not found {input_file}")
                continue

            try:
                # Read and filter data
                original_data = read_json(input_file)
                filtered_data = filter_json_data(original_data, keys_to_keep)
                
                # Write output file
                output_file = output_folder / file_name
                write_json(filtered_data, output_file)
                print(f"Processed: {folder}/{file_name}")
            except Exception as e:
                print(f"Error processing {folder}/{file_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Process ZIP file to filter JSON data based on config")
    parser.add_argument('zip_path', help='Input ZIP file path')
    parser.add_argument('config_path', help='config.json file path')
    parser.add_argument('output_zip', help='Output ZIP file path')
    args = parser.parse_args()

    # Create temporary directories
    temp_extract_dir = tempfile.mkdtemp()
    temp_output_dir = tempfile.mkdtemp()

    try:
        # Extract input ZIP file
        print(f"Extracting {args.zip_path} to temporary directory...")
        extract_zip(args.zip_path, temp_extract_dir)

        # Read config file
        print(f"Reading config file {args.config_path}...")
        config = read_json(args.config_path)

        # Process only files specified in config
        print("Processing DBSchema and ExcelTable files...")
        process_config_files(temp_extract_dir, temp_output_dir, config)

        # Create output ZIP
        print(f"Creating output ZIP file {args.output_zip}...")
        create_zip(temp_output_dir, args.output_zip)

        print(f"Processing complete! Results saved to: {args.output_zip}")
    finally:
        # Clean up temporary directories
        shutil.rmtree(temp_extract_dir)
        shutil.rmtree(temp_output_dir)

if __name__ == '__main__':
    main()
