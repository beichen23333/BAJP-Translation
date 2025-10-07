import argparse
import zipfile
import tempfile
import shutil
from pathlib import Path
from repacker import TableRepackerImpl
from lib.encryption import zip_password
from extractor import TablesExtractor


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("input_zip", type=Path)
    parser.add_argument("output_dir", type=Path)
    
    args = parser.parse_args()

    packer = TableRepackerImpl("Extracted.FlatData")

    source_dir = Path(f'Extracted/Table/{args.input_zip.stem}')
    source_binary_dir = Path(f'Extracted/Temp/Table/{args.input_zip.stem}')

    with tempfile.TemporaryDirectory() as temp_extract_dir:
        temp_extract_path = Path(temp_extract_dir)
        shutil.copytree(source_binary_dir, temp_extract_dir, dirs_exist_ok=True)
        excel_table_dir = temp_extract_path / "ExcelTable"
        if excel_table_dir.exists():
            for json_file in excel_table_dir.glob("*.json"):
                print(f"Processing ExcelTable file: {json_file.name}")
                try:
                    new_content = packer.repackExcelZipJson(json_file)
                    target_file = temp_extract_path / f"{json_file.stem.lower()}.bytes"
                    with open(target_file, "wb") as tf:
                        tf.write(new_content)
                    print(f"Generated binary file: {target_file.name}")
                except Exception as e:
                    print(f"Error processing {json_file.name}: {e}")

        db_schema_dir = temp_extract_path / "DBSchema"
        excel_db_path = temp_extract_path / "ExcelDB.db"
        if db_schema_dir.exists() and excel_db_path.exists():
            for json_file in db_schema_dir.glob("*.json"):
                print(f"Updating database table: {json_file.name}")
                try:
                    packer.repackjson2db(json_file, excel_db_path)
                    print(f"Updated database table: {json_file.name}")
                except Exception as e:
                    print(f"Error updating database table {json_file.name}: {e}")

#        with tempfile.TemporaryDirectory() as temp_zip_dir:
#            temp_zip_path = Path(temp_zip_dir)
            
#            modified_excel_zip = temp_zip_path / "Excel.zip"
#            with zipfile.ZipFile(modified_excel_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
#                zipf.setpassword(zip_password("Excel.zip"))
                
#                for file in temp_extract_path.rglob('*'):
#                    if file.is_file() and file.name != "ExcelDB.db":
#                        arcname = file.relative_to(temp_extract_path)
#                        zipf.write(file, arcname)
            
#            print(f"Created password-protected Excel.zip")
            
            if excel_db_path.exists():
                shutil.copy2(excel_db_path, temp_zip_path / "ExcelDB.db")
                print("Copied modified ExcelDB.db")
            
            new_modify_zip = args.output_dir / "New-Modify.zip"
            with zipfile.ZipFile(new_modify_zip, 'w', zipfile.ZIP_DEFLATED) as final_zip:
                for file in temp_zip_path.rglob('*'):
                    if file.is_file():
                        arcname = file.relative_to(temp_zip_path)
                        final_zip.write(file, arcname)
            
            print(f"Created New-Modify.zip at: {new_modify_zip}")
    
    temp_dir = source_dir / "temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
if __name__ == "__main__":
    main()