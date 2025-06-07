import os
import sys
import requests
from pathlib import Path
import sqlite3
import json
import importlib.util

def download_file(url: str, output_file: Path):
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def dynamic_import_module(module_path: Path, module_name: str):
    """
    动态导入模块
    """
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def unpack_json_from_db(db_path: Path, output_dir: Path, flatbuffers_dir: Path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_info in tables:
        table_name = table_info[0]
        table_type = table_name.replace("DBSchema", "Excel")
        json_path = output_dir / f"{table_type}.json"

        # 获取表的列信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        # 获取表中的所有数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        # 解析每一行数据
        json_data = []
        for row in rows:
            entry = {}
            for col, value in zip(columns, row):
                if col == "Bytes":
                    # 反序列化 FlatBuffers 数据
                    bytes_data = value
                    try:
                        # 动态导入 FlatBuffers 类
                        flatbuffer_class_name = table_type
                        flatbuffer_module_path = flatbuffers_dir / f"{flatbuffer_class_name}.py"
                        if not flatbuffer_module_path.exists():
                            print(f"FlatBuffers class file {flatbuffer_module_path} not found.")
                            continue

                        flatbuffer_module = dynamic_import_module(flatbuffer_module_path, flatbuffer_class_name)
                        flatbuffer_class = getattr(flatbuffer_module, flatbuffer_class_name)

                        # 获取 FlatBuffers 对象
                        flatbuffer_obj = flatbuffer_class.GetRootAs(bytes_data, 0)

                        # 动态获取 FlatBuffers 对象的字段
                        for field_name in dir(flatbuffer_obj):
                            if not field_name.startswith("__") and not callable(getattr(flatbuffer_obj, field_name)):
                                field_value = getattr(flatbuffer_obj, field_name)()
                                entry[field_name] = field_value
                    except Exception as e:
                        print(f"Error processing {table_type}: {e}")
                else:
                    entry[col] = value
            json_data.append(entry)

        # 如果表中有数据且没有跳过，则保存为 JSON 文件
        if json_data:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"Unpacked {table_name} to {json_path}")

    conn.close()

def download_and_unpack_excel_db(env_file: Path, output_dir: Path, temp_dir: Path, flatbuffers_dir: Path):
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            env_vars[key] = value
    
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL")
    if not ba_server_url:
        raise ValueError("ADDRESSABLE_CATALOG_URL not found in the environment file.")
    
    # 下载 ExcelDB.db 文件
    excel_db_url = f"{ba_server_url}/TableBundles/ExcelDB.db"
    excel_db_path = output_dir / "ExcelDB.db"
    download_file(excel_db_url, excel_db_path)
    
    # 解包 ExcelDB.db 文件
    print(f"Unpacking {excel_db_path} to {temp_dir}...")
    unpack_json_from_db(excel_db_path, temp_dir, flatbuffers_dir)
    
    print(f"Unpacked files are saved in {temp_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download ExcelDB.db from BA_SERVER_URL and unpack it.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_dir", type=Path, default="./downloads", help="Directory to save the downloaded files.")
    parser.add_argument("--temp_dir", type=Path, default="./temp", help="Temporary directory to unpack the files.")
    args = parser.parse_args()
    
    EXTRACT_DIR = "Extracted"
    flatbuffers_dir = Path(EXTRACT_DIR) / "FlatData"  # 确保路径正确
    download_and_unpack_excel_db(args.env_file, args.output_dir, args.temp_dir, flatbuffers_dir)
