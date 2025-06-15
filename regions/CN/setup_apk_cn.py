from ..utils.util import ZipUtils
from os import path
import glob
import os
from ..lib.downloader import FileDownloader
from ..lib.console import ProgressBar, notice

TEMP_DIR = "Temp"

def extract_apk_file(apk_path: str) -> None:
    apk_files = ZipUtils.extract_zip(apk_path, path.join(TEMP_DIR), keywords=["com.RoamingStar.BlueArchive.bilibili.apk"])
    ZipUtils.extract_zip(apk_files, path.join(TEMP_DIR, "Data"), zips_dir=TEMP_DIR)

def get_apk_url() -> str:
    response = FileDownloader("https://bluearchive-cn.com/").get_response()
    js_match = re.search(r'<script[^>]+type="module"[^>]+crossorigin[^>]+src="([^"]+)"[^>]*>', response.text)
    if not js_match:
        raise LookupError("Could not find the JavaScript file link.")

    js_url = js_match.group(1)
    js_response = FileDownloader(js_url).get_response()
    apk_match = re.search(r'http[s]?://[^\s"<>]+?\.apk', js_response.text)
    if not apk_match:
        raise LookupError("Could not find the APK download link.")

    return apk_match.group()

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

if not path.exists(path.join(TEMP_DIR, "Data")):
    apk_url = get_apk_url()
    apk_path = download_apk(apk_url)
    notice(f"APK downloaded to {apk_path}")

    extract_apk_file(apk_path)
