from lib.console import notice, print
from lib.downloader import FileDownloader
from lib.structure import GLResource, Resource
from utils.config import Config
import re
import requests
import json
from pathlib import Path

# 定义常量
UPTODOWN_URL = "https://blue-archive-global.en.uptodown.com/android"
MANIFEST_URL = "https://api-pub.nexon.com/patch/v1.1/version-check"

def get_latest_version() -> str:
    """Fetch the latest version from Uptodown."""
    response = FileDownloader(UPTODOWN_URL).get_response()
    if not response:
        raise LookupError("Cannot fetch resource catalog.")
    
    if version_match := re.search(r"(\d+\.\d+\.\d+)", response.text):
        return version_match.group(1)
    
    raise LookupError("Unable to retrieve the version.")

def get_server_url(version: str) -> str:
    """Get server url from game API."""
    request_body = {
        "market_game_id": "com.nexon.bluearchive",
        "market_code": "playstore",
        "curr_build_version": version,
        "curr_build_number": version.split(".")[-1],
    }
    server_resp = FileDownloader(MANIFEST_URL, request_method="post", json=request_body).get_response()
    if server_resp and server_resp.json():
        return server_resp.json().get("patch", {}).get("resource_path", "")
    return ""

def get_resource_manifest(server_url: str) -> Resource:
    """Fetch the resource manifest from the server URL."""
    resources = GLResource()
    try:
        resources.set_url_link(server_url.rsplit("/", 1)[0] + "/")
        resource_data = FileDownloader(server_url).get_response()
        if not resource_data or not resource_data.json():
            raise LookupError("Failed to fetch resource catalog. Retry may solve the issue.")
        
        resource = resource_data.json()
        for res in resource.get("resources", []):
            resources.add_resource(
                res["group"],
                res["resource_path"],
                res["resource_size"],
                res["resource_hash"],
            )
        
        if not resources:
            notice("The catalog is incomplete, and some resource types may fail to be retrieved.", "warn")
    except Exception as e:
        raise LookupError(f"Encountered the following error while attempting to fetch manifest: {e}.") from e
    return resources.to_resource()

def main():
    """Main entry of GLServer."""
    version = Config.version
    if not version:
        notice("Version not specified. Automatically fetching latest...")
        version = Config.version = get_latest_version()
    notice(f"Current resource version: {version}")
    
    server_url = get_server_url(version)
    print("Pulling catalog...")
    resources = get_resource_manifest(server_url)
    notice(f"Catalog: {resources}.")
    return resources

if __name__ == "__main__":
    main()
