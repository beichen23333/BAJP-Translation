import os
import requests
from pathlib import Path  # 确保导入 Path
import sqlite3
import json
import flatbuffers

# 假设 extractor 模块是外部提供的，确保它可用
from extractor import TablesExtractor  # 如果这个模块不存在，可以暂时忽略

def download_file(url: str, output_file: Path):
    """
    下载文件并保存到指定路径。
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def unpack_json_from_db(db_path: Path, output_dir: Path):
    """
    从 SQLite 数据库中提取表数据并保存为 JSON 文件。
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_info in tables:
        table_name = table_info[0]
        # 修改类名拼接逻辑
        table_type = table_name.replace("DBSchema", "ExcelTable")
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
                    flatbuffer_class = getattr(flatbuffers, table_type, None)
                    if not flatbuffer_class:
                        print(f"Warning: FlatBuffers class for {table_type} not found. Skipping this table.")
                        continue
                    flatbuffer_obj = getattr(flatbuffer_class, "GetRootAs")(bytes_data, 0)
                    
                    # 提取 FlatBuffers 中的字段
                    for field in columns:
                        if field != "Bytes":
                            accessor = getattr(flatbuffer_obj, field, None)
                            if callable(accessor):
                                entry[field] = accessor()
                            else:
                                entry[field] = None
                else:
                    entry[col] = value
            json_data.append(entry)

        # 保存为 JSON 文件
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        print(f"Unpacked {table_name} to {json_path}")

    conn.close()

def download_and_unpack_excel_db(env_file: Path, output_dir: Path, temp_dir: Path):
    """
    从环境文件中读取配置，下载 ExcelDB.db 文件并解包。
    """
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
    unpack_json_from_db(excel_db_path, temp_dir)
    
    print(f"Unpacked files are saved in {temp_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download ExcelDB.db from BA_SERVER_URL and unpack it.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_dir", type=Path, default="./downloads", help="Directory to save the downloaded files.")
    parser.add_argument("--temp_dir", type=Path, default="./temp", help="Temporary directory to unpack the files.")
    args = parser.parse_args()
    
    download_and_unpack_excel_db(args.env_file, args.output_dir, args.temp_dir)
