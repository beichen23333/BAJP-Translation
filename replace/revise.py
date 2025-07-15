import os
import json
from pathlib import Path
from zhconv import convert
import zipfile
import tempfile


def convert_traditional_to_simplified(text: str) -> str:
    """将繁体中文转换为简体中文"""
    return convert(text, 'zh-cn')

def load_replacement_rules(replace_file: Path) -> dict:
    """读取替换名词文件"""
    replacements = {}
    try:
        with open(replace_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                original = lines[i]
                replacement = lines[i+1]
                replacements[original] = replacement
        return replacements
    except Exception as e:
        print(f"Error loading replacement file: {e}")
        return {}

def process_value(value: str, replacements: dict) -> str:
    """处理单个文本值"""
    if not isinstance(value, str):
        return value
    
    simplified = convert_traditional_to_simplified(value)
    
    for original, replacement in replacements.items():
        simplified = simplified.replace(original, replacement)
    
    return simplified

def process_json_file(file_path: Path, replacements: dict):
    """处理单个JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    new_value = process_value(value, replacements)
                    if new_value != value:
                        data[key] = new_value
                        modified = True
                elif isinstance(value, list):
                    for i in range(len(value)):
                        if isinstance(value[i], str):
                            new_value = process_value(value[i], replacements)
                            if new_value != value[i]:
                                value[i] = new_value
                                modified = True
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str):
                            new_value = process_value(value, replacements)
                            if new_value != value:
                                item[key] = new_value
                                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False

def create_zip_from_directory(directory: Path, output_zip: Path):
    """将目录中的所有文件压缩为ZIP"""
    try:
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = Path(root) / file
                    arcname = os.path.relpath(file_path, directory)
                    zipf.write(file_path, arcname)
        print(f"Created ZIP archive: {output_zip}")
        return True
    except Exception as e:
        print(f"Error creating ZIP file: {e}")
        return False

def process_all_json_files(input_dir: Path, output_zip: Path, replacements: dict):
    """处理目录中的所有JSON文件并打包为ZIP"""
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # 复制所有文件到临时目录
        for item in input_dir.glob('*'):
            if item.is_file():
                shutil.copy(item, temp_dir_path)
            elif item.is_dir():
                shutil.copytree(item, temp_dir_path / item.name)
        
        # 处理JSON文件
        print("Starting JSON file processing...")
        processed_count = 0
        for root, _, files in os.walk(temp_dir_path):
            for file in files:
                if file.lower().endswith('.json'):
                    file_path = Path(root) / file
                    if process_json_file(file_path, replacements):
                        processed_count += 1
        
        print(f"Processed {processed_count} JSON files")
        
        # 创建ZIP文件
        if not create_zip_from_directory(temp_dir_path, output_zip):
            return False
        
    return True

def main():
    # 输入输出配置
    input_dir = Path("BA-Text/processed")  # 第一个脚本的输出目录
    replace_file = Path("替换名词.txt")     # 名词替换规则文件
    output_zip = Path("BA-Text/日服.zip")   # 最终输出的ZIP文件
    
    # 确保输出目录存在
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取替换规则
    replacements = load_replacement_rules(replace_file)
    if not replacements:
        print("No replacement rules loaded. Continuing with only traditional to simplified conversion.")
    
    print(f"Loaded {len(replacements)} replacement rules")
    
    # 处理并打包文件
    if not process_all_json_files(input_dir, output_zip, replacements):
        print("Failed to process files")
        return
    
    print(f"Successfully created {output_zip}")

if __name__ == "__main__":
    main()
