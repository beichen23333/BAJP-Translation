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

def get_server_url(version: str) -> str:
    request_body = {
        "market_game_id": "com.nexon.bluearchive",
        "market_code": "playstore",
        "curr_build_version": version,
        "curr_build_number": version.split(".")[-1],
    }

    try:
        response = requests.post("https://api-pub.nexon.com/patch/v1.1/version-check", json=request_body)
        if response.status_code == 200:
            server_url = response.json()
            return server_url["patch"]["resource_path"]
    except Exception as e:
        print(f"Error: {e}")

    return ""
