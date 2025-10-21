import argparse
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import tempfile

def read_json(file_path: str) -> List[Dict[str, Any]]:
    """读取JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(data: List[Dict[str, Any]], file_path: str) -> None:
    """写入JSON文件"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def filter_json_data(data: List[Dict[str, Any]], keys_to_keep: List[str]) -> List[Dict[str, Any]]:
    """过滤JSON数据，只保留指定的键"""
    return [{k: item[k] for k in keys_to_keep if k in item} for item in data]

def extract_zip(zip_path: str, extract_to: str) -> None:
    """解压ZIP文件"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def process_and_create_zip(input_dir: str, output_zip: str, config: Dict[str, Dict[str, List[str]]]) -> None:
    """
    处理文件并直接创建ZIP到输出路径
    跳过所有不在config中的文件
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_zip)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in ['DBSchema', 'ExcelTable']:
            if folder not in config:
                continue
                
            input_folder = Path(input_dir) / folder
            if not input_folder.exists():
                print(f"警告: 目录不存在 {input_folder}")
                continue

            for file_name, keys_to_keep in config[folder].items():
                input_file = input_folder / file_name
                if not input_file.exists():
                    print(f"警告: 文件未找到 {input_file}")
                    continue

                try:
                    # 读取并过滤数据
                    original_data = read_json(input_file)
                    filtered_data = filter_json_data(original_data, keys_to_keep)
                    
                    # 创建临时文件
                    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
                    write_json(filtered_data, temp_file.name)
                    temp_file.close()
                    
                    # 添加到ZIP文件
                    zip_path = os.path.join(folder, file_name)
                    zipf.write(temp_file.name, zip_path)
                    print(f"已处理并添加到ZIP: {zip_path}")
                    
                    # 删除临时文件
                    os.unlink(temp_file.name)
                except Exception as e:
                    print(f"处理 {folder}/{file_name} 时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description="根据配置文件处理ZIP文件中的JSON数据并直接输出ZIP")
    parser.add_argument('zip_path', help='输入ZIP文件路径')
    parser.add_argument('config_path', help='config.json配置文件路径')
    parser.add_argument('output_zip', help='输出ZIP文件路径')
    args = parser.parse_args()

    # 创建临时目录用于解压
    temp_extract_dir = tempfile.mkdtemp()

    try:
        # 解压输入ZIP文件
        print(f"正在解压 {args.zip_path} 到临时目录...")
        extract_zip(args.zip_path, temp_extract_dir)

        # 读取配置文件
        print(f"正在读取配置文件 {args.config_path}...")
        config = read_json(args.config_path)

        # 直接处理文件并创建输出ZIP
        print(f"正在处理文件并创建输出ZIP {args.output_zip}...")
        process_and_create_zip(temp_extract_dir, args.output_zip, config)

        print(f"处理完成！结果已保存到: {args.output_zip}")
    finally:
        # 清理临时目录
        shutil.rmtree(temp_extract_dir)

if __name__ == '__main__':
    main()
