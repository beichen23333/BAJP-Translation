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

    # 1. 解压
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

        # ------------ 新增：补全缺失的 CN 字段 ------------
        # 重新加载，避免修改原文件
        hanhua_data = load_json(hanhua_file)

        jp_field = keys[1]
        cn_field = jp_field.replace("JP", "CN").replace("Jp", "Cn").replace("jp", "cn")

        # 同一个文件里可能出现多种 JP 字段，这里只关心当前 keys 指定的
        for item in hanhua_data:
            if jp_field not in item:
                continue
            # 只有当 CN 不存在或为空时才补
            if item.get(cn_field) in (None, ""):
                item[cn_field] = item[jp_field]

        # 保存回汉化文件（可选，也可不保存，视需求而定）
        save_json(hanhua_file, hanhua_data)
        # --------------------------------------------------

        # 继续原来的逻辑
        hanhua_data = load_json(hanhua_file)   # 重新加载，确保拿到补全后的数据
        target_data = load_json(target_file)

        key_field = keys[0]

        # 2. 建立同主键 → 中文文本列表（按出现顺序）
        cn_map = {}
        for item in hanhua_data:
            k = item.get(key_field)
            if k is None:
                continue
            # 此时 CN 字段一定存在且非空，无需再判断
            cn_map.setdefault(k, []).append(item[cn_field])

        # 3. 按顺序替换（与之前完全一致）
        counter = {}
        for item in target_data:
            k = item.get(key_field)
            if k is None or k not in cn_map:
                continue
            used = counter.setdefault(k, 0)
            if used >= len(cn_map[k]):
                continue
            item[jp_field] = cn_map[k][used]
            counter[k] += 1

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
