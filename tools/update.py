import zipfile
import json
import os
import tempfile
import shutil
import argparse

def replace_jsons(jp_data, global_data):
    id_key = list(global_data[0].keys())[0]
    
    global_dict = {}
    for item in global_data:
        id_value = item[id_key]
        if id_value not in global_dict:
            global_dict[id_value] = []
        global_dict[id_value].append(item)
    
    for item in jp_data:
        id_value = item[id_key]
        if id_value in global_dict and global_dict[id_value]:
            replacement_item = global_dict[id_value].pop(0)
            for key, value in replacement_item.items():
                if key != id_key:
                    item[key] = value
    
    return jp_data

def process_zip_files(zip1_path, zip2_path, output_zip_path):
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()
    
    try:
        with zipfile.ZipFile(zip1_path, 'r') as zip1:
            zip1.extractall(temp_dir1)
        
        with zipfile.ZipFile(zip2_path, 'r') as zip2:
            zip2.extractall(temp_dir2)
        
        target_folders = ['DBSchema', 'ExcelTable']
        
        for folder in target_folders:
            folder_path1 = os.path.join(temp_dir1, folder)
            folder_path2 = os.path.join(temp_dir2, folder)
            
            if os.path.exists(folder_path1) and os.path.exists(folder_path2):
                for root, dirs, files in os.walk(folder_path1):
                    for file in files:
                        if file.endswith('.json'):
                            file_path1 = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path1, folder_path1)
                            file_path2 = os.path.join(folder_path2, relative_path)
                            
                            with open(file_path1, 'r', encoding='utf-8') as f:
                                jp_data = json.load(f)
                            
                            if os.path.exists(file_path2):
                                with open(file_path2, 'r', encoding='utf-8') as f:
                                    global_data = json.load(f)
                                
                                replaced_data = replace_jsons(jp_data, global_data)
                                
                                with open(file_path1, 'w', encoding='utf-8') as f:
                                    json.dump(replaced_data, f, ensure_ascii=False, indent=4)
        
        with zipfile.ZipFile(output_zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output_zip:
            for folder in target_folders:
                folder_path = os.path.join(temp_dir1, folder)
                if os.path.exists(folder_path):
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir1)
                            output_zip.write(file_path, arcname)
        
        print(f"Processing completed. Result saved to {output_zip_path}")
    
    finally:
        shutil.rmtree(temp_dir1)
        shutil.rmtree(temp_dir2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process and merge JSON files from two ZIP archives containing DBSchema and ExcelTable folders.')
    parser.add_argument('zip1_path', help='Path to the first ZIP file (Japanese version)')
    parser.add_argument('zip2_path', help='Path to the second ZIP file (CN version)')
    parser.add_argument('output_zip_path', help='Path for the output ZIP file')
    
    args = parser.parse_args()
    process_zip_files(args.zip1_path, args.zip2_path, args.output_zip_path)
