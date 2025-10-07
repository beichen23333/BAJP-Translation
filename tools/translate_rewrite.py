import argparse
import json
import os
import re
from pathlib import Path

def find_corresponding_cn_key(jp_key):
    """根据JP键找到对应的CN键"""
    # 根据您提供的生成方式：jp_key.replace("Jp", "Cn").replace("jp", "cn").replace("JP", "CN")
    cn_key = jp_key
    if "Jp" in cn_key:
        cn_key = cn_key.replace("Jp", "Cn")
    elif "jp" in cn_key:
        cn_key = cn_key.replace("jp", "cn")
    elif "JP" in cn_key:
        cn_key = cn_key.replace("JP", "CN")
    return cn_key

def process_json_files(input_dir, output_dir):
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 遍历输入目录中的所有JSON文件
    input_path = Path(input_dir)
    json_files = input_path.glob("*.json")
    
    for json_file in json_files:
        print(f"处理文件: {json_file.name}")
        
        try:
            # 读取JSON文件
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理每个JSON对象
            processed_data = []
            for item in data:
                processed_item = item.copy()  # 创建副本
                
                # 首先找到所有的JP键
                jp_keys = [key for key in item.keys() if re.search(r'jp$', key, re.IGNORECASE)]
                
                for jp_key in jp_keys:
                    # 根据JP键找到对应的CN键
                    cn_key = find_corresponding_cn_key(jp_key)
                    
                    # 如果存在CN键，则将CN的值复制到JP
                    if cn_key in item:
                        processed_item[jp_key] = item[cn_key]
                        # 删除CN键
                        if cn_key in processed_item:
                            del processed_item[cn_key]
                
                # 添加到处理后的数据
                processed_data.append(processed_item)
            
            # 写入输出文件
            output_file = output_path / json_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            
            print(f"已处理并输出: {output_file}")
            
        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description="将JSON文件中的CN内容写回到JP字段并删除CN键")
    parser.add_argument("input_dir", help="输入目录路径")
    parser.add_argument("output_dir", help="输出目录路径")
    
    args = parser.parse_args()
    
    process_json_files(args.input_dir, args.output_dir)
    print("处理完成！")

if __name__ == "__main__":
    main()
