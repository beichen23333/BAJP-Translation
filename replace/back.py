import json
import os
import re
import shutil
import zipfile
import tempfile
from pathlib import Path

# 使用Path对象更安全地处理路径
config_path = Path('配置.json')
hanhua_dir = Path('BA-Text/汉化后')
rizip_path = Path('BA-Text/日服.zip')

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def debug_print(data, limit=3):
    """调试用：打印数据结构"""
    print(f"数据样本（前{limit}项）:")
    for i, item in enumerate(data[:limit], 1):
        print(f"{i}. {json.dumps(item, ensure_ascii=False)}")
    print(f"...共{len(data)}项\n")

def replace_jp_with_cn(temp_dir):
    temp_dir = Path(temp_dir)
    print(f"\n{'='*40}\n开始处理...")
    
    try:
        cfg = load_json(config_path)
        schema = cfg.get("DBSchema", {}).get("日服", {})
        print(f"加载配置成功，找到{len(schema)}个文件配置")

        # 解压日服zip
        with zipfile.ZipFile(rizip_path, 'r') as zf:
            zf.extractall(temp_dir)
        print(f"解压完成到临时目录: {temp_dir}")

        for filename, keys in schema.items():
            if not keys:
                continue

            hanhua_file = hanhua_dir / filename
            target_file = temp_dir / filename

            print(f"\n处理文件: {filename}")
            print(f"汉化文件路径: {hanhua_file}")
            print(f"目标文件路径: {target_file}")

            if not hanhua_file.exists():
                print(f"⚠️ 跳过：汉化文件不存在")
                continue
            if not target_file.exists():
                print(f"⚠️ 跳过：目标文件不存在")
                continue

            # 加载数据
            hanhua_data = load_json(hanhua_file)
            target_data = load_json(target_file)
            
            print("\n汉化文件数据样本:")
            debug_print(hanhua_data)
            print("目标文件数据样本:")
            debug_print(target_data)

            key_field, jp_field = keys[0], keys[1]
            cn_field = jp_field.replace('JP', 'CN').replace('Jp', 'Cn').replace('jp', 'cn')
            print(f"\n关键字段: 主键={key_field}, JP字段={jp_field}, CN字段={cn_field}")

            # 构建映射
            text_map = {}
            for item in hanhua_data:
                key = item.get(key_field)
                if key is None:
                    continue
                cn_text = item.get(cn_field, "")
                jp_text = item.get(jp_field, "")
                text = cn_text if cn_text else jp_text
                text_map.setdefault(key, []).append(text)
                print(f"映射: {key} → '{text}' (CN: '{cn_text}', JP: '{jp_text}')")

            # 执行替换
            counter = {}
            changed = 0
            for item in target_data:
                key = item.get(key_field)
                if key not in text_map:
                    continue
                
                idx = counter.get(key, 0)
                if idx >= len(text_map[key]):
                    continue
                
                original = item.get(jp_field, "")
                new_text = text_map[key][idx]
                if original != new_text:
                    item[jp_field] = new_text
                    changed += 1
                    print(f"替换: {key}[{idx}] '{original}' → '{new_text}'")
                
                counter[key] = idx + 1

            print(f"\n替换统计: 共{changed}处修改")
            
            # 保存文件
            save_json(target_file, target_data)
            save_json(hanhua_file, hanhua_data)
            print(f"✅ 文件处理完成: {filename}")

    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        raise

def repack_zip(temp_dir):
    print(f"\n{'='*40}\n重新打包...")
    with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in Path(temp_dir).rglob('*'):
            if file.is_file():
                arcname = file.relative_to(temp_dir)
                zf.write(file, arcname)
                print(f"添加: {arcname}")
    print(f"✅ 已覆盖 {rizip_path}")

if __name__ == "__main__":
    print("="*40)
    print("蓝档汉化替换工具")
    print("="*40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            replace_jp_with_cn(temp_dir)
            repack_zip(temp_dir)
        except Exception as e:
            print(f"❌ 程序异常: {str(e)}")
        finally:
            input("\n按Enter键退出...")
