from os import path
import os
import subprocess  # 用于调用外部命令

EXTRACT_DIR = "Extracted"
DUMP_PATH = "Dumps"
TEMP_DIR = "Temp"

if not path.exists(path.join(EXTRACT_DIR, "FlatData")):
    print("FlatData directory does not exist. Setting up...")
    import setup_apk  # 确保这个模块可用
    from lib.dumper import IL2CppDumper
    from lib.console import notice
    from utils.util import FileUtils
    from extractor import compile_python

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

    # 编译 dump.cs 为 Python 文件
    compile_python(path.join(extract_path, "dump.cs"), EXTRACT_DIR)
    notice("Generated FlatData to dir: " + EXTRACT_DIR)

    # 确保生成的 .fbs 文件被编译为 .py 文件
    fbs_files = FileUtils.find_files(EXTRACT_DIR, ["*.fbs"], True)
    for fbs_file in fbs_files:
        fbs_file_path = path.abspath(fbs_file)
        py_file_path = path.splitext(fbs_file_path)[0] + ".py"
        print(f"Compiling {fbs_file_path} to {py_file_path}...")
        try:
            # 调用 flatc 编译器
            subprocess.run(
                ["flatc", "-p", "-o", path.dirname(py_file_path), fbs_file_path],
                check=True
            )
            print(f"Successfully compiled {fbs_file_path} to {py_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to compile {fbs_file_path}: {e}")

else:
    print("FlatData directory already exists. Skipping setup.")
