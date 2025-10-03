import os
import sys
import argparse
from pathlib import Path
from lib.downloader import FileDownloader

def download_excel_files(env_file: Path, output_dir: Path):
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            env_vars[key] = value
    
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL")

    excel_db_url = f"{ba_server_url}/TableBundles/ExcelDB.db"
    excel_zip_url = f"{ba_server_url}/TableBundles/Excel.zip"

    excel_db_path = output_dir / "ExcelDB.db"
    excel_zip_path = output_dir / "Excel.zip"

    downloader = FileDownloader(excel_db_url, enable_progress=True)
    if downloader.save_file(excel_db_path):
        print(f"Downloaded ExcelDB.db to {excel_db_path}")
    else:
        print(f"Failed to download ExcelDB.db")

    downloader = FileDownloader(excel_zip_url, enable_progress=True)
    if downloader.save_file(excel_zip_path):
        print(f"Downloaded Excel.zip to {excel_zip_path}")
    else:
        print(f"Failed to download Excel.zip")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download ExcelDB.db and Excel.zip from BA_SERVER_URL.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_dir", type=Path, default="./downloads", help="Directory to save the downloaded files.")
    args = parser.parse_args()
    
    download_excel_files(args.env_file, args.output_dir)
