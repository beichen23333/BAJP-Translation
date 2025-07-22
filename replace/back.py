import json
import os
import re
import shutil
import zipfile
import tempfile

config_path = '配置.json'
hanhua_dir = 'BA-Text/汉化后'
rizip_path = 'BA-Text/日服.zip'

# ---------- 工具函数 ----------
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ---------- 动态补全缺失 CN ----------
JP_RE = re.compile(r'^(.*?)([Jj][Pp])$')

def fill_missing_cn(data):
    for item in data:
        for jp_key, jp_val in list(item.items()):
            m = JP_RE.match(jp_key)
            if not m:
                continue
            prefix = m.group(1)
            suffix = m.group(2)
            cn_key = prefix + suffix.replace('Jp', 'Cn').replace('JP', 'CN').replace('jp', 'cn')
            if cn_key not in item or item[cn_key] in (None, ""):
                item[cn_key] = jp_val

# ---------- 主流程 ----------
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

        # 读取
        hanhua_data = load_json(hanhua_file)
        target_data = load_json(target_file)

        key_field = keys[0]
        jp_field  = keys[1]
        cn_field  = jp_field.replace("JP", "CN").replace("Jp", "Cn").replace("jp", "cn")

        # ---------- 3. 建立同主键 → 中文文本列表（必须一一对应，含空串） ----------
        cn_map = {}
        for item in hanhua_data:
            k = item.get(key_field)
            if k is None:
                continue
            # 有 TextCn 就用 TextCn，否则用空串占位，保证顺序不乱
            text_cn = item.get(cn_field) if item.get(cn_field) not in (None, "") else item.get(jp_field, "")
            cn_map.setdefault(k, []).append(text_cn)
        save_json(target_file, target_data)          # 写回 temp 供打包
        save_json(hanhua_file, hanhua_data)          # ★覆盖汉化后目录
        print(f"[替换] {filename} 完成")

        # ---------- 4. 按顺序替换（顺序与汉化文件完全一致） ----------
        counter = {}
        for item in target_data:
            k = item.get(key_field)
            if k is None or k not in cn_map:
                continue
            used = counter.setdefault(k, 0)
            if used >= len(cn_map[k]):
                continue
            # 直接替换，即使 TextJp 是空串也照写
            item[jp_field] = cn_map[k][used]
            counter[k] += 1


def repack_zip(temp_dir):
    # 直接重新打包为 zip（覆盖原文件）
    with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arc_path = os.path.relpath(abs_path, temp_dir)
                zf.write(abs_path, arc_path)
    print(f"已覆盖 {rizip_path}")

# ---------- 入口 ----------
if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        replace_jp_with_cn(temp_dir)
        repack_zip(temp_dir)
