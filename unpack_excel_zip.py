import os
import json
import argparse
import sys
import tempfile
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ThreadPoolExecutor, as_completed
from lib.encryption import zip_password
from setup_utils import deserialize_flatbuffer
from unpack_excel_db import safe_deserialize
import importlib
from extractor import TableExtractorImpl

def process_zip_file(zip_path, flatbuffers_dir, config_file, server,output_zip_path=None, output_dir=None,zip_filename="Excel.zip", threads=4):
    temp_path = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="excel_"))
    shutil.rmtree(temp_path, ignore_errors=True)
    temp_path.mkdir(parents=True, exist_ok=True)
    json_output_dir = temp_path / "json_output"
    json_output_dir.mkdir(exist_ok=True)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        server_config = config["DBSchema"][server]

        needed_files = {}
        for json_name, keep_fields in server_config.items():
            if not json_name.endswith("Table.json"):
                continue
            table_name = json_name[:-5]
            bytes_name = f"{table_name.lower()}.bytes"
            needed_files[bytes_name] = (table_name, json_name)

        password = zip_password(zip_filename)
        extracted_files = set()
        with ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.filename.lower() in needed_files:
                    zf.extract(info, temp_path, pwd=password)
                    extracted_files.add(info.filename.lower())
                    print(f"已解压: {info.filename}")

        missing = set(needed_files) - extracted_files
        if missing:
            print(f"未找到以下文件: {missing}")

        tasks = []
        for bytes_name in extracted_files:
            table_name, json_name = needed_files[bytes_name]
            keep_fields = server_config[json_name]
            tasks.append((
                temp_path / bytes_name,
                flatbuffers_dir,
                None,
                table_name,
                keep_fields,
            ))

        processed_files = []
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {pool.submit(process_single_file, *t): t for t in tasks}
            for fut in as_completed(futures):
                bytes_path, result = fut.result()
                if result is not None:
                    out_json = json_output_dir / f"{bytes_path.stem}.json"
                    with open(out_json, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    processed_files.append(out_json.name)

        if not output_zip_path:
            output_zip_path = zip_path.with_name(f"processed_{zip_path.name}")
        with ZipFile(output_zip_path, "w", ZIP_DEFLATED) as zf:
            for json_file in json_output_dir.glob("*.json"):
                zf.write(json_file, json_file.name)

        print(f"处理完成，共解析 {len(processed_files)} 个文件")
        print(f"输出ZIP: {output_zip_path}")
        return processed_files, output_zip_path

    except Exception as e:
        print(f"处理过程中出错: {e}")
        return [], None
    finally:
        if not output_dir:
            shutil.rmtree(temp_path, ignore_errors=True)


def process_single_file(bytes_path, _flatbuffers_dir, _xor_table_name,table_name, keep_fields):
    try:
        extractor = TableExtractorImpl(table_name)
        obj = extractor.bytes2json(bytes_path)
        if obj is None:
            print(f"反序列化 {bytes_path.name} 返回 None")
            return None, None

        def _filter(item):
            return {k: v for k, v in item.items() if k in keep_fields}

        if isinstance(obj, list):
            filtered = [_filter(row) for row in obj]
        else:
            filtered = _filter(obj)

        return bytes_path, filtered

    except Exception as e:
        print(f"处理 {bytes_path.name} 失败: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser(description="处理 Excel 压缩包")
    parser.add_argument("--zip_path", type=Path, required=True, help="输入的ZIP文件路径")
    parser.add_argument("--output_dir", type=Path, default=None, help="自定义解压目录(默认使用临时目录)")
    parser.add_argument("--flatbuffers_dir", type=Path, required=True, help="无用但保持兼容")
    parser.add_argument("--server", type=str, required=True, choices=["日服", "国服", "国际服"])
    parser.add_argument("--config_file", type=Path, required=True)
    parser.add_argument("--zip_filename", type=str, default="Excel.zip", help="用于生成密码的ZIP文件名(默认: Excel.zip)")
    parser.add_argument("--output_zip", type=Path, default=None, help="输出ZIP文件路径(默认: 输入文件同目录下processed_前缀文件)")
    parser.add_argument("--threads", type=int, default=4)

    args = parser.parse_args()

    process_zip_file(
        args.zip_path,
        args.flatbuffers_dir,
        args.config_file,
        args.server,
        args.output_zip,
        args.output_dir,
        args.zip_filename,
        args.threads,
    )


if __name__ == "__main__":
    main()
