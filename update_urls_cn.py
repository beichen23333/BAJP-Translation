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

    apk_url = get_apk_url()

    apk_path = download_apk(apk_url)
    notice(f"APK downloaded to {apk_path}")

    with open(args.output_path, "wb") as fs:
        server_url = get_server_url()
        addressable_catalog_url = get_addressable_catalog_url(server_url, args.json_output_path)
        versionCode, versionName = get_apk_version_info(path.join(TEMP_DIR, "com.RoamingStar.BlueArchive.bilibili.apk"))
        fs.write(f"BA_SERVER_URL=https://gs-api.bluearchive-cn.com/api/state\nADDRESSABLE_CATALOG_URL={addressable_catalog_url}\nBA_VERSION_CODE={versionCode}\nBA_VERSION_NAME={versionName}".encode())
