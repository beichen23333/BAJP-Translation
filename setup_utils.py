import importlib.util
import json
import inspect
import numpy as np
from pathlib import Path

def dynamic_import_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def convert_to_basic_types(obj):
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    elif isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')  # 尝试解码为 UTF-8 字符串
        except UnicodeDecodeError:
            return obj.hex()  # 如果解码失败，返回十六进制字符串
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

def deserialize_flatbuffer(bytes_data: bytes, flatbuffers_dir: Path, table_type: str):
    """
    反序列化 FlatBuffers 数据并返回字典形式的字段值。
    """
    flatbuffer_class_name = table_type
    flatbuffer_module_path = flatbuffers_dir / f"{flatbuffer_class_name}.py"
    if not flatbuffer_module_path.exists():
        print(f"FlatBuffers class file {flatbuffer_module_path} not found.")
        return None

    flatbuffer_module = dynamic_import_module(flatbuffer_module_path, flatbuffer_class_name)
    flatbuffer_class = getattr(flatbuffer_module, flatbuffer_class_name)

    # 获取 FlatBuffers 对象
    flatbuffer_obj = flatbuffer_class.GetRootAs(bytes_data, 0)

    # 动态获取 FlatBuffers 对象的字段
    result = {}
    for field_name in dir(flatbuffer_obj):
        if field_name.startswith("_"):
            continue

        try:
            attr = getattr(flatbuffer_obj, field_name)

            if callable(attr):
                # 确保是无参数的方法，才调用
                sig = inspect.signature(attr)
                if len(sig.parameters) == 0:
                    value = attr()
                else:
                    continue  # 跳过需要参数的函数
            else:
                value = attr

            value = convert_to_basic_types(value)
            result[field_name] = value
        except Exception as e:
            print(f"Error reading field {field_name} in {table_type}: {e}")
    return result
