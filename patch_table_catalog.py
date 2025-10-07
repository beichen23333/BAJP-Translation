import json
from pathlib import Path
import binascii
import json
import subprocess
import zipfile
import shutil

def calculate_crc32(file_path) -> int:
    with open(file_path, 'rb') as f:
        return binascii.crc32(f.read()) & 0xFFFFFFFF

with open("./TableCatalog.json", "r", encoding="utf8") as f:
    catalog_data = json.loads(f.read())

modify_zip_path = Path("./Modify.zip")
extracted_excel_db_path = Path("./TempExcelDB")

extracted_excel_db = None
if modify_zip_path.exists():
    with zipfile.ZipFile(modify_zip_path, 'r') as zip_ref:
        names = zip_ref.namelist()
        excel_db_in_zip = None
        for name in names:
            if name.endswith("ExcelDB.db"):
                excel_db_in_zip = name
                break
        if excel_db_in_zip:
            with zip_ref.open(excel_db_in_zip) as src, open(extracted_excel_db_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            extracted_excel_db = extracted_excel_db_path

hasModded = False

if extracted_excel_db and extracted_excel_db.exists():
    files_path = extracted_excel_db.parent
    files_to_patch = {extracted_excel_db.name: extracted_excel_db}

    for key, item in catalog_data["Table"].items():
        if key in files_to_patch:
            size = item["size"]
            crc = item["crc"]
            patched_file = files_to_patch[key]
            patched_file_size = patched_file.stat().st_size
            patched_file_crc = calculate_crc32(patched_file)
            item["size"] = patched_file_size
            item["crc"] = patched_file_crc
            hasModded = True
            print(f"TableCatalog.bytes: 修改{key} 文件大小值 {size} -> {patched_file_size}")
            print(f"TableCatalog.bytes: 修改{key} crc值 {crc} -> {patched_file_crc}")

    if hasModded:
        original_catalog_path = Path("./TableCatalog.json")
        with open(original_catalog_path, "w", encoding="utf8") as f:
            json.dump(catalog_data, f, ensure_ascii=False, indent=2)
        print("✅ 已将修改后的 Catalog 数据写回 ./TableCatalog.json")
