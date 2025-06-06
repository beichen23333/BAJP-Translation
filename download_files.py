import os
import requests
from pathlib import Path
import sqlite3
import json
import flatbuffers

def unpack_json_from_db(db_path: Path, output_dir: Path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)

    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_info in tables:
        table_name = table_info[0]
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
                    try:
                        # 动态加载 FlatBuffers 类
                        flatbuffer_class = getattr(flatbuffers, table_type, None)
                        if not flatbuffer_class:
                            print(f"Warning: FlatBuffers class for {table_type} not found. Skipping this table.")
                            break
                        flatbuffer_obj = getattr(flatbuffer_class, "GetRootAs")(bytes_data, 0)
                        
                        # 提取 FlatBuffers 中的字段
                        for field in columns:
                            if field != "Bytes":
                                accessor = getattr(flatbuffer_obj, field, None)
                                if callable(accessor):
                                    entry[field] = accessor()
                                else:
                                    entry[field] = None
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
