import os
from os import path
from pathlib import Path
from lib.console import notice
import regions.GL.setup_apk_gl as setup_apk_gl
import regions.GL.update_urls_gl as update_urls_gl

TEMP_DIR = "Temp"
APK_NAME = "com.nexon.bluearchive.apk"
APK_PATH = path.join(TEMP_DIR, APK_NAME)


def main(output_path: Path, json_output_path: Path):

    os.makedirs(TEMP_DIR, exist_ok=True)

    if not path.exists(APK_PATH):
        notice("APK 文件不存在，开始下载...")
        apk_path_downloaded = setup_apk_gl.download_xapk()
        setup_apk_gl.extract_apk_file(apk_path_downloaded)
    else:
        notice("已存在 APK 文件，跳过下载步骤。")

    versionCode, versionName = update_urls_gl.get_apk_version_info(path.join(TEMP_DIR, "com.nexon.bluearchive.apk"))
    server_url = update_urls_gl.get_server_url(versionName)
    notice(f"server_url已获取，地址{server_url}。")
    addressable_catalog_url = server_url.rsplit('/', 1)[0]

    if not path.exists(output_path):
        lines = ['\n'] * 12
    else:
        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        while len(lines) < 12:
            lines.append('\n')

    lines[8] = f"BA_SERVER_URL_GL={server_url}\n"
    lines[9] = f"ADDRESSABLE_CATALOG_URL_GL={addressable_catalog_url}\n"
    lines[10] = f"BA_VERSION_CODE_GL={versionCode}\n"
    lines[11] = f"BA_VERSION_NAME_GL={versionName}\n"

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
