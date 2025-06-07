import sqlite3
import json
import flatbuffers
import os
import requests
import sys
import importlib.util
from pathlib import Path

def download_file(url: str, output_file: Path):
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def unpack_json_from_db(db_path: Path, output_dir: Path):
    # 确保FlatBuffers生成的目录在sys.path中
    flatbuffers_generated_dir = output_dir / "FlatData"
    if str(flatbuffers_generated_dir) not in sys.path:
        sys.path.append(str(flatbuffers_generated_dir))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table_info in tables:
        table_name = table_info[0]
        table_type = table_name.replace("DBSchema", "Excel")
        json_path = output_dir / f"{table_type}.json"
        
        # 获取表的所有列名
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]
        
        # 获取所有行数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        json_data = []
        
        # 尝试导入对应的FlatBuffers模块
        module_file = flatbuffers_generated_dir / f"{table_type}.py"
        if not module_file.exists():
            print(f"Warning: No FlatBuffers module found for {table_type} at {module_file}")
            continue
            
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(table_type, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            flatbuffer_class = getattr(module, table_type)
        except Exception as e:
            print(f"Error importing {table_type} module: {e}")
            continue
            
        for row in rows:
            entry = {}
            
            # 处理非Bytes列
            for col, value in zip(columns, row):
                if col != "Bytes":
                    entry[col] = value
            
            # 处理Bytes列
            bytes_idx = columns.index("Bytes") if "Bytes" in columns else None
            if bytes_idx is not None:
                bytes_data = bytes(row[bytes_idx])
                
                try:
                    # 创建FlatBuffers对象
                    flatbuffer_obj = flatbuffer_class.GetRootAs(bytes_data, 0)
                    
                    # 获取类定义中的所有属性和方法
                    class_items = dir(flatbuffer_class)
                    
                    # 提取获取字段值的方法（通常是无参方法）
                    getter_methods = [
                        m for m in class_items 
                        if callable(getattr(flatbuffer_class, m)) 
                        and not m.startswith('__')
                        and not m.startswith('GetRootAs')
                        and 'Get' not in m  # 通常数据获取方法不以"Get"开头
                    ]
                    
                    # 调用获取方法提取字段值
                    for method_name in getter_methods:
                        try:
                            method = getattr(flatbuffer_class, method_name)
                            # 尝试无参调用
                            result = method(flatbuffer_obj)
                            
                            # 特殊处理数组类型字段
                            if f"{method_name}Length" in class_items:
                                length_method = getattr(flatbuffer_class, f"{method_name}Length")
                                length = length_method(flatbuffer_obj)
                                if length > 0:
                                    array = []
                                    for i in range(length):
                                        array.append(method(flatbuffer_obj, i))
                                    entry[method_name] = array
                                else:
                                    entry[method_name] = result
                            else:
                                entry[method_name] = result
                        except Exception as e:
                            # 有些方法需要参数，跳过这些
                            continue
                except Exception as e:
                    print(f"Error processing Bytes for {table_type}: {str(e)}")
            
            # 将bytes类型字段转换为字符串（如果适用）
            for key, value in entry.items():
                if isinstance(value, bytes):
                    try:
                        entry[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        # 如果不是可解码的文本，保留原始字节
                        pass
            
            json_data.append(entry)
        
        # 保存JSON文件
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        
        print(f"Processed {table_name} ({len(json_data)} rows) => {json_path}")
    
    conn.close()

def download_and_unpack_excel_db(env_file: Path, output_dir: Path, temp_dir: Path):
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    # 读取环境变量
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                env_vars[key] = value
    
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL")
    if not ba_server_url:
        raise ValueError("ADDRESSABLE_CATALOG_URL not found in the environment file.")
    
    # 下载ExcelDB.db文件
    excel_db_url = f"{ba_server_url}/TableBundles/ExcelDB.db"
    excel_db_path = output_dir / "ExcelDB.db"
    download_file(excel_db_url, excel_db_path)
    
    # 解包ExcelDB.db文件
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
