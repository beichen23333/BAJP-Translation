from utils.util import ZipUtils
from os import path
import glob
import os
from lib.downloader import FileDownloader
from lib.console import ProgressBar, notice

TEMP_DIR = "Temp"

def extract_apk_file(apk_path: str) -> None:
    apk_files = ZipUtils.extract_zip(apk_path, path.join(TEMP_DIR), keywords=["com.YostarJP.BlueArchive.apk"])
    ZipUtils.extract_zip(apk_files, path.join(TEMP_DIR, "Data"), zips_dir=TEMP_DIR)

def download_xapk() -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    apk_dir = glob.glob(f"./{TEMP_DIR}/*.xapk")
    if len(apk_dir) > 0:
        return apk_dir[0].replace("\\", "/")

    apk_url = "https://d.apkpure.net/b/XAPK/com.YostarJP.BlueArchive?version=latest&nc=arm64-v8a&sv=24"
    notice("Downloading XAPK...")
    apk_req = FileDownloader(apk_url, request_method="get", use_cloud_scraper=True, verbose=True)
    apk_data = apk_req.get_response(True)

    apk_path = path.join(
        TEMP_DIR,
        apk_data.headers["Content-Disposition"]
        .rsplit('"', 2)[-2]
        .encode("ISO8859-1")
        .decode(),
    )
    apk_size = int(apk_data.headers.get("Content-Length", 0))

    if path.exists(apk_path) and path.getsize(apk_path) == apk_size:
        return apk_path

    FileDownloader(apk_url, request_method="get", enable_progress=True, use_cloud_scraper=True).save_file(apk_path)

    return apk_path.replace("\\", "/")

if not path.exists(path.join(TEMP_DIR, "Data")):
    apk_path = download_xapk()
    extract_apk_file(apk_path)
