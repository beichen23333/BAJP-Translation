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
import regions.CN.setup_apk_cn
TEMP_DIR = "Temp"

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
        server_info = json.loads(server_info_json)
        addressables_catalog_url_roots = server_info.get("AddressablesCatalogUrlRoots", [])
        if not addressables_catalog_url_roots:
            raise LookupError("Cannot find AddressablesCatalogUrlRoots in the server response.")

        first_catalog_url = addressables_catalog_url_roots[0]
        if not first_catalog_url:
            raise LookupError("Cannot find the first AddressablesCatalogUrlRoot in the list.")

        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(server_info, f, separators=(",", ":"), ensure_ascii=False)
        
        return first_catalog_url
    except Exception as e:
        raise LookupError(f"Error processing server info: {str(e)}")