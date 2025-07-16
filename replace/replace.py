import os
import re
import json
import argparse
from pathlib import Path
import zipfile
import tempfile
import shutil
from typing import Dict, List, Optional, Any

def read_ba_versions(env_file_path: Path) -> Dict[str, str]:
    """读取ba.env文件中的版本信息"""
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        pattern = r'BA_VERSION_NAME(_CN|_GL)?\s*=\s*([^\n]+)'
        matches = re.findall(pattern, content)
        
        versions = {}
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
        print(f"正在解压: {zip_path.name} 到 {extract_to}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            print(f"解压文件列表 ({len(file_list)} 个文件):")
            for file in file_list[:5]:  # 只显示前5个文件作为示例
                print(f"  - {file}")
            if len(file_list) > 5:
                print(f"  ... 和 {len(file_list)-5} 更多文件")
            zip_ref.extractall(extract_to)
        print(f"解压完成: {zip_path.name}")
        return True
    except Exception as e:
        print(f"解压错误 {zip_path}: {e}")
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
    """处理JSON文件，按顺序替换文本字段"""
    if 'DBSchema' not in config:
        print("Missing DBSchema in config")
        return
    
    if server_type not in config['DBSchema']:
        print(f"No schema found for {server_type}")
        return
    
    schema = config['DBSchema'][server_type]
    
    for json_file, keys in schema.items():
        jp_file = jp_dir / json_file
        other_file = other_dir / json_file
        
        if not jp_file.exists():
            print(f"日服文件不存在: {jp_file}")
            continue
        if not other_file.exists():
            print(f"{server_type}文件不存在: {other_file}")
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
            continue

        id_key, *text_keys = keys
        
        # 创建ID映射表
        other_id_map = {}
        for item in other_data:
            if id_key in item:
                other_id_map[item[id_key]] = {
                    text_keys[i]: item.get(text_keys[i]) 
                    for i in range(len(text_keys))
                }

        # 执行替换
        updated = 0
        for item in jp_data:
            if id_key in item and item[id_key] in other_id_map:
                for i, text_key in enumerate(text_keys):
                    if text_key in item:
                        item[text_key] = other_id_map[item[id_key]][text_key]
                        updated += 1

        # 保存文件
        try:
            with open(jp_file, 'w', encoding='utf-8') as f:
                json.dump(jp_data, f, ensure_ascii=False, indent=2)
            print(f"更新文件: {json_file} (替换了 {updated} 处文本)")
        except Exception as e:
            print(f"保存文件错误 {json_file}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Process BA asset bundles.")
    parser.add_argument("--env_file", type=Path, default="BA-Assets-TableBundles/ba.env", 
                       help="Path to the ba.env file.")
    parser.add_argument("--server", type=str, required=True,
                       choices=['国服', '国际服'], 
                       help="Server type to process")
    parser.add_argument("--config", type=Path, default="config.json",
                       help="Path to the config file")
    args = parser.parse_args()
    
    # 读取版本信息
    print("\n=== 读取版本信息 ===")
    versions = read_ba_versions(args.env_file)
    if not versions:
        print("未找到版本信息")
        return
    
    print("找到的版本信息:")
    for key, value in versions.items():
        print(f"  {key}: {value}")
    
    # 读取配置文件
    print("\n=== 读取配置文件 ===")
    config = load_config(args.config)
    if not config:
        print("未找到有效配置文件")
        return
    
    print(f"配置文件加载成功，包含 {len(config.get('DBSchema', {}))} 个服务器配置")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # 处理日服ZIP
        jp_version = versions.get('BA_VERSION_NAME')
        jp_zip_path = Path("BA-Text") / f"日服{jp_version}.zip"
        jp_dir = temp_dir_path / "jp_zip"
        
        print("\n=== 处理日服资源 ===")
        if not extract_zip(jp_zip_path, jp_dir):
            return
        
        # 处理目标服务器ZIP
        server_version_key = get_server_version_key(args.server)
        server_version = versions.get(server_version_key)
        
        if args.server == '国服':
            server_zip_path = Path("BA-Text") / f"国服{server_version}.zip"
        else:
            server_zip_path = Path("BA-Assets-TableBundles") / f"国际服{server_version}.zip"
            
        server_dir = temp_dir_path / f"{args.server}_zip"
        
        print(f"\n=== 处理{args.server}资源 ===")
        if not extract_zip(server_zip_path, server_dir):
            return
        
        # 处理JSON文件
        print(f"\n=== 处理JSON文件 ===")
        process_json_files(jp_dir, server_dir, config, args.server)
        
        # 保存结果到processed目录
        output_dir = Path("BA-Text") / "processed"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        print(f"\n=== 保存处理结果到 {output_dir} ===")
        for root, _, files in os.walk(jp_dir):
            for file in files:
                src_path = Path(root) / file
                rel_path = src_path.relative_to(jp_dir)
                dest_path = output_dir / rel_path
                
                dest_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(src_path, dest_path)
                print(f"已保存: {rel_path}")
        
        print("\n处理完成！所有文件已保存到 BA-Text/processed 目录")

if __name__ == "__main__":
    main()
