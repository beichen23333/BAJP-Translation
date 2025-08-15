import json
import os
import tempfile
import zipfile
from pathlib import Path

rizip_path = 'BA-Text/日服.zip'

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def apply_patch(temp_dir: Path, patch_map: dict):
    for filename, patches in patch_map.items():
        target = temp_dir / filename
        if not target.exists():
            print(f'[WARN] 未找到 {filename}，跳过')
            continue

        original_data = load_json(target)
        if not original_data:
            continue

        # 动态确定主键字段（从补丁的第一个条目中找出数字类型的键）
        if not patches:
            continue
            
        # 找出可能是主键的字段（值为数字的字段）
        potential_keys = [k for k, v in patches[0].items() if isinstance(v, (int, float))]
        if not potential_keys:
            print(f'[ERROR] {filename} 无法确定主键（没有数字类型字段），跳过')
            continue
            
        primary_key = potential_keys[0]  # 使用第一个数字字段作为主键
        print(f'[DEBUG] 为 {filename} 自动选择主键: {primary_key}')

        # 创建主键到行索引的映射
        key_to_index = {}
        for idx, row in enumerate(original_data):
            if primary_key in row:
                key_to_index[row[primary_key]] = idx

        patched = 0
        for patch in patches:
            if primary_key not in patch:
                continue
                
            key = patch[primary_key]
            if key in key_to_index:
                # 合并原有行和补丁行，补丁行优先
                original_data[key_to_index[key]].update(patch)
                patched += 1

        save_json(target, original_data)
        print(f'[INFO] {filename} 已打补丁 {patched} 处（共 {len(patches)} 个补丁）')

def repack_zip(temp_dir: Path):
    with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(temp_dir):
            for file in files:
                abs_path = Path(root) / file
                arc_path = abs_path.relative_to(temp_dir)
                zf.write(abs_path, arc_path)
    print(f"已覆盖 {rizip_path}")

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        
        # 解压原始文件
        with zipfile.ZipFile(rizip_path, 'r') as zf:
            zf.extractall(tmp_path)
        
        # 应用补丁
        patch_map = load_json("特殊修改.json")
        apply_patch(tmp_path, patch_map)
        
        # 重新打包
        repack_zip(tmp_path)
