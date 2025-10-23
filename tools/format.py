import json
import zipfile
from collections import defaultdict
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("jp_zip")
args = parser.parse_args()

zip_file_jp = args.jp_zip
zip_file_cn = "BA-Text/日服备份.zip"

jp_extract_dir = "日服解压"
cn_extract_dir = "日服备份解压"

excel_db_dir = "beicheng/latest/TableBundles/buildSrc/ExcelDB"
excel_dir = "beicheng/latest/TableBundles/buildSrc/Excel"

os.makedirs(jp_extract_dir, exist_ok=True)
os.makedirs(cn_extract_dir, exist_ok=True)
os.makedirs(excel_db_dir, exist_ok=True)
os.makedirs(excel_dir, exist_ok=True)

def extract_zip_to_folder(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

extract_zip_to_folder(zip_file_jp, jp_extract_dir)
extract_zip_to_folder(zip_file_cn, cn_extract_dir)

def get_json_files_from_folder(folder_path):
    json_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return sorted(json_files, key=lambda x: os.path.basename(x))

db_schema_jp_files = get_json_files_from_folder(os.path.join(jp_extract_dir, "DBSchema"))
db_schema_cn_files = get_json_files_from_folder(os.path.join(cn_extract_dir, "DBSchema"))

excel_table_jp_files = get_json_files_from_folder(os.path.join(jp_extract_dir, "ExcelTable"))
excel_table_cn_files = get_json_files_from_folder(os.path.join(cn_extract_dir, "ExcelTable"))

def match_files_by_name(jp_files, cn_files):
    pairs = []
    jp_dict = {os.path.basename(f): f for f in jp_files}
    cn_dict = {os.path.basename(f): f for f in cn_files}
    for name in jp_dict:
        if name in cn_dict:
            pairs.append((jp_dict[name], cn_dict[name]))
    return pairs

db_schema_pairs = match_files_by_name(db_schema_jp_files, db_schema_cn_files)
excel_table_pairs = match_files_by_name(excel_table_jp_files, excel_table_cn_files)

def load_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"文件加载失败: {file_path}\n错误信息: {str(e)}")
        return None

def is_special_file(file_name):
    return file_name == "ScenarioScriptExcel.json"

def process_special_pair(jp_file, cn_file, output_dir):
    file_name = os.path.basename(jp_file)
    print(f"\n正在处理特殊文件: {file_name}")

    cn_data = load_json_file(cn_file)
    jp_data = load_json_file(jp_file)
    if not all([cn_data, jp_data]):
        print(f"特殊文件 {file_name} 加载失败，跳过处理。")
        return

    old_value_counter = defaultdict(int)
    for item in cn_data:
        # 保持 VoiceId 的原始数据类型
        voice_id = item.get("VoiceId", 0)
        key = (
            item.get("ScriptKr", ""),
            item.get("TextJp", ""),
            voice_id
        )
        old_value_counter[key] += 1

    voice_mappings = []
    no_voice_mappings = []
    current_counts = defaultdict(int)

    for index in range(min(len(cn_data), len(jp_data))):
        cn_item = cn_data[index]
        jp_item = jp_data[index]

        # 保持 VoiceId 的原始数据类型
        jp_voice_id = jp_item.get("VoiceId", 0)
        old_key = (
            jp_item.get("ScriptKr", ""),
            jp_item.get("TextJp", ""),
            jp_voice_id
        )
        total_occurrences = old_value_counter[old_key]

        current_counts[old_key] += 1
        target_index = current_counts[old_key] - 1

        new_scriptkr = cn_item.get("ScriptKr", "")
        new_textjp = cn_item.get("TextJp", "")
        new_voiceid = cn_item.get("VoiceId", 0)  # 保持原始数据类型

        if old_key[0] == new_scriptkr and old_key[1] == new_textjp:
            continue

        # 根据国服 VoiceId 的值决定处理类型
        # 如果 VoiceId 为空字符串、0 或 None，则使用第二类型（不包含 VoiceId）
        if new_voiceid in ("", 0, None):
            no_voice_mapping = {
                "old": [old_key[0], old_key[1]],
                "new": [new_scriptkr, new_textjp],
                "target_index": target_index,
                "replacement_count": 1
            }
            no_voice_mappings.append(no_voice_mapping)
        else:
            # VoiceId 不为空，使用第一类型（包含 VoiceId）
            mapping = {
                "old": [old_key[0], old_key[1], old_key[2]],
                "new": [new_scriptkr, new_textjp, new_voiceid],
                "target_index": target_index,
                "replacement_count": 1
            }
            voice_mappings.append(mapping)

    output = []
    if voice_mappings:
        output.append({"fields": ["ScriptKr", "TextJp", "VoiceId"], "mappings": voice_mappings})
    if no_voice_mappings:
        output.append({"fields": ["ScriptKr", "TextJp"], "mappings": no_voice_mappings})

    if not output:
        print(f"警告: {file_name} 无有效特殊映射，跳过输出")
        return

    output_file = os.path.join(output_dir, file_name)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"特殊文件处理完成，写入: {output_file}")

def process_normal_pair(jp_file, cn_file, output_dir):
    file_name = os.path.basename(jp_file)
    print(f"\n正在处理文件: {file_name}")

    cn_data = load_json_file(cn_file)
    jp_data = load_json_file(jp_file)
    
    if not all([cn_data, jp_data]):
        print(f"文件 {file_name} 加载失败，跳过处理。")
        return

    if len(cn_data) == 0:
        print(f"警告: {file_name} 中没有数据，跳过处理")
        return

    if file_name != "ScenarioScriptExcel.json":
        if len(cn_data) > 0:
            fields = list(cn_data[0].keys())[1:]
        else:
            print(f"警告: {file_name} 中没有数据，跳过处理")
            return

        print(f"字段列表: {fields}")

        old_value_counter = defaultdict(int)
        for item in cn_data:
            for field in fields:
                key = item.get(field, "")
                old_value_counter[key] += 1

        output = []

        for field in fields:
            mappings = []
            current_counts = defaultdict(int)

            for index in range(min(len(cn_data), len(jp_data))):
                cn_item = cn_data[index]
                jp_item = jp_data[index]

                old_key = cn_item.get(field, "")
                total_occurrences = old_value_counter[old_key]

                current_counts[old_key] += 1

                target_index = current_counts[old_key] - 1

                old_value = jp_item.get(field, "")
                new_value = cn_item.get(field, "")
                if not old_value and not new_value:
                    continue

                mapping = {
                    "old": [old_value],
                    "new": [new_value],
                    "target_index": target_index,
                    "replacement_count": 1
                }
                mappings.append(mapping)

            if mappings:
                output.append({
                    "fields": [field],
                    "mappings": mappings
                })

        if not output:
            print(f"警告: {file_name} 无有效映射，跳过输出")
            return

        output_file = os.path.join(output_dir, file_name)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"文件处理完成，写入: {output_file}")
    else:
        print(f"跳过特殊文件: {file_name}")
        return

file_pairs = []
for jp_file in db_schema_jp_files:
    jp_name = os.path.basename(jp_file)
    cn_file = next((f for f in db_schema_cn_files if os.path.basename(f) == jp_name), None)
    if cn_file:
        file_pairs.append((jp_file, cn_file))

for jp_file in excel_table_jp_files:
    jp_name = os.path.basename(jp_file)
    cn_file = next((f for f in excel_table_cn_files if os.path.basename(f) == jp_name), None)
    if cn_file:
        file_pairs.append((jp_file, cn_file))

for jp_file, cn_file in file_pairs:
    if os.path.dirname(jp_file).endswith("DBSchema"):
        output_dir = excel_db_dir
    elif os.path.dirname(jp_file).endswith("ExcelTable"):
        output_dir = excel_dir
    else:
        output_dir = excel_dir

    file_name = os.path.basename(jp_file)
    if is_special_file(file_name):
        process_special_pair(jp_file, cn_file, output_dir)
    else:
        process_normal_pair(jp_file, cn_file, output_dir)

print("\n所有文件处理完成！")
