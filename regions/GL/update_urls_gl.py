from BA_Chinese_Translation.lib.console import notice, print
from utils.util import UnityUtils
from os import path
import os
import base64
from BA_Chinese_Translation.lib.encryption import convert_string, create_key
import json
import argparse
import requests
import subprocess
import re
from pathlib import Path
from shutil import move
from BA_Chinese_Translation.lib.downloader import FileDownloader
from BA_Chinese_Translation.lib.console import ProgressBar, notice
import setup_apk_gl
TEMP_DIR = "Temp"

def get_latest_version() -> str:
    url = "https://blue-archive-global.en.uptodown.com/android"
    if not (response := FileDownloader(url).get_response()):
        raise LookupError("Cannot fetch resource catalog.")

    if version_match := re.search(r"(\d+\.\d+\.\d+)", response.text):
        return version_match.group(1)

    raise LookupError("Unable to retrieve the version.")

def get_server_url(version: str) -> str:
    request_body = {
        "market_game_id": "com.nexon.bluearchive",
        "market_code": "playstore",
        "curr_build_version": version,
        "curr_build_number": version.split(".")[-1],
    }

    if (
        server_resp := FileDownloader(
            "https://api-pub.nexon.com/patch/v1.1/version-check", request_method="post", json=request_body
        ).get_response()
    ) and (server_url := server_resp.json()):
        return server_url.get("patch", {}).get("resource_path", "")

    return ""

import zipfile
import xml.etree.ElementTree as ET
from pyaxmlparser.axmlprinter import AXMLPrinter

def get_apk_version_info(apk_path):
    try:
        with zipfile.ZipFile(apk_path, 'r') as apk:
            manifest_content = apk.read('AndroidManifest.xml')
        
        xml_str = AXMLPrinter(manifest_content).get_xml()
        
        root = ET.fromstring(xml_str)
        

        android_ns = "http://schemas.android.com/apk/res/android"
        
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
    parser = argparse.ArgumentParser(description="Update Nexon server URL for Blue Archive")
    parser.add_argument("output_path", type=Path, help="output file for server url")
    parser.add_argument("json_output_path", type=Path, help="output file for json from server url")

    args = parser.parse_args()
    latest_version = get_latest_version()
    server_url = get_server_url(latest_version)
    versionCode, versionName = get_apk_version_info(path.join(TEMP_DIR, "com.nexon.bluearchive.apk"))
    addressable_catalog_url = server_url.rsplit('/', 1)[0]

    with open(args.output_path, "r") as fs:
        lines = fs.readlines()

    lines[8] = f"BA_SERVER_URL_GL={ba_server_url}"
    lines[9] = f"ADDRESSABLE_CATALOG_URL_GL={addressable_catalog_url}"
    lines[10] = f"BA_VERSION_CODE_GL={versionCode}"
    lines[11] = f"BA_VERSION_CODE_GL={versionCode}"
    with open(args.output_path, "w") as fs:
        fs.writelines(lines)
