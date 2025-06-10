import os
import requests
import json
from os import path
from shutil import move
from lib.downloader import FileDownloader
from lib.console import ProgressBar, notice

TEMP_DIR = "Temp"

def download_apk(apk_url: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    notice("Downloading APK...")
    apk_req = FileDownloader(apk_url, request_method="get", use_cloud_scraper=True, verbose=True)
    apk_data = apk_req.get_response(True)

    apk_filename = "com.RoamingStar.BlueArchive.bilibili.apk"
    apk_path = path.join(TEMP_DIR, apk_filename)
    apk_size = int(apk_data.headers.get("Content-Length", 0))

    if path.exists(apk_path) and path.getsize(apk_path) == apk_size:
        return apk_path

    FileDownloader(apk_url, request_method="get", enable_progress=True, use_cloud_scraper=True).save_file(apk_path)

    return apk_path.replace("\\", "/")

def main():
    # 读取网页内容
    url = "https://line1-h5-pc-api.biligame.com/game/detail/gameinfo?game_base_id=109864"
    response = requests.get(url)
    if response.status_code != 200:
        notice(f"Failed to fetch data from {url}")
        return

    # 解析 JSON 数据
    data = json.loads(response.text)
    apk_url = data["data"]["android_download_link"]

    # 下载 APK 文件
    apk_path = download_apk(apk_url)
    notice(f"APK downloaded to {apk_path}")

if __name__ == "__main__":
    main()
