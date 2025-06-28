import os
from os import path
from pathlib import Path
from lib.console import notice
import regions.CN.setup_apk_cn as setup_apk_cn
import regions.CN.update_urls_cn as update_urls_cn
from regions.get_apk_version import get_apk_version_info

TEMP_DIR = "Temp"
APK_NAME = "com.RoamingStar.BlueArchive.bilibili.apk"
APK_PATH = path.join(TEMP_DIR, APK_NAME)

def main(output_path: Path, json_output_path: Path):

    os.makedirs(TEMP_DIR, exist_ok=True)

    if not path.exists(APK_PATH):
        notice("APK 文件不存在，开始获取下载链接并下载...")
        apk_url = setup_apk_cn.get_apk_url()
        notice(f"APK 链接: {apk_url}")
        apk_path_downloaded = setup_apk_cn.download_apk_multithreaded(apk_url)
        setup_apk_cn.extract_apk_file(apk_path_downloaded)
    else:
        notice("已存在 APK 文件，跳过下载步骤。")

    server_url_json = update_urls_cn.get_server_url()
    addressable_url = update_urls_cn.get_addressable_catalog_url(server_url_json, json_output_path)

    version_info = get_apk_version_info(APK_PATH)
    if version_info is None:
        notice("无法从 APK 提取版本信息。")
        return
    version_code, version_name = version_info

    if not path.exists(output_path):
        lines = ['\n'] * 8
    else:
        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        while len(lines) < 8:
            lines.append('\n')

    lines[4] = f"BA_SERVER_URL_CN=https://gs-api.bluearchive-cn.com/api/state\n"
    lines[5] = f"ADDRESSABLE_CATALOG_URL_CN={addressable_url}\n"
    lines[6] = f"BA_VERSION_CODE_CN={version_code}\n"
    lines[7] = f"BA_VERSION_NAME_CN={version_name}\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    notice("已完成所有操作并写入文件。")

    

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="自动获取 APK 和服务器信息")
    parser.add_argument("output_path", type=Path, help="输出服务器信息文件路径")
    parser.add_argument("json_output_path", type=Path, help="输出 server json 文件路径")
    args = parser.parse_args()

    main(args.output_path, args.json_output_path)