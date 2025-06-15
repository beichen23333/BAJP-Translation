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
