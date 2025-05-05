import os
import requests
from pathlib import Path

def download_excel_zip(env_file: Path, output_file: Path):
    # 读取 ba.env 文件
    if not env_file.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found.")
    
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            key, value = line.strip().split("=")
            env_vars[key] = value

    # 获取 BA_SERVER_URL 并拼接路径
    ba_server_url = env_vars.get("ADDRESSABLE_CATALOG_URL")
    if not ba_server_url:
        raise ValueError("ADDRESSABLE_CATALOG_URL not found in the environment file.")
    
    excel_zip_url = f"{ba_server_url}/TableBundles/Excel.zip"
    
    # 下载文件
    response = requests.get(excel_zip_url)
    if response.status_code != 200:
        raise ConnectionError(f"Failed to download {excel_zip_url}. Status code: {response.status_code}")
    
    # 保存文件
    with open(output_file, "wb") as f:
        f.write(response.content)
    
    print(f"Downloaded {excel_zip_url} and saved as {output_file}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download Excel.zip from BA_SERVER_URL.")
    parser.add_argument("--env_file", type=Path, default="./ba.env", help="Path to the ba.env file.")
    parser.add_argument("--output_file", type=Path, default="./Excel.zip", help="Path to save the downloaded Excel.zip file.")
    args = parser.parse_args()

    download_excel_zip(args.env_file, args.output_file)
