import os
import json
import sqlite3
import argparse
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ThreadPoolExecutor, as_completed
from setup_utils import safe_deserialize


def process_table(args):
    task_id, db_path, flatbuffers_dir, output_dir, db_table, json_file, keep_keys = args

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    json_path = output_dir / json_file
    json_data = []

    try:
        cursor.execute(f"SELECT Bytes FROM {db_table}")
        rows = cursor.fetchall()
        for (bytes_data,) in rows:
            deserialized = safe_deserialize(
                bytes_data, flatbuffers_dir,
                json_file.replace(".json", ""), keep_keys
            )
            if deserialized:
                json_data.append(deserialized)

        if json_data:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            return str(json_path), len(json_data)
    finally:
        conn.close()

    return None, 0


def process_tables_parallel(db_path, output_dir, flatbuffers_dir,config_file, server, max_workers=8):
    for p in output_dir.glob("*.json"):
        p.unlink(missing_ok=True)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    server_config = config["DBSchema"][server]
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for json_file, keep_keys in server_config.items():
        db_table = json_file.replace("Excel.json", "DBSchema")
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (db_table,)
        )
        if cursor.fetchone():
            tasks.append((
                db_path, flatbuffers_dir, output_dir,
                db_table, json_file, keep_keys
            ))
    conn.close()

    if not tasks:
        print("没有有效的表需要处理")
        return []

    print("开始处理表...")
    processed_files = []
    total_records = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_table, t) for t in tasks]
        for future in as_completed(futures):
            result_path, count = future.result()
            if result_path:
                processed_files.append(result_path)
                total_records += count

    print(f"处理完成，共生成 {len(processed_files)} 个文件，{total_records} 条记录")
    return processed_files


def main():
    parser = argparse.ArgumentParser(description="处理")
    parser.add_argument("--db_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, default="./unpacked")
    parser.add_argument("--flatbuffers_dir", type=Path, required=True)
    parser.add_argument("--config_file", type=Path, required=True)
    parser.add_argument("--server", type=str, required=True,
                        choices=["日服", "国服", "国际服"])
    parser.add_argument("--zip_path", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8, help="线程数")
    args = parser.parse_args()

    processed_files = process_tables_parallel(
        args.db_path, args.output_dir, args.flatbuffers_dir,
        args.config_file, args.server, args.threads
    )

    if processed_files:
        print("正在打包文件...")
        with ZipFile(args.zip_path, 'w', ZIP_DEFLATED) as zf:
            for f in processed_files:
                zf.write(f, Path(f).name)
        print(f"所有文件已打包到 {args.zip_path}")
    else:
        print("未处理任何文件")
        sys.exit(1)


if __name__ == "__main__":
    main()
