import json
import os
import tempfile
import zipfile
from pathlib import Path

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


# ---------- 主流程：日服 → 汉化 ----------
def replace_jp_with_cn(temp_dir: Path):
    config = load_json(config_path)
    schema = config.get("DBSchema", {}).get("日服", {})

    # 1. 解压
    with zipfile.ZipFile(rizip_path, 'r') as zf:
        zf.extractall(temp_dir)

    for filename, keys in schema.items():
        if not keys:
            continue

        hanhua_file = Path(hanhua_dir) / filename
        target_file = temp_dir / filename

        if not hanhua_file.exists():
            print(f"跳过：汉化文件 {filename} 不存在")
            continue
        if not target_file.exists():
            print(f"跳过：目标文件 {filename} 不存在")
            continue

        hanhua_rows = load_json(hanhua_file)
        target_rows = load_json(target_file)

        key_field = keys[0]
        jp_field  = keys[1]
        cn_field  = jp_field.replace("JP", "CN") \
                            .replace("Jp", "Cn") \
                            .replace("jp", "cn")

        # { key_value : [cn_text_or_none, ...] }
        cn_map = {}
        for row in hanhua_rows:
            k = row.get(key_field)
            if k is None:
                continue
            # 没有 CN 字段视为 None，后面直接跳过不替换
            text_cn = row.get(cn_field)
            cn_map.setdefault(k, []).append(text_cn)

        # 按出现顺序替换
        counter = {}          # { key_value : 已用索引 }
        for row in target_rows:
            k = row.get(key_field)
            if k is None or k not in cn_map:
                continue

            idx = counter.setdefault(k, 0)
            if idx >= len(cn_map[k]):
                continue

            text_cn = cn_map[k][idx]
            if text_cn is not None and text_cn != "":
                row[jp_field] = text_cn
            # 否则保留原 JP 文本

            counter[k] += 1

        save_json(target_file, target_rows)
        print(f"[替换] {filename} 完成")


# ---------- 补丁：覆盖官方键值 ----------
def apply_patch(temp_dir: Path, patch_map: dict[str, dict[int, dict]]):
    """
    patch_map 结构：
    {
        "LocalizeExcel.json": {
            2673619827: {...整行新值...},
            ...
        },
        ...
    }
    """
    for filename, key_patch in patch_map.items():
        target = temp_dir / filename
        if not target.exists():
            print(f'[WARN] 未找到 {filename}，跳过')
            continue

        original_rows = load_json(target)
        if not original_rows:
            continue

        # 动态取主键列名：补丁里第一条记录的键
        primary_key = next(iter(key_patch.values())).keys().__iter__().__next__()
        key_to_index = {row.get(primary_key): idx
                        for idx, row in enumerate(original_rows)
                        if primary_key in row}

        patched = 0
        for key, new_row in key_patch.items():
            if key in key_to_index:
                original_rows[key_to_index[key]] = new_row
                patched += 1

        save_json(target, original_rows)
        print(f'[INFO] {filename} 已打补丁 {patched} 处')


# ---------- 打包 ----------
def repack_zip(temp_dir: Path):
    with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                abs_path = Path(root) / file
                arc_path = abs_path.relative_to(temp_dir)
                zf.write(abs_path, arc_path)
    print(f"已覆盖 {rizip_path}")


# ---------- 入口 ----------
if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1) 用汉化后 JSON 替换 JP 文本
        replace_jp_with_cn(tmp_path)

        # 2) （可选）再额外打补丁，如需要取消注释
        # patch_map = load_json("patch.json")      # 自己准备
        # apply_patch(tmp_path, patch_map)

        # 3) 重新打包
        repack_zip(tmp_path)
