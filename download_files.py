import os
import sys
import requests
from pathlib import Path
import sqlite3
import json
import flatbuffers

def download_file(url: str, output_file: Path):
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def unpack_json_from_db(db_path: Path, output_dir: Path):
    import importlib
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    # 在函数外添加 FlatBuffers 生成目录到 sys.path
    flatbuffers_generated_dir = output_dir / "FlatData"
    if str(flatbuffers_generated_dir) not in sys.path:
        sys.path.append(str(flatbuffers_generated_dir))
    
    for table_info in tables:
        table_name = table_info[0]
        table_type = table_name.replace("DBSchema", "Excel")
        json_path = output_dir / f"{table_type}.json"

        # 获取列信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        json_data = []
        for row in rows:
            entry = {}
            flat_data = {}  # 存储解析出的FlatBuffers数据
            has_bytes = False
            
            for col, value in zip(columns, row):
                if col == "Bytes":
                    has_bytes = True
                    bytes_data = value
                    
                    try:
                        # 动态导入对应的FlatBuffers模块
                        module = importlib.import_module(table_type)
                        # 获取FlatBuffers类
                        flatbuffer_class = getattr(module, table_type)
                        
                        # 解析FlatBuffers数据
                        flatbuffer_obj = flatbuffer_class.GetRootAs(bytes_data, 0)
                        
                        # 获取所有可能的字段
                        field_names = [attr for attr in dir(flatbuffer_class) 
                                      if not attr.startswith('_') and 
                                      not attr.startswith('GetRoot') and 
                                      callable(getattr(flatbuffer_class, attr))]
                        
                        # 尝试获取每个字段的值
                        for field in field_names:
                            try:
                                # 调用方法获取字段值
                                method = getattr(flatbuffer_class, field)
                                field_value = method(flatbuffer_obj)
                                flat_data[field] = field_value
                            except Exception as e:
                                # 某些方法可能不是字段访问器，忽略错误
                                pass
                        
                    except Exception as e:
                        print(f"Error processing {table_type}: {e}")
                        entry[col] = list(bytes_data)  # 原始字节作为备选
                else:
                    entry[col] = value
            
            if has_bytes:
                entry["FlatData"] = flat_data
                
            json_data.append(entry)

        if json_data:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"Unpacked {table_name} to {json_path}")

    conn.close()


def download_and_unpack_excel_db(env_file: Path, output_dir: Path, temp_dir: Path):
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
    
    # 确保生成的 FlatBuffers 类文件所在的目录被添加到 sys.path 中
    flatbuffers_generated_dir = output_dir / "FlatData"
    if str(flatbuffers_generated_dir) not in sys.path:
        sys.path.append(str(flatbuffers_generated_dir))
    
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
