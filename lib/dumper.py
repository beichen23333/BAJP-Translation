"""Dump il2cpp file to csharp file."""

import json
import os
import platform
import shutil
from os import path

from lib.downloader import FileDownloader
from utils.util import CommandUtils, FileUtils, ZipUtils, CommandUtils_Jp

IL2CPP_ZIP = "https://github.com/Perfare/Il2CppDumper/archive/refs/heads/master.zip"
IL2CPP_FOLDER = "Il2CppDumper-master"
ZIP_NAME = "il2cpp-dumper.zip"

def get_platform_identifier():
    os_map = {
        "linux": "linux",
        "darwin": "osx",
        "windows": "win"
    }

    arch_map = {
        "x86_64": "x64",
        "AMD64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64"
    }

    os_name = os_map.get(platform.system().lower())
    arch = arch_map.get(platform.machine().lower())

    if not os_name or not arch:
        raise RuntimeError(f"Unsupported OS or architecture: {platform.system()} {platform.machine()}")

    return f"{os_name}-{arch}", os_name

class IL2CppDumper:

    def __init__(self) -> None:
        self.project_dir = ""

    def get_il2cpp_dumper(self, save_path: str) -> None:
        FileDownloader(IL2CPP_ZIP).save_file(path.join(save_path, ZIP_NAME))
        ZipUtils.extract_zip(path.join(save_path, ZIP_NAME), save_path)

        if not (
            config_path := FileUtils.find_files(
                path.join(save_path, IL2CPP_FOLDER), ["config.json"], True
            )
        ):
            raise FileNotFoundError(
                "Cannot find config file. Make sure il2cpp-dumper exsist."
            )

        with open(config_path[0], "r+", encoding="utf8") as config:
            il2cpp_config: dict = json.load(config)
            il2cpp_config["RequireAnyKey"] = False
            il2cpp_config["GenerateDummyDll"] = False
            config.seek(0)
            config.truncate()
            json.dump(il2cpp_config, config)

        self.project_dir = path.dirname(config_path[0])

    def dump_il2cpp(
        self,
        extract_path: str,
        il2cpp_path: str,
        global_metadata_path: str,
        max_retries: int = 1,
    ) -> None:
        """Dump il2cpp with using il2cpp-dumper.
        Args:
            extract_path (str): Absolute path to extract dump file.
            il2cpp_path (str): Absolute path to il2cpp lib.
            global_metadata_path (str): Absolute path to global metadata.
            max_retries (int): Max retry count for dump when dump failed.


        Raises:
            RuntimeError: Raise error when dump unsuccess.
        """

        os.makedirs(extract_path, exist_ok=True)

        success, err = CommandUtils.run_command(
            "dotnet",
            "run",
            "--framework",
            "net8.0",
            il2cpp_path,
            global_metadata_path,
            extract_path,
            cwd=self.project_dir,
        )
        if not success:
            if max_retries == 0:
                raise RuntimeError(
                    f"Error occurred during dump the lib2cpp file. Retry might solve this issue. Info: {err}"
                )
            return self.dump_il2cpp(
                extract_path, il2cpp_path, global_metadata_path, max_retries - 1
            )

        return None


class IL2CppDumper_Jp:
    def __init__(self) -> None:
        self.project_dir = ""
        self.binary_name = "Il2CppInspector"

    def get_il2cpp_dumper(self, save_path: str) -> None:
        platform_id, os_name = get_platform_identifier()
        il2cpp_zip_url = f"https://github.com/asfu222/Il2CppInspectorRedux/releases/latest/download/Il2CppInspectorRedux.CLI-{platform_id}.zip"

        zip_path = path.join(save_path, "Il2CppInspectorRedux.CLI.zip")
        FileDownloader(il2cpp_zip_url).save_file(zip_path)

        extract_path = path.join(save_path, "Il2CppInspector")
        ZipUtils.extract_zip(zip_path, extract_path)
        self.project_dir = extract_path

        if os_name == "win":
            self.binary_name += ".exe"
        else:
            # Make the binary executable on Unix systems
            CommandUtils_Jp.run_command(
                "chmod",
                "+x",
                f"./{self.binary_name}",
                cwd=self.project_dir
            )

    def dump_il2cpp(
        self,
        extract_path: str,
        il2cpp_path: str,
        global_metadata_path: str,
        max_retries: int = 1,
    ) -> None:
        """Dump il2cpp using Il2CppInspector."""
        os.makedirs(extract_path, exist_ok=True)

        binary_path = f"./{self.binary_name}"
        cs_out = path.join(extract_path, "dump.cs")

        success, err = CommandUtils_Jp.run_command(
            binary_path,
            "--bin", il2cpp_path,
            "--metadata", global_metadata_path,
            "--select-outputs",
            "--cs-out", cs_out,
            "--must-compile",
            cwd=self.project_dir
        )

        if not success:
            raise RuntimeError(f"IL2CPP dump failed: {err}")

        return None
