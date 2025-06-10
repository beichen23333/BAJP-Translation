from lib.console import notice, print
from utils.util import UnityUtils
from os import path
import os
import base64
from lib.encryption import convert_string, create_key
import json
import argparse
import requests
import subprocess
import re
from pathlib import Path
from shutil import move
from lib.downloader import FileDownloader
from lib.console import ProgressBar, notice
TEMP_DIR = "Temp"
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_apk_worker(task_manager: TaskManager, url: str) -> None:
    task = task_manager.tasks。get()
    FileDownloader(url, headers=task["header"], enable_progress=True)。save_file(task["path"])
    task_manager.tasks。task_done()

def download_apk_file(apk_url: str) -> str:
    apk_size = 0
    if apk_head := FileDownloader(apk_url, headers={}, enable_progress=False)。get_response():
        apk_size = int(apk_head.headers。get("Content-Length"， 0))

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    apk_path = TEMP_DIR / "com.RoamingStar.BlueArchive.bilibili.apk"

    if apk_path.exists() 和 apk_path.stat()。st_size == apk_size:
        print("APK file already exists and size matches.")
        return str(apk_path)

    if not apk_size:
        FileDownloader(apk_url)。save_file(str(apk_path))
    else:
        worker_num = 5
        chunk_size = apk_size // worker_num
        parts: List[Dict] = []
        for i in range(worker_num):
            start = chunk_size * i
            end = start + chunk_size - 1 if i != worker_num - 1 else apk_size - 1
            output = TEMP_DIR / f"chunk_{i}.dat"
            header = {"Range": f"bytes={start}-{end}"， "User-Agent": "Chrome/122.0"}
            parts.append({"header": header, "path": str(output)})

        task_manager = TaskManager(max_workers=worker_num, worker_num=worker_num)
        for part in parts:
            task_manager.add_task(part)

        with ProgressBar(apk_size, "Downloading APK..."， "MB"， 1048576) as progress:
            task_manager.run(apk_url, download_apk_worker)
            for part in parts:
                progress.update(os.path。getsize(part["path"]))

        with open(apk_path, "wb") as apk:
            for part in parts:
                with open(part["path"]， "rb") as chunk:
                    apk.write(chunk.read())
                os.remove(part["path"])

        if apk_path.stat().st_size != apk_size:
            notice("Failed when download apk. Retry...", "error")
            return download_apk_file(apk_url)

    notice("Combinate files to apk success.")
    return str(apk_path)

def get_app_version() -> str:
    url = "https://bluearchive-cn.com/api/meta/setup"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        app_version = data.get("data", {}).get("appVersion", "")
        match = re.search(r"(\d+\.\d+\.\d+)", app_version)
        if match:
            return match.group(1)
    raise ValueError("Failed to extract app version from the response.")

def fetch_server_info(app_version: str) -> dict:
    url = "https://gs-api.bluearchive-cn.com/api/state"
    headers = {
        "APP-VER": app_version,
        "PLATFORM-ID": "1",
        "CHANNEL-ID": "2",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None

def get_server_url() -> str:
    try:
        app_version = get_app_version()
        server_info = fetch_server_info(app_version)
        if server_info:
            return json.dumps(server_info, indent=4)
        else:
            return json.dumps({"error": "Failed to fetch server information."}, indent=4)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=4)

def get_addressable_catalog_url(server_info_json: str, json_output_path: Path) -> str:
    try:
        # Parse the server info JSON
        server_info = json.loads(server_info_json)
        
        # Extract the first AddressablesCatalogUrlRoot from the list
        addressables_catalog_url_roots = server_info.get("AddressablesCatalogUrlRoots", [])
        if not addressables_catalog_url_roots:
            raise LookupError("Cannot find AddressablesCatalogUrlRoots in the server response.")
        
        # Get the first AddressablesCatalogUrlRoot in the list
        first_catalog_url = addressables_catalog_url_roots[0]
        if not first_catalog_url:
            raise LookupError("Cannot find the first AddressablesCatalogUrlRoot in the list.")
        
        # Save the full server response to the specified JSON output path
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(server_info, f, separators=(",", ":"), ensure_ascii=False)
        
        return first_catalog_url
    except Exception as e:
        raise LookupError(f"Error processing server info: {str(e)}")

import zipfile
import xml.etree.ElementTree as ET
from pyaxmlparser.axmlprinter import AXMLPrinter # Ensure this comes from your maintained AXMLParser package

def get_apk_version_info(apk_path):
    try:
        # Open the APK as a ZIP file and read the binary AndroidManifest.xml
        with zipfile.ZipFile(apk_path, 'r') as apk:
            manifest_content = apk.read('AndroidManifest.xml')
        
        # Use AXMLPrinter to convert the binary XML into plain text XML.
        # This class should also do the necessary cleanup of namespace URIs.
        xml_str = AXMLPrinter(manifest_content).get_xml()
        
        # Parse the XML string with ElementTree.
        root = ET.fromstring(xml_str)
        
        # The version attributes are usually in the 'android' namespace.
        # The AXMLPrinter (per docs) should have cleaned up the namespace URIs.
        # Here we explicitly define the expected android namespace.
        android_ns = "http://schemas.android.com/apk/res/android"
        
        # Extract versionCode and versionName using the namespace-qualified keys.
        version_code = root.attrib.get(f"{{{android_ns}}}versionCode")
        version_name = root.attrib.get(f"{{{android_ns}}}versionName")
        
        if version_code and version_name:
            return version_code, version_name
        else:
            print("Error: versionCode or versionName not found in the manifest.")
            return None
    except Exception as e:
        notice(f"Error extracting version info from manifest: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Yostar server URL for Blue Archive CN")
    parser.add_argument("output_path", type=Path, help="output file for server url")
    parser.add_argument("json_output_path", type=Path, help="output file for json from server url")

    args = parser.parse_args()

    url = "https://line1-h5-pc-api.biligame.com/game/detail/gameinfo?game_base_id=109864"
    response = requests.get(url, headers=headers)

    # 解析 JSON 数据
    data = json.loads(response.text)
    apk_url = data["data"]["android_download_link"]

    # 下载 APK 文件
    apk_path = download_apk(apk_url, apk_size)
    notice(f"APK downloaded to {apk_path}")

    with open(args.output_path, "wb") as fs:
        server_url = get_server_url()
        addressable_catalog_url = get_addressable_catalog_url(server_url, args.json_output_path)
        versionCode, versionName = get_apk_version_info(path.join(TEMP_DIR, "com.RoamingStar.BlueArchive.bilibili.apk"))
        fs.write(f"BA_SERVER_URL=https://gs-api.bluearchive-cn.com/api/state\nADDRESSABLE_CATALOG_URL={addressable_catalog_url}\nBA_VERSION_CODE={versionCode}\nBA_VERSION_NAME={versionName}".encode())
