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
extracted_excel_db_path = Path("./TempExcelDB.db")

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
            # Could also do the crc bypass method from before, but not implemented here because it is unnecessary

    if hasModded:
        catalog_json_path = files_path / "TableCatalog.json"
        with open(catalog_json_path, "wb") as f:
            f.write(json.dumps(catalog_data).encode())
        subprocess.run([
            "./MemoryPackRepacker", "serialize", "table",
            str(catalog_json_path), str(files_path / "TableCatalog.bytes")
        ])
        if catalog_json_path.exists():
            catalog_json_path.unlink()
        #with open("./assets/static/version.hash", "r") as rf, open(files_path / "TableCatalog.hash", "w") as wf:
        #   wf.write(f"{str(channel_dir.relative_to(Path("./assets")))}-{rf.read()}")
