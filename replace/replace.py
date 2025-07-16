import os
import re
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from zhconv import convert

# ========== 第一部分：国际服/国服 → 日服替换 ==========

def read_ba_versions(env_file_path: Path) -> Dict[str, str]:
    pattern = r'BA_VERSION_NAME(_CN|_GL)?\s*=\s*([^\n]+)'
    with open(env_file_path, encoding='utf-8') as f:
        content = f.read()
    matches = re.findall(pattern, content)
    return {f'BA_VERSION_NAME{m[0]}': m[1].strip() for m in matches}

def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_to)
        return True
    except Exception as e:
        print(f"解压失败 {zip_path}: {e}")
        return False

def load_config(config_path: Path) -> Dict[str, Any]:
    try:
        return json.loads(config_path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"读取配置失败: {e}")
        return {}

def process_json_files(jp_dir: Path, other_dir: Path, cfg: Dict[str, Any], server: str):
    schema = cfg.get('DBSchema', {}).get(server)
    if not schema:
        print(f"[调试] {server} 无 schema")
        return

    # 反向映射：日服字段 → 来源字段
    jp_schema = cfg['DBSchema']['日服']
    field_map = {
        jp_file: (jp_keys[0], jp_keys[1:], src_keys[1:])
        for jp_file, jp_keys in jp_schema.items()
        for src_file, src_keys in schema.items()
        if jp_file == src_file
    }

    for json_file, (id_key, tgt_fields, src_fields) in field_map.items():
        jp_file = jp_dir / json_file
        other_file = other_dir / json_file
        if not (jp_file.exists() and other_file.exists()):
            continue

        jp_data = json.loads(jp_file.read_text(encoding='utf-8'))
        other_data = json.loads(other_file.read_text(encoding='utf-8'))

        # 按顺序建立国际服列表（保留重复 & 顺序）
        other_list = [
            (item.get(id_key), {k: item.get(k) for k in src_fields})
            for item in other_data
            if id_key in item
        ]

        # 迭代器：每次遇到相同 ID 就顺序取用
        from collections import defaultdict, deque
        buckets = defaultdict(deque)
        for oid, fields in other_list:
            buckets[oid].append(fields)

        updated = 0
        for item in jp_data:
            oid = item.get(id_key)
            if oid in buckets and buckets[oid]:
                src_fields_map = buckets[oid].popleft()
                for tgt, src in zip(tgt_fields, src_fields):
                    if src in src_fields_map and tgt in item:
                        item[tgt] = src_fields_map[src]
                        updated += 1

        if updated:
            jp_file.write_text(json.dumps(jp_data, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"{json_file}: 替换 {updated} 处")



def repack_zip(src_dir: Path, dst_zip: Path):
    with zipfile.ZipFile(dst_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in src_dir.rglob('*'):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir))

def run_first_stage():
    env_file = Path("ba.env")
    cfg_file = Path("配置.json")
    versions = read_ba_versions(env_file)
    cfg = load_config(cfg_file)
    for server in ["国际服", "国服"]:
        jp_ver = versions["BA_VERSION_NAME"]
        jp_zip = Path("BA-Text") / f"日服{jp_ver}.zip"
        if server == "国服":
            other_ver = versions["BA_VERSION_NAME_CN"]
            other_zip = Path("BA-Text") / f"国服{other_ver}.zip"
        else:
            other_ver = versions["BA_VERSION_NAME_GL"]
            other_zip = Path("BA-Assets-TableBundles") / f"国际服{other_ver}.zip"

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            jp_dir = tmp / "jp"
            other_dir = tmp / "other"
            jp_dir.mkdir(); other_dir.mkdir()
            if not extract_zip(jp_zip, jp_dir) or not extract_zip(other_zip, other_dir):
                return
            process_json_files(jp_dir, other_dir, cfg, server)
            repack_zip(jp_dir, jp_zip)
            print(f"{server} 处理完成 → {jp_zip}")

# ========== 第二部分：繁体→简体 + 名词替换 ==========

def convert_traditional_to_simplified(text: str) -> str:
    return convert(text, 'zh-cn')

def load_replacement_rules(replace_file: Path) -> dict:
    raw = replace_file.read_text(encoding='utf-8')
    # 按行分割，但不去掉换行符
    lines = [ln.rstrip('\r\n') for ln in raw.splitlines()]
    # 过滤空行
    lines = [ln for ln in lines if ln.strip()]
    # 每两行一组
    return {lines[i]: lines[i+1] for i in range(0, len(lines), 2) if i+1 < len(lines)}

def process_value(value: str, replacements: dict) -> str:
    if not isinstance(value, str):
        return value
    simplified = convert_traditional_to_simplified(value)
    for orig, repl in replacements.items():
        simplified = simplified.replace(orig, repl)
    return simplified

def process_json_file(path: Path, reps: dict) -> bool:
    data = json.loads(path.read_text(encoding='utf-8'))
    modified = False
    def walk(obj):
        nonlocal modified
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str):
                    new = process_value(v, reps)
                    if new != v:
                        obj[k] = new
                        modified = True
                else:
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(data)
    if modified:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return modified

def run_second_stage():
    rules = load_replacement_rules(Path("替换名词.txt"))
    jp_zip = Path("BA-Text") / f"日服{read_ba_versions(Path('BA-Assets-TableBundles/ba.env')).get('BA_VERSION_NAME')}.zip"
    out_zip = Path("BA-Text/日服.zip")
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        extract_zip(jp_zip, tmp)
        count = 0
        for p in tmp.rglob("*.json"):
            if process_json_file(p, rules):
                count += 1
        repack_zip(tmp, out_zip)
        print(f"第二阶段处理 {count} 个 JSON → {out_zip}")


if __name__ == "__main__":
    print("=== 第一阶段：国际服/国服 → 日服 ===")
    run_first_stage()
    print("\n=== 第二阶段：繁体→简体 + 名词替换 ===")
    run_second_stage()
    print("\n全部完成！最终文件：BA-Text/日服.zip")
