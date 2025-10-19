import json
from pathlib import Path
import binascii
import subprocess
import zipfile
import shutil
import xxhash
from zlib import crc32

def calculate_crc32(file_path):
    with open(file_path, 'rb') as f:
        return binascii.crc32(f.read()) & 0xFFFFFFFF

def calculate_hash64(name):
    if isinstance(name, str):
        name = name.encode("utf8")
    return xxhash.xxh64(name).intdigest()

def calculate_crc(file_path):
    with file_path.open("rb") as f:
        return crc32(f.read()) & 0xFFFFFFFF

with open("./TableCatalog.json", "r", encoding="utf8") as f:
    catalog_data = json.loads(f.read())

modify_zip_path = Path("./Modify.zip")
extracted_excel_db_path = Path("./ExcelDB.db")

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
        print("已将修改后的 Catalog 数据写回")

if hasModded:
    original_file = extracted_excel_db
    original_filename = original_file.name
    original_name_for_hash = original_filename.lower()
    name_hash64 = calculate_hash64(original_name_for_hash)
    file_crc = calculate_crc(original_file)
    new_name = f"{name_hash64}_{file_crc}"
    renamed_file_path = original_file.parent / new_name
    original_file.rename(renamed_file_path)
    print(f"已重命名文件: {original_filename} -> {new_name}")

    new_zip_path = original_file.parent / "Modified_ExcelDB.zip"
    with zipfile.ZipFile(new_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(renamed_file_path, arcname=new_name)
    print(f"已重新打包为 zip: {new_zip_path}")

    ba_text_dir = Path("./BA-Text")
    ba_text_dir.mkdir(parents=True, exist_ok=True)
    target_zip_path = ba_text_dir / new_zip_path.name
    shutil.move(str(new_zip_path), str(target_zip_path))
    print(f"已移动新 zip 到: {target_zip_path}")
