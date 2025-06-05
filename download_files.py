import os
import requests
from pathlib import Path
from extractor import TablesExtractor  # 确保这个模块可用

def download_file(url: str, output_file: Path):
    response = requests.get(url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {url}. Status code: {response.status_code}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Downloaded {url} and saved as {output_file}")

def download_and_unpack_excel_db(env_file: Path, output_dir: Path, temp_dir: Path):
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            env_vars[key] = value
    
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL")
    if not ba_server_url:
        raise ValueError("ADDRESSABLE_CATALOG_URL not found in the environment file.")
    
    # 下载 ExcelDB.db 文件
    excel_db_url = f"{ba_server_url}/TableBundles/ExcelDB.db"
    excel_db_path = output_dir / "ExcelDB.db"
    download_file(excel_db_url, excel_db_path)
    
    # 解包 ExcelDB.db 文件
    print(f"Unpacking {excel_db_path} to {temp_dir}...")
    TablesExtractor(temp_dir, excel_db_path.parent).extract_table(excel_db_path.name)
    
    print(f"Unpacked files are saved in {temp_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download ExcelDB.db from BA_SERVER_URL and unpack it.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_dir", type=Path, default="./downloads", help="Directory to save the downloaded files.")
    parser.add_argument("--temp_dir", type=Path, default="./temp", help="Temporary directory to unpack the files.")
    args = parser.parse_args()
    
    download_and_unpack_excel_db(args.env_file, args.output_dir, args.temp_dir)
