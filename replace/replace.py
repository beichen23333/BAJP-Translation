import os
import re
import json
import argparse
from pathlib import Path
import zipfile
import tempfile
from typing import Dict, List, Optional, Any

def read_ba_versions(env_file_path: Path) -> Dict[str, str]:
    """读取ba.env文件中的版本信息"""
    versions = {}
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = r'BA_VERSION_NAME(_CN|_GL)?\s*=\s*([^\n]+)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            suffix = match[0] if match[0] else ''
            version = match[1].strip()
            key = f'BA_VERSION_NAME{suffix}'
            versions[key] = version
            
        return versions
    except Exception as e:
        print(f"Error reading {env_file_path}: {e}")
        return {}

def extract_zip(zip_path: Path, extract_to: str) -> bool:
    """解压ZIP文件到指定目录"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Successfully extracted {zip_path} to {extract_to}")
        return True
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return False

def get_server_version_key(server_type: str) -> Optional[str]:
    """根据服务器类型返回对应的版本key"""
    server_map = {
        '日服': 'BA_VERSION_NAME',
        '国服': 'BA_VERSION_NAME_CN',
        '国际服': 'BA_VERSION_NAME_GL'
    }
    return server_map.get(server_type)

def load_config(config_path: Path) -> Dict[str, Any]:
    """读取配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def process_json_files(jp_dir: Path, other_dir: Path, config: Dict[str, Any], server_type: str):
    """处理JSON文件，将其他服的文本替换到日服文件中"""
    if 'DBSchema' not in config or server_type not in config['DBSchema']:
        print(f"No schema found for {server_type}")
        return
    
    schema = config['DBSchema'][server_type]
    
    for json_file, keys in schema.items():
        jp_file = jp_dir / json_file
        other_file = other_dir / json_file
        
        if not jp_file.exists() or not other_file.exists():
            print(f"Skipping {json_file} (not found in both directories)")
            continue
        
        try:
            with open(jp_file, 'r', encoding='utf-8') as f:
                jp_data = json.load(f)
            with open(other_file, 'r', encoding='utf-8') as f:
                other_data = json.load(f)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
        
        if not keys or len(keys) < 2:
            print(f"Invalid keys for {json_file}")
            continue
        
        id_key = keys[0]
        text_keys = keys[1:]
        
        # 创建其他服数据的ID映射
        other_id_map = {}
        for item in other_data:
            if id_key in item:
                other_id_map[item[id_key]] = {k: item.get(k) for k in text_keys}
        
        # 更新日服数据
        updated = 0
        for item in jp_data:
            if id_key in item and item[id_key] in other_id_map:
                for k in text_keys:
                    if k in item and k in other_id_map[item[id_key]]:
                        item[k] = other_id_map[item[id_key]][k]
                        updated += 1
        
        # 保存更新后的文件
        try:
            with open(jp_file, 'w', encoding='utf-8') as f:
                json.dump(jp_data, f, ensure_ascii=False, indent=2)
            print(f"Updated {json_file} with {updated} text replacements")
        except Exception as e:
            print(f"Error saving {json_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Process BA asset bundles.")
    parser.add_argument("--env_file", type=Path, default="BA-Assets-TableBundles/ba.env", 
                       help="Path to the ba.env file.")
    parser.add_argument("--server", type=str, required=True,
                       choices=['国服', '国际服'], 
                       help="Server type to process (国服 or 国际服)")
    parser.add_argument("--config", type=Path, default="配置.json",
                       help="Path to the config file")
    args = parser.parse_args()
    
    # 读取版本信息
    versions = read_ba_versions(args.env_file)
    if not versions:
        print("No version information found.")
        return
    
    print("Detected versions:")
    for key, value in versions.items():
        print(f"{key}: {value}")
    
    # 读取配置文件
    config = load_config(args.config)
    if not config:
        print("No valid config found")
        return
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        print(f"\nCreated temporary directory: {temp_dir}")
        
        # 1. 处理日服ZIP文件
        jp_version_key = 'BA_VERSION_NAME'
        jp_version = versions.get(jp_version_key)
        jp_dir = temp_dir_path / "jp_zip"
        
        if jp_version:
            jp_zip_path = Path(f"BA-Assets-TableBundles/日服{jp_version}.zip")
            if jp_zip_path.exists():
                os.makedirs(jp_dir, exist_ok=True)
                if not extract_zip(jp_zip_path, jp_dir):
                    print("Failed to extract Japanese server ZIP")
                    return
            else:
                print(f"Japanese server ZIP file not found: {jp_zip_path}")
                return
        else:
            print("No Japanese version information found")
            return
        
        # 2. 处理其他服务器ZIP文件
        server_version_key = get_server_version_key(args.server)
        if not server_version_key:
            print(f"Invalid server type: {args.server}")
            return
            
        server_version = versions.get(server_version_key)
        if not server_version:
            print(f"No version found for {args.server} ({server_version_key})")
            return
            
        server_zip_path = Path(f"BA-Assets-TableBundles/{args.server}{server_version}.zip")
        server_dir = temp_dir_path / f"{args.server}_zip"
        
        if server_zip_path.exists():
            os.makedirs(server_dir, exist_ok=True)
            if not extract_zip(server_zip_path, server_dir):
                print(f"Failed to extract {args.server} ZIP")
                return
        else:
            print(f"{args.server} ZIP file not found: {server_zip_path}")
            return
        
        # 3. 处理JSON文件
        print(f"\nProcessing JSON files for {args.server}...")
        process_json_files(jp_dir, server_dir, config, args.server)

    output_dir = Path("BA-Text/processed")
    if jp_dir.exists():
        shutil.copytree(jp_dir, output_dir, dirs_exist_ok=True)
        print(f"\nProcessed files saved to: {output_dir}")

if __name__ == "__main__":
    main()
