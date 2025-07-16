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

        # 主键字段
        key_field = keys[0]

        # 建立多字段的 CN 映射
        # index = { key_value: { jp_field1: [cn1, cn2, ...], jp_field2: [...], ... } }
        index = {}
        for item in hanhua_data:
            k = item.get(key_field)
            if k is None:
                continue
            if k not in index:
                index[k] = {}
            for jp_key in keys[1:]:
                cn_key = jp_key.replace("JP", "CN").replace("Jp", "Cn").replace("jp", "cn")
                if jp_key in item and cn_key in item:
                    index[k].setdefault(jp_key, []).append(item[cn_key])

        # 为每个 (key, jp_field) 维护计数器
        counter = {}

        for item in target_data:
            k = item.get(key_field)
            if k is None or k not in index:
                continue

            for jp_key in keys[1:]:
                if jp_key not in item:
                    continue

                # 计数器维度：(key, jp_key)
                counter_key = (k, jp_key)
                if counter_key not in counter:
                    counter[counter_key] = 0

                cn_texts = index[k].get(jp_key, [])
                if counter[counter_key] >= len(cn_texts):
                    continue

                jp_texts = item[jp_key] if isinstance(item[jp_key], list) else [item[jp_key]]
                for i in range(min(len(jp_texts), len(cn_texts) - counter[counter_key])):
                    cn_idx = counter[counter_key] + i
                    if isinstance(item[jp_key], list):
                        item[jp_key][i] = cn_texts[cn_idx]
                    else:
                        item[jp_key] = cn_texts[cn_idx]
                        break
                counter[counter_key] += len(jp_texts) if isinstance(item[jp_key], list) else 1

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
