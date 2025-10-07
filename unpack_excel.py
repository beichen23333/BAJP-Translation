import json
import shutil
import sys
import tempfile
import zipfile
from argparse import ArgumentParser
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import importlib

from xtractor.table import TableExtractor
from utils.database import TableDatabase
from lib.encryption import zip_password
from extractor import TableExtractorImpl

def parse_args():
    p = ArgumentParser(description="Unpack to JSON files.")
    p.add_argument("db_path", type=Path)
    p.add_argument("zip_path", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("flatbuffers_dir", type=Path)
    p.add_argument("config_file", type=Path)
    p.add_argument("output_zip", type=Path)
    p.add_argument("threads", type=int, default=10)
    return p.parse_args()

def process_table(table, output_dir):
    out_file = output_dir / f"{table.name.replace('DBSchema', 'Excel')}.json"
    with out_file.open("wt", encoding="utf8") as f:
        json.dump(TableDatabase.convert_to_list_dict(table), f, ensure_ascii=False, indent=2)

def process_excel_db(db_path, output_dir, flat_data_module_name, threads):
    db_schema_dir = output_dir / "DBSchema"
    db_schema_dir.mkdir(parents=True, exist_ok=True)

    extractor = TableExtractor(str(db_path), str(db_schema_dir), flat_data_module_name)
    db_tables = extractor._process_db_file(str(db_path.resolve()))

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(process_table, table, db_schema_dir) for table in db_tables]
        for future in futures:
            future.result()

def process_excel_table(zip_path, output_dir, flat_data_module_name, threads):
    excel_table_dir = output_dir / "ExcelTable"
    excel_table_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp())
    try:
        password = zip_password("Excel.zip")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir, pwd=password)

        extractor = TableExtractor(str(temp_dir), str(excel_table_dir), flat_data_module_name)

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for file_path in temp_dir.glob("*.bytes"):
                file_name = file_path.name
                with file_path.open("rb") as f:
                    file_data = f.read()
                futures.append(executor.submit(extractor._process_zip_file, file_name, file_data))

            for future in futures:
                data, name, success = future.result()
                if success and data:
                    out_file = excel_table_dir / name
                    with out_file.open("wb") as f:
                        f.write(data)
    finally:
        shutil.rmtree(temp_dir)

def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    flat_data_module_name = ".".join(args.flatbuffers_dir.parts).lstrip(".")

    process_excel_db(args.db_path, args.output_dir, flat_data_module_name, args.threads)
#    process_excel_table(args.zip_path, args.output_dir, flat_data_module_name, args.threads)

    with zipfile.ZipFile(args.output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for db_schema_file in (args.output_dir / "DBSchema").rglob("*"):
            zf.write(db_schema_file, db_schema_file.relative_to(args.output_dir))
        for excel_table_file in (args.output_dir / "ExcelTable").rglob("*"):
            zf.write(excel_table_file, excel_table_file.relative_to(args.output_dir))
        for file_name in ["TableCatalog.json", "MediaCatalog.json"]:
            file_path = Path(file_name)
            if file_path.exists():
                zf.write(file_path, file_path.name)

if __name__ == "__main__":
    main()
