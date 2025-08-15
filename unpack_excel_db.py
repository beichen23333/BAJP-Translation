import os
import json
import sqlite3
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from setup_utils import deserialize_flatbuffer

def safe_deserialize(bytes_data, flatbuffers_dir, table_name, keep_keys):
    if not bytes_data:
        return None  
    try:
        data = deserialize_flatbuffer(bytes_data, flatbuffers_dir, table_name)
        return {k: data[k] for k in keep_keys if k in data} if data else None
    except Exception:
        return None

def process_table(args):
    task_id, db_path, flatbuffers_dir, output_dir, db_table, json_file, keep_keys = args
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    json_path = output_dir / json_file
    json_data = []
    
    try:
        cursor.execute(f"SELECT Bytes FROM {db_table}")
        rows = cursor.fetchall()
        # 禁用tqdm的内部进度条
        for (bytes_data,) in rows:
            deserialized = safe_deserialize(
                bytes_data, 
                flatbuffers_dir,
                json_file.replace(".json", ""),
                keep_keys
            )
            if deserialized:
                json_data.append(deserialized)
                
        if json_data:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            return (task_id, str(json_path), len(json_data))
    finally:
        conn.close()
    
    return (task_id, None, 0)

def process_tables_parallel(db_path, output_dir, flatbuffers_dir, config_file, server, max_workers=8):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    server_config = config["DBSchema"][server]
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    valid_tables = []
    for idx, (json_file, keep_keys) in enumerate(server_config.items()):
        db_table = json_file.replace("Excel.json", "DBSchema")
        cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (db_table,))
        if cursor.fetchone():
            tasks.append((
                idx, db_path, flatbuffers_dir, 
                output_dir, db_table, json_file, keep_keys
            ))
            valid_tables.append(db_table)
    
    conn.close()
    
    if not valid_tables:
        print("没有有效的表需要处理")
        return []
    
    print(f"开始处理 {len(valid_tables)} 个表 (线程数: {max_workers})")
    
    processed_files = []
    total_records = 0
    last_report = 0
    report_interval = max(1, len(valid_tables) // 5)  # 每20%进度报告一次
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_table, task): task[0] for task in tasks}
        
        for i, future in enumerate(as_completed(futures), 1):
            task_id, result, records = future.result()
            if result:
                processed_files.append(result)
                total_records += records

            if i - last_report >= report_interval or i == len(valid_tables):
                progress = int(100 * i / len(valid_tables))
                print(f"进度: {progress}% ({i}/{len(valid_tables)}) - 已处理 {total_records} 条记录")
                last_report = i
    
    print(f"\n处理完成! 共处理 {len(processed_files)} 个表, {total_records} 条记录")
    return processed_files

def main():
    parser = argparse.ArgumentParser(description="处理")
    parser.add_argument("--db_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, default="./unpacked")
    parser.add_argument("--flatbuffers_dir", type=Path, required=True)
    parser.add_argument("--config_file", type=Path, required=True)
    parser.add_argument("--server", type=str, required=True, choices=['日服', '国服', '国际服'])
    parser.add_argument("--zip_path", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=8, help="线程数")
    
    args = parser.parse_args()
    
    processed_files = process_tables_parallel(
        args.db_path,
        args.output_dir,
        args.flatbuffers_dir,
        args.config_file,
        args.server,
        args.threads
    )
    
    if processed_files:
        print("\n正在打包文件...")
        with ZipFile(args.zip_path, 'w', ZIP_DEFLATED) as zf:
            for i, file_path in enumerate(processed_files, 1):
                zf.write(file_path, os.path.basename(file_path))
                if i % 20 == 0 or i == len(processed_files):  # 每20文件或最后报告一次
                    print(f"已打包 {i}/{len(processed_files)} 文件")
        print(f"\n✅ 所有文件已打包到 {args.zip_path}")
    else:
        print("⚠️ 未处理任何文件")
        sys.exit(1)

if __name__ == "__main__":
    main()
