import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

ZIP_PATH   = Path('BA-Text/日服.zip')
PATCH_JSON = Path('replace/特殊修改.json')

def load_patch_map(patch_file: Path) -> dict[str, dict[int, dict]]:
    if not patch_file.exists():
        raise FileNotFoundError(patch_file)

    raw = json.loads(patch_file.read_text(encoding='utf-8'))
    patch_map = {}

    for filename, rows in raw.items():
        key_map = {}
        for row in rows:
            int_fields = [k for k, v in row.items() if isinstance(v, int)]
            if not int_fields:
                raise ValueError(f'{filename} 中的条目找不到整数主键：{row}')
            key = row[int_fields[0]]
            key_map[key] = row
        patch_map[filename] = key_map
    return patch_map



def apply_patch(temp_dir: Path, patch_map: dict[str, dict[int, dict]]):
    for filename, key_patch in patch_map.items():
        target = temp_dir / filename
        if not target.exists():
            print(f'[WARN] 未找到 {filename}，跳过')
            continue

        original_rows = json.loads(target.read_text(encoding='utf-8'))
        key_to_index = {row['Key']: idx for idx, row in enumerate(original_rows)}

        patched = 0
        for key, new_row in key_patch.items():
            if key in key_to_index:
                original_rows[key_to_index[key]] = new_row
                patched += 1

        target.write_text(
            json.dumps(original_rows, ensure_ascii=False, indent=4),
            encoding='utf-8'
        )
        print(f'[INFO] {filename} 已打补丁 {patched} 处')


def rebuild_zip(source_dir: Path, dest_zip: Path):
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                full_path = Path(root) / file
                arc_name  = full_path.relative_to(source_dir)
                zf.write(full_path, arc_name)
    print(f'[INFO] 已重新打包为 {dest_zip}')


def main():
    if not ZIP_PATH.exists():
        raise FileNotFoundError(ZIP_PATH)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
            zf.extractall(tmp_path)
        print(f'[INFO] 已解压到 {tmp_path}')

        patch_map = load_patch_map(PATCH_JSON)
        apply_patch(tmp_path, patch_map)

        # 把修改后的内容重新压缩回原 zip
        rebuild_zip(tmp_path, ZIP_PATH)

    print('[INFO] 全部完成！')


if __name__ == '__main__':
    main()
