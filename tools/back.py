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

def ensure_cn_fields(data, jp_fields):
    # Ensure CN fields exist (temporary for mapping)
    modified = False
    for item in data:
        for jp_field in jp_fields:
            cn_field = get_cn_field(jp_field)
            if cn_field not in item or item[cn_field] in (None, ""):
                jp_value = item.get(jp_field, "")
                item[cn_field] = jp_value
                modified = True
    return modified

def remove_additional_fields(data, jp_fields):
    # Remove temporary CN fields and any Tr/Re fields after processing
    for item in data:
        for jp_field in jp_fields:
            # Remove CN fields
            cn_field = get_cn_field(jp_field)
            if cn_field in item:
                del item[cn_field]
            
            # Remove Re fields (derived from JP)
            re_field = get_re_key(jp_field)
            if re_field in item:
                del item[re_field]
            
            # Remove Tr fields (derived from KR, but we'll check anyway)
            tr_field = get_tr_key(jp_field)
            if tr_field in item:
                del item[tr_field]

def replace_jp_with_cn(modified_dir, config_path):
    modified_dir = Path(modified_dir)
    print("Starting JP to CN text replacement...")
    
    try:
        cfg = load_json(config_path)
        processed_files = 0
        replaced_items = 0
        skipped_empty = 0
        removed_fields = 0

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
                    continue  # Skip if file not found
                
                source_data = load_json(source_file)
                key_field = fields[0]
                jp_fields = fields[1:] if len(fields) > 2 else [fields[1]]

                # Temporarily ensure CN fields exist for mapping
                ensure_cn_fields(source_data, jp_fields)

                # Build text mapping
                text_maps = {field: {} for field in jp_fields}
                for item in source_data:
                    key = item.get(key_field)
                    if key is None:
                        continue
                    
                    for jp_field in jp_fields:
                        cn_field = get_cn_field(jp_field)
                        text_to_use = item.get(cn_field, item.get(jp_field, ""))
                        text_maps[jp_field].setdefault(key, []).append(text_to_use)

                # Perform replacements
                file_replaced = 0
                file_skipped = 0
                counters = {field: {} for field in jp_fields}
                
                for item in source_data:
                    key = item.get(key_field)
                    if key is None:
                        continue
                    
                    for jp_field in jp_fields:
                        if key not in text_maps[jp_field]:
                            continue
                        
                        idx = counters[jp_field].get(key, 0)
                        if idx >= len(text_maps[jp_field][key]):
                            continue
                        
                        new_text = text_maps[jp_field][key][idx]
                        original = item.get(jp_field, "")
                        
                        if new_text == original:
                            file_skipped += 1
                        else:
                            item[jp_field] = new_text
                            file_replaced += 1
                        
                        counters[jp_field][key] = idx + 1

                # Remove temporary CN fields and any Tr/Re fields
                remove_additional_fields(source_data, jp_fields)
                
                save_json(source_file, source_data)
                
                processed_files += 1
                replaced_items += file_replaced
                skipped_empty += file_skipped

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
