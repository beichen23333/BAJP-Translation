from os import path
import os
import shutil
import regions.GL.setup_apk_gl as setup_apk_gl

EXTRACT_DIR = "Extracted"
DUMP_PATH = "Dumps"
TEMP_DIR = "Temp"
APK_NAME = "com.nexon.bluearchive"
APK_PATH = path.join(TEMP_DIR, APK_NAME)

if not path.exists(path.join(EXTRACT_DIR, "FlatData")):
    print("FlatData directory does not exist. Setting up...")
    import regions.GL.setup_apk_gl
    from lib.dumper import IL2CppDumper
    from lib.console import notice
    from utils.util import FileUtils
    from extractor import compile_python

    os.makedirs(TEMP_DIR, exist_ok=True)

    if not path.exists(APK_PATH):
        notice("APK 文件不存在，开始下载...")
        apk_path_downloaded = setup_apk_gl.download_xapk()
        setup_apk_gl.extract_apk_file(apk_path_downloaded)
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
            "无法找到il2cpp文件或global-metadata文件，请确保它们存在。"
        )

    abs_il2cpp_path = path.abspath(il2cpp_path[0])
    abs_metadata_path = path.abspath(metadata_path[0])

    extract_path = path.abspath(path.join(EXTRACT_DIR, DUMP_PATH))

    print("尝试dump il2cpp...")
    dumper.dump_il2cpp(
        extract_path, abs_il2cpp_path, abs_metadata_path, 5
    )
    notice("Dump il2cpp文件成功")
    compile_python(path.join(extract_path, "dump.cs"), EXTRACT_DIR)
    notice("生成FlatData到路径: " + EXTRACT_DIR)
else:
    print("FlatData目录已经存在，跳过设置。")
