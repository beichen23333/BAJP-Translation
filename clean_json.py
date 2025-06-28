import os
import json
import argparse
from pathlib import Path

def clean_json_file(file_path, keep_keys):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        cleaned_data = clean_json(json_data, keep_keys)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
        print(f"Cleaned {file_path}")
    except FileNotFoundError:
        print(f"File {file_path} not found, skipping.")
    except json.JSONDecodeError:
        print(f"File {file_path} is not a valid JSON file, skipping.")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def clean_json(data, keep_keys):
    if isinstance(data, dict):
        cleaned_data = {}
        for key, value in data.items():
            if key in keep_keys:
                cleaned_data[key] = clean_json(value, keep_keys)
        return cleaned_data
    elif isinstance(data, list):
        return [clean_json(item, keep_keys) for item in data]
    else:
        return data

def main():
    parser = argparse.ArgumentParser(description="Clean JSON files in a directory based on a configuration file.")
    parser.add_argument('--output_dir', type=str, required=True, help="Directory containing JSON files.")
    parser.add_argument('--server', type=str, required=True, choices=['日服', '国服', '国际服'], help="选择服务器")
    parser.add_argument("--zip_path", type=Path, default="./unpacked/UnpackedExcel.zip", help="Path to save the ZIP archive.")
    args = parser.parse_args()

    # 读取配置文件
    config_file = '配置.json'
    if not os.path.exists(config_file):
        print(f"Configuration file {config_file} not found.")
        return

    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)

    # 获取指定目录
    output_dir = args.output_dir
    if not os.path.exists(output_dir):
        print(f"Directory {output_dir} does not exist.")
        return

    # 获取指定服务器的配置
    server_config = config_data.get("DBSchema", {}).get(args.server)
    if not server_config:
        print(f"Server {args.server} not found in configuration file.")
        return

    # 遍历配置中的每个文件和对应的保留键
    for file_name, keep_keys in server_config.items():
        file_path = os.path.join(output_dir, file_name)
        if os.path.exists(file_path):
            clean_json_file(file_path, keep_keys)
        else:
            print(f"File {file_path} not found, skipping.")

    pack_to_zip(args.output_dir, args.zip_path)

if __name__ == "__main__":
    main()
