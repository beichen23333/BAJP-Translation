import json
import sys
from pathlib import Path
import argparse

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load JSON: {path}\nError: {str(e)}")
        raise

def save_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save JSON: {path}\nError: {str(e)}")
        raise

def get_cn_field(jp_field):
    # Convert JP field name to CN field name
    if 'JP' in jp_field:
        return jp_field.replace('JP', 'CN')
    elif 'Jp' in jp_field:
        return jp_field.replace('Jp', 'Cn')
    elif 'jp' in jp_field:
        return jp_field.replace('jp', 'cn')
    return jp_field

def get_re_key(jp_key: str) -> str:
    return jp_key.replace("Jp", "Re").replace("jp", "re").replace("JP", "RE")

def get_tr_key(kr_key: str) -> str:
    return kr_key.replace("Kr", "Tr").replace("kr", "tr").replace("KR", "TR")

def is_jp_field(field_name):
    """判断字段是否为JP字段"""
    jp_indicators = ['JP', 'Jp', 'jp', 'Japanese']
    return any(indicator in field_name for indicator in jp_indicators)

def is_kr_field(field_name):
    """判断字段是否为KR字段"""
    kr_indicators = ['Kr', 'kr', 'KR', 'Korean', 'ScriptKr']
    return any(indicator in field_name for indicator in kr_indicators)

def replace_jp_with_cn(modified_dir, config_path):
    modified_dir = Path(modified_dir)
    print("Starting JP to CN text replacement...")
    
    try:
        cfg = load_json(config_path)
        processed_files = 0
        replaced_items = 0
        skipped_empty = 0

        # Process all files in DBSchema and ExcelTable
        for schema_type, schema in cfg.items():
            for filename, fields in schema.items():
                if not fields or len(fields) < 2:
                    continue  # Skip incomplete configurations

                # Check both NewBack and ReviseBack directories
                source_files = [
                    modified_dir / "NewBack" / schema_type / filename,
                    modified_dir / "ReviseBack" / schema_type / filename
                ]
                
                source_file = None
                for f in source_files:
                    if f.exists():
                        source_file = f
                        break
                
                if source_file is None:
                    print(f"File not found: {filename}")
                    continue
                
                source_data = load_json(source_file)
                if not source_data:
                    print(f"Empty data: {filename}")
                    continue
                    
                key_field = fields[0]
                
                # 只提取真正的JP字段（包含JP、Jp、jp的字段）
                jp_fields = [field for field in fields[1:] if is_jp_field(field)]
                
                if not jp_fields:
                    print(f"No JP fields found in {filename}, skipping")
                    continue
                
                print(f"\nProcessing {filename}:")
                print(f"Key field: {key_field}")
                print(f"JP fields: {jp_fields}")
                print(f"Original fields in data: {list(source_data[0].keys())}")

                # 第一步：用CN字段的内容替换JP字段的内容
                file_replaced = 0
                file_skipped = 0
                
                for item in source_data:
                    for jp_field in jp_fields:
                        cn_field = get_cn_field(jp_field)
                        
                        # 如果存在CN字段，就用CN字段的内容替换JP字段
                        if cn_field in item:
                            cn_text = item[cn_field]
                            jp_text = item.get(jp_field, "")
                            
                            if cn_text != jp_text:
                                item[jp_field] = cn_text
                                file_replaced += 1
                            else:
                                file_skipped += 1

                # 第二步：删除CN、Re、Tr字段，但保留JP字段和KR字段！
                fields_to_remove = []
                
                # 删除与JP字段对应的CN和Re字段
                for jp_field in jp_fields:
                    cn_field = get_cn_field(jp_field)
                    re_field = get_re_key(jp_field)
                    
                    if cn_field in source_data[0] and cn_field not in fields_to_remove:
                        fields_to_remove.append(cn_field)
                    if re_field in source_data[0] and re_field not in fields_to_remove:
                        fields_to_remove.append(re_field)
                
                # 删除与KR字段对应的Tr字段
                for field in list(source_data[0].keys()):
                    if is_kr_field(field):
                        tr_field = get_tr_key(field)
                        if tr_field in source_data[0] and tr_field not in fields_to_remove:
                            fields_to_remove.append(tr_field)
                
                # 确保不删除JP字段和KR字段！
                all_fields_to_keep = jp_fields + [field for field in source_data[0].keys() if is_kr_field(field)] + [key_field, 'VoiceId']
                for field in all_fields_to_keep:
                    if field in fields_to_remove:
                        fields_to_remove.remove(field)
                
                print(f"Fields to remove: {fields_to_remove}")
                
                # 删除指定的字段
                for item in source_data:
                    for field in fields_to_remove:
                        if field in item:
                            del item[field]
                
                # 保存前检查保留的字段
                remaining_fields = list(source_data[0].keys()) if source_data else []
                print(f"Remaining fields after processing: {remaining_fields}")
                
                save_json(source_file, source_data)
                
                processed_files += 1
                replaced_items += file_replaced
                skipped_empty += file_skipped

                print(f"  - Replaced: {file_replaced}, Skipped: {file_skipped}")

        # Print final summary
        print("\nProcessing summary:")
        print(f"Total files processed: {processed_files}")
        print(f"Total items replaced: {replaced_items}")
        print(f"Total items skipped (no change needed): {skipped_empty}")

        return processed_files, replaced_items

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='JP to CN text replacement tool')
    parser.add_argument('config_path', help='Path to configuration JSON')
    parser.add_argument('modified_dir', help='Directory containing NewBack and ReviseBack folders')
    args = parser.parse_args()

    exit_code = 0
    try:
        processed, replaced = replace_jp_with_cn(
            Path(args.modified_dir),
            Path(args.config_path)
        )
        if replaced == 0:
            print("No replacements were made")
            exit_code = 1
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        exit_code = 2
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
