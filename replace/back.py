import json
import os
import re
import shutil
import zipfile
import tempfile

config_path   = '配置.json'
hanhua_dir    = 'BA-Text/汉化后'
rizip_path    = 'BA-Text/日服.zip'

# ---------- 工具 ----------
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ---------- 动态补 CN ----------
JP_RE = re.compile(r'^(.*?)(([Jj][Pp])|([Kk][Rr])|([Ee][Nn])|([Tt][Ww]))$')

def fill_cn_by_jp(data):
    for item in data:
        for key, val in list(item.items()):
            m = JP_RE.match(key)
            if not m or m.group(2).lower() != 'jp':
                continue   # 只处理 JP
            prefix = m.group(1)
            cn_key = prefix + m.group(2).replace('Jp','Cn').replace('JP','CN').replace('jp','cn')
            if cn_key not in item or item[cn_key] in (None, ""):
                item[cn_key] = val

# ---------- 主流程 ----------
def replace_jp_with_cn(temp_dir):
    cfg    = load_json(config_path)
    schema = cfg.get("DBSchema", {}).get("日服", {})

    with zipfile.ZipFile(rizip_path, 'r') as zf:
        zf.extractall(temp_dir)

    for filename, keys in schema.items():
        if not keys:
            continue

        hanhua_file = os.path.join(hanhua_dir, filename)
        target_file = os.path.join(temp_dir, filename)

        if not os.path.exists(hanhua_file) or not os.path.exists(target_file):
            continue

        hanhua = load_json(hanhua_file)
        target = load_json(target_file)

        key_field = keys[0]
        jp_field  = keys[1]
        cn_field  = jp_field.replace('JP','CN').replace('Jp','Cn').replace('jp','cn')

        # 1. 就地补全缺失 CN
        for it in hanhua:
            if jp_field in it and (cn_field not in it or it[cn_field] in (None, "")):
                it[cn_field] = it[jp_field]

        # 2. 把汉化文件按 GroupId → 顺序列表（含空串）
        cn_by_gid = {}
        for it in hanhua:
            gid = it.get(key_field)
            if gid is None:
                continue
            cn_by_gid.setdefault(gid, []).append(it.get(cn_field, ''))

        # 3. 按顺序替换目标文件
        counter = {}
        for it in target:
            gid = it.get(key_field)
            if gid is None or gid not in cn_by_gid:
                continue
            idx = counter.setdefault(gid, 0)
            if idx >= len(cn_by_gid[gid]):
                continue
            it[jp_field] = cn_by_gid[gid][idx]
            counter[gid] += 1

        # 4. 写回
        save_json(target_file, target)   # temp 目录
        save_json(hanhua_file, hanhua)   # 覆盖汉化后
        print(f"[完成] {filename}")


def repack_zip(temp_dir):
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
