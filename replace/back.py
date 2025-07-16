import json
import os
import shutil
import zipfile
import tempfile

config_path = '配置.json'
hanhua_dir = 'BA-Text/汉化后'
rizip_path = 'BA-Text/日服.zip'

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def replace_jp_with_cn(temp_dir):
    config = load_json(config_path)
    schema = config.get("DBSchema", {}).get("日服", {})

    # 解压原始zip到临时目录
    with zipfile.ZipFile(rizip_path, 'r') as zf:
        zf.extractall(temp_dir)

    for filename, keys in schema.items():
        if not keys:
            continue
        jp_field = keys[-1]  # 获取JP后缀的字段名
        cn_field = jp_field.replace("JP", "CN").replace("Jp", "Cn").replace("jp", "cn")

        hanhua_file = os.path.join(hanhua_dir, filename)
        target_file = os.path.join(temp_dir, filename)

        if not os.path.exists(hanhua_file):
            print(f"跳过：汉化文件 {filename} 不存在")
            continue

        if not os.path.exists(target_file):
            print(f"跳过：目标文件 {filename} 不存在")
            continue

        hanhua_data = load_json(hanhua_file)
        target_data = load_json(target_file)

        # 创建索引字典，按ID分组所有对应的CN文本
        key_field = keys[0]
        index = {}
        for item in hanhua_data:
            if key_field not in item or cn_field not in item:
                continue
            key = item[key_field]
            if key not in index:
                index[key] = []
            index[key].append(item[cn_field])

        # 替换目标文件中的文本，按顺序替换
        for item in target_data:
            key = item.get(key_field)
            if key in index and jp_field in item:
                # 获取该ID对应的所有CN文本
                cn_texts = index[key]
                # 获取该ID对应的所有JP文本（可能是一个列表或单个值）
                jp_texts = item[jp_field] if isinstance(item[jp_field], list) else [item[jp_field]]
                
                # 按顺序替换，确保不会超出范围
                for i in range(min(len(jp_texts), len(cn_texts))):
                    if i < len(cn_texts):
                        if isinstance(item[jp_field], list):
                            item[jp_field][i] = cn_texts[i]
                        else:
                            item[jp_field] = cn_texts[i]
                            break  # 如果是单个值，只替换第一个

        save_json(target_file, target_data)
        print(f"[替换] {filename} 完成")

def repack_zip(temp_dir):
    # 直接重新打包为zip（覆盖原文件）
    with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_path = os.path.relpath(abs_path, temp_dir)
                zf.write(abs_path, arc_path)

    print(f"已覆盖 {rizip_path}")

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        replace_jp_with_cn(temp_dir)
        repack_zip(temp_dir)
