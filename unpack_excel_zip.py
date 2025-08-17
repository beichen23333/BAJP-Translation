import os
import json
import argparse
import sys
import tempfile
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from concurrent.futures import ThreadPoolExecutor, as_completed
from extractor import TableExtractorImpl
from lib.encryption import zip_password
from utils.config import Config

def filter_json(data: list, keep_fields: list) -> list:
    if not isinstance(data, list):
        return data
    return [{k: item[k] for k in keep_fields if k in item} for item in data]

def process_single_file(bytes_path: Path,table_extractor: TableExtractorImpl,json_name: str,keep_fields: list,output_dir: Path):
    try:
        print(f"开始处理 {bytes_path.name}")
        data = table_extractor.bytes2json(bytes_path)
        if data is None:
            print(f"处理 {bytes_path.name} 失败")
            return json_name, []
        data = filter_json(data, keep_fields)
        json_path = output_dir / f"{json_name}"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已写入 {json_path}")
        return json_name, data

    except Exception as e:
        print(f"处理 {bytes_path.name} 失败: {e}", exc_info=True)
        return json_name, []

def process_zip_file(zip_path: Path,flatbuffers_dir: Path,config_file: Path,server: str,output_zip_path: Path = None,output_dir: Path = None,zip_filename="Excel.zip",threads=4):
    temp_path = output_dir or Path(tempfile.mkdtemp(prefix="excel_"))
    temp_path.mkdir(parents=True, exist_ok=True)

    for p in temp_path.glob("*.json"):
        p.unlink(missing_ok=True)

    print(f"开始处理 {zip_path}，临时目录 {temp_path}")

    try:
        cfg = json.loads(config_file.read_text(encoding='utf-8'))
        server_cfg = cfg["DBSchema"][server]
        print(f"已加载服务器配置: {server}")

        needed = {}
        keep_fields_map = {}
        for json_name in server_cfg:
            if not json_name.endswith("Table.json"):
                continue
            table = json_name[:-5]
            needed[f"{table.lower()}.bytes"] = json_name
            keep_fields_map[json_name] = server_cfg[json_name]
        print(f"待处理表数量: {len(needed)}")
        flat_data_module_name = ".".join(flatbuffers_dir.parts).lstrip(".")
        table_extractor = TableExtractorImpl(flat_data_module_name)
        extracted = set()
        with ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.filename.lower() in needed:
                    pwd = zip_password(zip_filename)
                    zf.extract(info, temp_path, pwd=pwd)
                    extracted.add(info.filename.lower())
                    print(f"已解压: {info.filename}")

        missing = set(needed) - extracted
        if missing:
            print(f"缺失文件: {missing}")

        tasks = [(temp_path / bn,table_extractor,needed[bn],keep_fields_map[needed[bn]],temp_path) for bn in needed if bn in extracted]

        processed = 0
        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {pool.submit(process_single_file, *t): t for t in tasks}
            for f in as_completed(futures):
                json_name, data = f.result()
                if data:
                    processed += 1
                    print(f"已处理 {json_name}")
        output_zip_path = output_zip_path or zip_path.with_name(f"processed_{zip_path.name}")
        with ZipFile(output_zip_path, "w", ZIP_DEFLATED) as zf:
            for p in temp_path.glob("*.json"):
                zf.write(p, p.name)
        print(f"处理完成，共写 {processed} 个 JSON，输出 ZIP: {output_zip_path}")
        return processed, output_zip_path
    except Exception as e:
        print(f"整体处理失败: {e}", exc_info=True)
        return 0, None
    finally:
        if output_dir is None:
            shutil.rmtree(temp_path, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="处理 Excel 压缩包")
    parser.add_argument("--zip_path", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, default=None)
    parser.add_argument("--flatbuffers_dir", type=Path, required=True)
    parser.add_argument("--server", choices=["日服", "国服", "国际服"], required=True)
    parser.add_argument("--config_file", type=Path, required=True)
    parser.add_argument("--zip_filename", default="Excel.zip")
    parser.add_argument("--output_zip", type=Path, default=None)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()

    Config.is_cn = (args.server == "国服")

    processed, zip_out = process_zip_file(args.zip_path,args.flatbuffers_dir,args.config_file,args.server,args.output_zip,args.output_dir,args.zip_filename,args.threads)

if __name__ == "__main__":
    main()
