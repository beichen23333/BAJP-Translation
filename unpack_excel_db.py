import os
import sys
import sqlite3
import json
import inspect
from pathlib import Path
from setup_utils import dynamic_import_module, convert_to_basic_types, pack_to_zip, deserialize_flatbuffer

def unpack_json_from_db(db_path: Path, output_dir: Path, flatbuffers_dir: Path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    output_dir.mkdir(parents=True, exist_ok=True)

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table_info in tables:
        table_name = table_info[0]
        table_type = table_name.replace("DBSchema", "Excel")
        json_path = output_dir / f"{table_type}.json"

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        columns = [col[1] for col in columns_info]

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        json_data = []
        for row in rows:
            entry = {}
            for col, value in zip(columns, row):
                if col == "Bytes":
                    # 反序列化 FlatBuffers 数据
                    try:
                        deserialized_data = deserialize_flatbuffer(value, flatbuffers_dir, table_type)
                        if deserialized_data:
                            entry.update(deserialized_data)
                    except Exception as e:
                        print(f"Error processing {table_type}: {e}")
                else:
                    entry[col] = value
            json_data.append(entry)

        if json_data:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=4)
            print(f"Unpacked {table_name} to {json_path}")

    conn.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Unpack ExcelDB.db and pack JSON files into a ZIP archive.")
    parser.add_argument("--db_path", type=Path, required=True, help="Path to the ExcelDB.db file.")
    parser.add_argument("--output_dir", type=Path, default="./unpacked", help="Directory to save the unpacked files.")
    parser.add_argument("--flatbuffers_dir", type=Path, default="./Extracted/FlatData", help="Directory containing FlatBuffers class files.")
    parser.add_argument("--zip_path", type=Path, default="./unpacked/UnpackedExcel.zip", help="Path to save the ZIP archive.")
    args = parser.parse_args()
    
    unpack_json_from_db(args.db_path, args.output_dir, args.flatbuffers_dir)
    pack_to_zip(args.output_dir, args.zip_path)

if __name__ == "__main__":
    main()
