import importlib.util
import json
import zipfile
from pathlib import Path

def dynamic_import_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def convert_to_basic_types(obj):
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [convert_to_basic_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_basic_types(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return {key: convert_to_basic_types(value) for key, value in obj.__dict__.items() if not key.startswith("_")}
    elif hasattr(obj, "__iter__"):
        return [convert_to_basic_types(item) for item in obj]
    else:
        return str(obj)

def pack_to_zip(output_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in output_dir.rglob("*.json"):
            zipf.write(file_path, file_path.relative_to(output_dir))
    print(f"Packed JSON files into {zip_path}")
