import json
import os
import zipfile
import shutil
from setup_utils import read_json, extract_zip

ba_env_path1 = 'ba.env'
ba_env_path2 = 'BA-Assets-TableBundles/ba.env'
config_path = '配置.json'

def read_ba_version(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('BA_VERSION_NAME='):
                return line.strip().split('=')[1]
    return None

def compare_json_files(folder1, folder2, config):
    for file_name, keys in config.items():
        file_path1 = os.path.join(folder1, file_name)
        file_path2 = os.path.join(folder2, file_name)
        
        if not os.path.exists(file_path1) or not os.path.exists(file_path2):
            print(f"文件 {file_name} 在其中一个文件夹中不存在，跳过对比。")
            continue
        
        with open(file_path1, 'r', encoding='utf-8') as file1, open(file_path2, 'r', encoding='utf-8') as file2:
            data1 = json.load(file1)
            data2 = json.load(file2)
            
            key = keys[0]
            # 获取文件1中所有键值
            data1_keys = {item[key] for item in data1}
            # 保留文件2中键值不在文件1中的条目
            filtered_data2 = [item for item in data2 if item[key] not in data1_keys]
            
            # 将过滤后的数据写回文件
            with open(file_path2, 'w', encoding='utf-8') as file2:
                json.dump(filtered_data2, file2, ensure_ascii=False, indent=4)
        
        print(f"已处理文件 {file_name}，删除了与文件1中相同的 {key} 对应的条目。")

def main():
    version1 = read_ba_version(ba_env_path1)
    version2 = read_ba_version(ba_env_path2)
    
    if version1 != version2:
        print(f"版本不同，BA_VERSION_NAME1={version1}, BA_VERSION_NAME2={version2}")
        
        # 读取配置文件
        config = read_json(config_path)
        db_schema = config.get("DBSchema", {}).get("日服", {})
        
        # 解压zip文件
        extract_to1 = 'extracted_1'
        extract_to2 = 'extracted_2'
        os.makedirs(extract_to1, exist_ok=True)
        os.makedirs(extract_to2, exist_ok=True)
        
        extract_zip(f'BA-Assets-TableBundles/日服{version2}.zip', extract_to1)
        extract_zip(f'BA-Assets-TableBundles/日服{version1}.zip', extract_to2)
        
        # 比较json文件
        compare_json_files(extract_to1, extract_to2, db_schema)
        
        # 将过滤后的文件移动到BA-Text/日服
        processed_folder = 'BA-Text/日服'
        os.makedirs(processed_folder, exist_ok=True)
        for file_name in db_schema.keys():
            src_path = os.path.join(extract_to2, file_name)
            dst_path = os.path.join(processed_folder, file_name)
            if os.path.exists(src_path):
                shutil.move(src_path, dst_path)
            else:
                print(f"警告: 文件 {file_name} 不存在于 {extract_to2}")

        # 清理解压文件夹
        shutil.rmtree(extract_to1)
        shutil.rmtree(extract_to2)
    else:
        print("版本相同，无需处理。")

if __name__ == "__main__":
    main()
