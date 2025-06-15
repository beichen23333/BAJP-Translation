import os
import sys
import requests
from pathlib import Path

def download_file(url: str, output_file: Path):
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def download_excel_files(env_file: Path, output_dir: Path):
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            env_vars[key] = value
    
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL_CN")

    excel_db_url = f"{ba_server_url}/TableBundles/ExcelDB.db"
    excel_zip_url = f"{ba_server_url}/TableBundles/Excel.zip"

    excel_db_path = output_dir / "ExcelDB.db"
    excel_zip_path = output_dir / "Excel.zip"

    download_file(excel_db_url, excel_db_path)
    download_file(excel_zip_url, excel_zip_path)

    print(f"Downloaded ExcelDB.db to {excel_db_path}")
    print(f"Downloaded Excel.zip to {excel_zip_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download ExcelDB.db and Excel.zip from BA_SERVER_URL.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_dir", type=Path, default="./downloads", help="Directory to save the downloaded files.")
    args = parser.parse_args()
    
    download_excel_files(args.env_file, args.output_dir)
