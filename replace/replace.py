import os
import re
import json
import argparse
from pathlib import Path
import zipfile
import tempfile
import shutil
from typing import Dict, List, Optional, Any

def debug_print(title: str, content: Any, level: int = 1):
    """带缩进的调试输出"""
    indent = "  " * level
    print(f"{indent}=== {title} ===")
    if isinstance(content, (dict, list)):
        print(f"{indent}{json.dumps(content, indent=2, ensure_ascii=False)}")
    else:
        print(f"{indent}{content}")

def read_ba_versions(env_file_path: Path) -> Dict[str, str]:
    """读取ba.env文件中的版本信息"""
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        debug_print("Reading ba.env", content)
        
        pattern = r'BA_VERSION_NAME(_CN|_GL)?\s*=\s*([^\n]+)'
        matches = re.findall(pattern, content)
        
        versions = {}
        for match in matches:
            suffix = match[0] if match[0] else ''
            version = match[1].strip()
            key = f'BA_VERSION_NAME{suffix}'
            versions[key] = version
            
        debug_print("Parsed versions", versions)
        return versions
    except Exception as e:
        print(f"❌ Error reading {env_file_path}: {e}")
        return {}

def extract_zip(zip_path: Path, extract_to: str) -> bool:
    """解压ZIP文件到指定目录"""
    debug_print(f"Extracting {zip_path}", f"to {extract_to}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            debug_print("ZIP contents", file_list[:5])  # 显示前5个文件
            zip_ref.extractall(extract_to)
        print(f"✅ Successfully extracted {zip_path}")
        return True
    except Exception as e:
        print(f"❌ Error extracting {zip_path}: {e}")
        return False

def get_server_version_key(server_type: str) -> Optional[str]:
    """根据服务器类型返回对应的版本key"""
    server_map = {
        '日服': 'BA_VERSION_NAME',
        '国服': 'BA_VERSION_NAME_CN',
        '国际服': 'BA_VERSION_NAME_GL'
    }
    debug_print(f"Get version key for {server_type}", f"Result: {server_map.get(server_type)}")
    return server_map.get(server_type)

def load_config(config_path: Path) -> Dict[str, Any]:
    """读取配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        debug_print("Loaded config", config)
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return {}

def process_json_files(jp_dir: Path, other_dir: Path, config: Dict[str, Any], server_type: str):
    """处理JSON文件，将其他服的文本替换到日服文件中"""
    debug_print(f"Processing JSON for {server_type}", f"JP dir: {jp_dir}, Other dir: {other_dir}")
    
    if 'DBSchema' not in config:
        print("❌ Missing DBSchema in config")
        return
    
    if server_type not in config['DBSchema']:
        print(f"❌ No schema found for {server_type}")
        debug_print("Available schemas", list(config['DBSchema'].keys()))
        return
    
    schema = config['DBSchema'][server_type]
    debug_print(f"Using schema for {server_type}", schema)
    
    for json_file, keys in schema.items():
        jp_file = jp_dir / json_file
        other_file = other_dir / json_file
        
        debug_print("Processing file", f"{json_file} (Keys: {keys})")
        
        if not jp_file.exists():
            print(f"⚠️ JP file not found: {jp_file}")
            continue
        if not other_file.exists():
            print(f"⚠️ {server_type} file not found: {other_file}")
            continue
        
        # 读取文件内容
        try:
            with open(jp_file, 'r', encoding='utf-8') as f:
                jp_data = json.load(f)
            with open(other_file, 'r', encoding='utf-8') as f:
                other_data = json.load(f)
                
            debug_print("JP data sample", jp_data[:1] if isinstance(jp_data, list) else jp_data)
            debug_print(f"{server_type} data sample", other_data[:1] if isinstance(other_data, list) else other_data)
        except Exception as e:
            print(f"❌ Error reading {json_file}: {e}")
            continue
        
        if not keys or len(keys) < 2:
            print(f"⚠️ Invalid keys for {json_file}: {keys}")
            continue
        
        id_key, *text_keys = keys
        debug_print("Using keys", {"ID": id_key, "Text": text_keys})
        
        # 创建ID映射表
        other_id_map = {}
        for item in other_data:
            if id_key in item:
                other_id_map[item[id_key]] = {k: item.get(k) for k in text_keys}
        
        debug_print("ID mapping stats", 
                   f"Total IDs: {len(other_id_map)}, Sample: {list(other_id_map.items())[:3]}")
        
        # 更新日服数据
        updated = 0
        for item in jp_data:
            if id_key in item and item[id_key] in other_id_map:
                for k in text_keys:
                    if k in item and k in other_id_map[item[id_key]]:
                        old_value = item[k]
                        new_value = other_id_map[item[id_key]][k]
                        if new_value and new_value != old_value:
                            item[k] = new_value
                            updated += 1
                            debug_print("Replacement", 
                                       f"ID: {item[id_key]}, Key: {k}\n"
                                       f"Old: {old_value}\n"
                                       f"New: {new_value}", level=2)
        
        # 保存更新后的文件
        try:
            with open(jp_file, 'w', encoding='utf-8') as f:
                json.dump(jp_data, f, ensure_ascii=False, indent=2)
            print(f"✅ Updated {json_file} ({updated} replacements)")
        except Exception as e:
            print(f"❌ Error saving {json_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Process BA asset bundles.")
    parser.add_argument("--env_file", type=Path, default="BA-Assets-TableBundles/ba.env", 
                       help="Path to the ba.env file.")
    parser.add_argument("--server", type=str, required=True,
                       choices=['国服', '国际服'], 
                       help="Server type to process (国服 or 国际服)")
    parser.add_argument("--config", type=Path, default="config.json",
                       help="Path to the config file")
    args = parser.parse_args()
    
    debug_print("Script started", f"Args: {vars(args)}")
    
    # 读取版本信息
    versions = read_ba_versions(args.env_file)
    if not versions:
        print("❌ No version information found")
        return
    
    debug_print("Detected versions", versions)
    
    # 读取配置文件
    config = load_config(args.config)
    if not config:
        print("❌ No valid config found")
        return
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        debug_print("Created temp dir", temp_dir_path)
        
        # ================= 日服处理 =================
        jp_version_key = 'BA_VERSION_NAME'
        jp_version = versions.get(jp_version_key)
        jp_dir = temp_dir_path / "jp_zip"
        
        if not jp_version:
            print("❌ No Japanese version information found")
            return
            
        jp_zip_path = Path("BA-Text") / f"日服{jp_version}.zip"
        debug_print("Japanese ZIP path", jp_zip_path)
        
        if not jp_zip_path.exists():
            print(f"❌ Japanese server ZIP not found: {jp_zip_path}")
            return
            
        os.makedirs(jp_dir, exist_ok=True)
        if not extract_zip(jp_zip_path, jp_dir):
            print("❌ Failed to extract Japanese server ZIP")
            return
        
        # ================= 目标服务器处理 =================
        server_version_key = get_server_version_key(args.server)
        if not server_version_key:
            print(f"❌ Invalid server type: {args.server}")
            return
            
        server_version = versions.get(server_version_key)
        if not server_version:
            print(f"❌ No version found for {args.server} ({server_version_key})")
            return
            
        # 确定ZIP路径
        if args.server == '国服':
            server_zip_path = Path("BA-Text") / f"国服{server_version}.zip"
        else:
            server_zip_path = Path("BA-Assets-TableBundles") / f"国际服{server_version}.zip"
        
        debug_print(f"{args.server} ZIP path", server_zip_path)
        
        if not server_zip_path.exists():
            print(f"❌ {args.server} ZIP not found: {server_zip_path}")
            return
            
        server_dir = temp_dir_path / f"{args.server}_zip"
        os.makedirs(server_dir, exist_ok=True)
        
        if not extract_zip(server_zip_path, server_dir):
            print(f"❌ Failed to extract {args.server} ZIP")
            return
        
        # ================= JSON处理 =================
        print("\n" + "="*50)
        print(f"🌟 Processing JSON files for {args.server}")
        print("="*50)
        process_json_files(jp_dir, server_dir, config, args.server)
        
        print("\n" + "="*50)
        print("✅ Processing completed. Temporary files will be deleted.")
        print("="*50)

if __name__ == "__main__":
    main()
