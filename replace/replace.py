import os
import re
import json
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from zhconv import convert

# ========== 第一阶段：国际服/国服 → 日服替换（不压缩回原ZIP） ==========

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

    jp_schema = cfg['DBSchema']['日服']
    field_map = {
        jp_file: (jp_keys[0], jp_keys[1:], src_keys[1:])
        for jp_file, jp_keys in jp_schema.items()
        for src_file, src_keys in schema.items()
        if jp_file == src_file
    }

    for json_file, (id_key, tgt_fields, src_fields) in field_map.items():
        jp_path = jp_dir / json_file
        other_path = other_dir / json_file
        if not (jp_path.exists() and other_path.exists()):
            continue

        jp_data = json.loads(jp_path.read_text(encoding='utf-8'))
        other_data = json.loads(other_path.read_text(encoding='utf-8'))

        other_list = [
            (item.get(id_key), {k: item.get(k) for k in src_fields})
            for item in other_data
            if id_key in item
        ]

        from collections import defaultdict, deque
        buckets = defaultdict(deque)
        for oid, fields in other_list:
            buckets[oid].append(fields)

        updated = 0
        for item in jp_data:
            oid = item.get(id_key)
            if oid in buckets and buckets[oid]:
                src_map = buckets[oid].popleft()
                for tgt, src in zip(tgt_fields, src_fields):
                    if src in src_map and tgt in item:
                        item[tgt] = src_map[src]
                        updated += 1

        if updated:
            jp_path.write_text(
                json.dumps(jp_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            print(f"{json_file}: 替换 {updated} 处")

def run_first_stage(tmp_root: Path) -> Path:
    env_file = Path("ba.env")
    cfg_file = Path("配置.json")
    versions = read_ba_versions(env_file)
    cfg = load_config(cfg_file)

    jp_ver = versions["BA_VERSION_NAME"]
    jp_zip = Path("BA-Text") / f"日服{jp_ver}.zip"
    jp_dir = tmp_root / "jp"

    for server in ["国际服", "国服"]:
        if server == "国服":
            other_ver = versions["BA_VERSION_NAME_CN"]
            other_zip = Path("BA-Text") / f"国服{other_ver}.zip"
        else:
            other_ver = versions["BA_VERSION_NAME_GL"]
            other_zip = Path("BA-Assets-TableBundles") / f"国际服{other_ver}.zip"
        other_dir = tmp_root / f"other_{server}"

        if not jp_dir.exists():
            jp_dir.mkdir(parents=True)
            if not extract_zip(jp_zip, jp_dir):
                continue
        other_dir.mkdir(parents=True, exist_ok=True)
        if not extract_zip(other_zip, other_dir):
            continue

        process_json_files(jp_dir, other_dir, cfg, server)
        print(f"{server} 处理完成")
    return jp_dir  # 返回处理后的目录，供第二阶段使用

# ========== 第二阶段：纯文本繁简转换 + 名词替换 ==========

def convert_traditional_to_simplified(text: str) -> str:
    return convert(text, 'zh-cn')

def load_replacement_rules(replace_file: Path) -> dict:
    raw = replace_file.read_text(encoding='utf-8')
    lines = [ln.rstrip('\r\n') for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    return {lines[i]: lines[i+1] for i in range(0, len(lines), 2) if i+1 < len(lines)}

def process_text_file(path: Path, replacements: dict) -> bool:
    original = path.read_text(encoding='utf-8')
    text = convert_traditional_to_simplified(original)
    for old, new in replacements.items():
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False

def run_second_stage(src_dir: Path):
    rules = load_replacement_rules(Path("替换名词.txt"))
    out_zip = Path("BA-Text/日服.zip")
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    for p in src_dir.rglob("*.json"):
        if process_text_file(p, rules):
            count += 1
    # 重新打包
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in src_dir.rglob('*'):
            if file.is_file():
                zf.write(file, file.relative_to(src_dir))
    print(f"第二阶段处理 {count} 个文件 → {out_zip}")

# ========== 主入口 ==========
if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        print("=== 第一阶段：国际服/国服 → 日服 ===")
        processed_dir = run_first_stage(tmp_path)
        print("\n=== 第二阶段：繁体→简体 + 名词替换 ===")
        run_second_stage(processed_dir)
        print("\n全部完成！最终文件：BA-Text/日服.zip")
