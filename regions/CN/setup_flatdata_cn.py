from os import path
import os
import shutil

EXTRACT_DIR = "Extracted"
DUMP_PATH = "Dumps"
TEMP_DIR = "Temp"

if path.exists(path.join(EXTRACT_DIR, "FlatData")):
    print("Removing existing FlatData directory...")
    shutil.rmtree(flatdata_path)

if not path.exists(path.join(EXTRACT_DIR, "FlatData")):
    print("FlatData directory does not exist. Setting up...")
    import regions.CN.setup_apk_cn as setup_apk_cn
    from lib.dumper import IL2CppDumper
    from lib.console import notice
    from utils.util import FileUtils
    from extractor import compile_python

    os.makedirs(TEMP_DIR, exist_ok=True)

    if not path.exists(APK_PATH):
        notice("APK 文件不存在，开始获取下载链接并下载...")
        apk_url = setup_apk_cn.get_apk_url()
        notice(f"APK 链接: {apk_url}")
        apk_path_downloaded = setup_apk_cn.download_apk(apk_url)
        setup_apk_cn.extract_apk_file(apk_path_downloaded)
    else:
        notice("已存在 APK 文件，跳过下载步骤。")

    IL2CPP_NAME = "libil2cpp.so"
    METADATA_NAME = "global-metadata.dat"

    save_path = TEMP_DIR
    dumper = IL2CppDumper()
    dumper.get_il2cpp_dumper(save_path)

    il2cpp_path = FileUtils.find_files(TEMP_DIR, [IL2CPP_NAME], True)
    metadata_path = FileUtils.find_files(TEMP_DIR, [METADATA_NAME], True)

    if not (il2cpp_path and metadata_path):
        raise FileNotFoundError(
            "Cannot find il2cpp binary file or global-metadata file. Make sure they exist."
        )

    abs_il2cpp_path = path.abspath(il2cpp_path[0])
    abs_metadata_path = path.abspath(metadata_path[0])

    extract_path = path.abspath(path.join(EXTRACT_DIR, DUMP_PATH))

    print("Trying to dump il2cpp...")
    dumper.dump_il2cpp(
        extract_path, abs_il2cpp_path, abs_metadata_path, 5
    )
    notice("Dump il2cpp binary file successfully.")
    compile_python(path.join(extract_path, "dump.cs"), EXTRACT_DIR)
    notice("Generated FlatData to dir: " + EXTRACT_DIR)
else:
    print("FlatData directory already exists. Skipping setup.")
