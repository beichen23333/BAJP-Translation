import json
import os
import sys
import zipfile
import tempfile
from pathlib import Path

# 配置路径
config_path = Path('配置.json')
hanhua_dir = Path('BA-Text/汉化后')
rizip_path = Path('BA-Text/日服.zip')

def log(message):
    """统一的日志记录函数"""
    print(f"[{os.path.basename(__file__)}] {message}")

def load_json(path):
    """加载JSON文件，带有错误处理"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"❌ 加载JSON文件失败: {path}\n错误: {str(e)}")
        raise

def save_json(path, data):
    """保存JSON文件，带有错误处理"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        log(f"❌ 保存JSON文件失败: {path}\n错误: {str(e)}")
        raise

def replace_jp_with_cn(temp_dir):
    """主替换逻辑"""
    temp_dir = Path(temp_dir)
    log("开始处理日服汉化替换...")
    
    try:
        # 加载配置
        cfg = load_json(config_path)
        schema = cfg.get("DBSchema", {}).get("日服", {})
        log(f"加载配置成功，找到{len(schema)}个文件配置")

        # 解压日服zip
        with zipfile.ZipFile(rizip_path, 'r') as zf:
            zf.extractall(temp_dir)
        log(f"解压完成到临时目录: {temp_dir}")

        processed_files = 0
        replaced_items = 0

        for filename, keys in schema.items():
            if not keys or len(keys) < 2:
                log(f"⚠️ 跳过：文件 {filename} 配置不完整")
                continue

            hanhua_file = hanhua_dir / filename
            target_file = temp_dir / filename

            if not hanhua_file.exists():
                log(f"⚠️ 跳过：汉化文件不存在 {hanhua_file}")
                continue
            if not target_file.exists():
                log(f"⚠️ 跳过：目标文件不存在 {target_file}")
                continue

            # 加载数据
            hanhua_data = load_json(hanhua_file)
            target_data = load_json(target_file)
            
            key_field, jp_field = keys[0], keys[1]
            cn_field = jp_field.replace('JP', 'CN').replace('Jp', 'Cn').replace('jp', 'cn')

            # 构建映射
            text_map = {}
            for item in hanhua_data:
                key = item.get(key_field)
                if key is None:
                    continue
                
                jp_text = item.get(jp_field, "")
                cn_text = item.get(cn_field, "")
                text = cn_text if cn_text else jp_text
                
                if text:
                    text_map.setdefault(key, []).append(text)

            # 执行替换
            counter = {}
            file_replaced = 0
            for item in target_data:
                key = item.get(key_field)
                if key not in text_map:
                    continue
                
                idx = counter.get(key, 0)
                if idx >= len(text_map[key]):
                    continue
                
                if item.get(jp_field, "") != text_map[key][idx]:
                    item[jp_field] = text_map[key][idx]
                    file_replaced += 1
                
                counter[key] = idx + 1

            # 保存文件
            save_json(target_file, target_data)
            save_json(hanhua_file, hanhua_data)
            
            processed_files += 1
            replaced_items += file_replaced
            log(f"处理完成: {filename} (替换了 {file_replaced} 处)")

        log(f"\n处理总结:\n"
            f"总处理文件数: {processed_files}\n"
            f"总替换条目数: {replaced_items}")

        return processed_files, replaced_items

    except Exception as e:
        log(f"❌ 处理过程中发生错误: {str(e)}")
        raise

def repack_zip(temp_dir):
    """重新打包zip文件"""
    log("开始重新打包日服zip...")
    try:
        with zipfile.ZipFile(rizip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in Path(temp_dir).rglob('*'):
                if file.is_file():
                    arcname = file.relative_to(temp_dir)
                    zf.write(file, arcname)
        log(f"✅ 成功覆盖 {rizip_path}")
    except Exception as e:
        log(f"❌ 打包失败: {str(e)}")
        raise

def main():
    """主函数"""
    exit_code = 0
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            processed, replaced = replace_jp_with_cn(temp_dir)
            if processed == 0 or replaced == 0:
                log("⚠️ 警告: 没有处理任何文件或替换任何内容")
                exit_code = 1
            repack_zip(temp_dir)
    except Exception as e:
        log(f"❌ 程序异常终止: {str(e)}")
        exit_code = 2
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
