import re
import json
import requests
import os
import time
from typing import List, Dict, Union, Tuple, Optional
import argparse
import concurrent.futures

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def read_terms(file_path: str) -> List[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"文件未找到：{file_path}")
        return []
    except Exception as e:
        print(f"读名词表出错：{str(e)}")
        return []

def read_config(file_path: str) -> Dict[str, Dict[str, List[str]]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"配置文件未找到：{file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"配置文件格式错误：{file_path}")
        return {}
    except Exception as e:
        print(f"读取配置文件出错：{str(e)}")
        return {}

def get_cn_key(jp_key: str) -> str:
    return jp_key.replace("Jp", "Cn").replace("jp", "cn").replace("JP", "CN")

def get_re_key(jp_key: str) -> str:
    return jp_key.replace("Jp", "Re").replace("jp", "re").replace("JP", "RE")

def get_tr_key(kr_key: str) -> str:
    return kr_key.replace("Kr", "Tr").replace("kr", "tr").replace("KR", "TR")

def translate_with_deepseek(texts: List[str], terms: List[str], prompt: str, content: str, model: str = "deepseek-chat", max_retries: int = 3) -> Optional[List[str]]:
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            messages = [
                {"role": "system", "content": content},
                {"role": "user", "content": f"{prompt}\n仅进行直译，不要进行润色处理，确保标点符号正确，待翻译内容（请保持原格式）：\n=====\n" + "\n=====\n".join(texts)}
            ]
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "top_p": 0.9,
                "frequency_penalty": 0,
                "presence_penalty": 0
            }
            
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                translated = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                translated_texts = [t.strip() for t in translated.split("=====") if t.strip()]
                if len(translated_texts) == len(texts):
                    return translated_texts
                error_msg = f"返回结果数量不匹配（预期{len(texts)}，实际{len(translated_texts)}）"
                print(f"警告：{error_msg}")
                last_error = error_msg
            else:
                error_msg = f"API请求失败，状态码：{response.status_code}"
                last_error = error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常（{retries+1}/{max_retries}）：{str(e)}"
            last_error = error_msg
            time.sleep(5 * (retries + 1))
        except Exception as e:
            error_msg = f"处理异常（{retries+1}/{max_retries}）：{str(e)}"
            last_error = error_msg
            time.sleep(2)
        retries += 1
    print(f"翻译失败，已达最大重试次数。最后错误：{last_error}")
    return None

def process_translation_batch(
    data: List[Dict], 
    batch_texts: List[str], 
    batch_indices: List[Tuple[int, str]], 
    translated_texts: List[str],
    translation_type: str = "Cn"
) -> bool:
    if len(translated_texts) != len(batch_texts):
        print(f"错误：翻译结果数量不匹配（预期{len(batch_texts)}，实际{len(translated_texts)}），本批次跳过")
        return False
    
    try:
        for i, (original, translation) in enumerate(zip(batch_texts, translated_texts)):
            idx, key = batch_indices[i]
            if translation_type == "Cn":
                target_key = get_cn_key(key)
            elif translation_type == "Re":
                target_key = get_re_key(key)
            elif translation_type == "Tr":
                target_key = get_tr_key(key)
            data[idx][target_key] = translation
        return True
    except Exception as e:
        print(f"更新数据时出错：{str(e)}")
        return False

def find_texts_to_translate(data: List[Dict[str, Union[str, int]]], jp_keys: List[str], kr_keys: List[str], file_name: str) -> Tuple[List[Dict], List[Tuple[int, str, str]]]:
    """
    返回格式: (待翻译文本列表, 索引信息列表)
    每个待翻译文本是字典: {"text": 文本, "type": "jp" 或 "kr"}
    索引信息是元组: (数据索引, 字段键, 文本类型)
    """
    to_translate = []
    indices = []

    for idx, item in enumerate(data):
        # 处理日文键（翻译为Cn和Re）
        for key in jp_keys:
            text_jp = item.get(key, "")
            cn_key = get_cn_key(key)
            re_key = get_re_key(key)

            # 只有当原文存在且目标字段为空时才翻译
            if text_jp and not item.get(cn_key) and not item.get(re_key):
                to_translate.append({"text": text_jp, "type": "jp"})
                indices.append((idx, key, "jp"))
        
        # 处理韩文键（仅对ScenarioScriptExcel.json，翻译为Tr）
        if file_name == "ScenarioScriptExcel.json":
            for key in kr_keys:
                text_kr = item.get(key, "")
                tr_key = get_tr_key(key)

                # 只有当原文存在且目标字段为空时才翻译
                if text_kr and not item.get(tr_key):
                    to_translate.append({"text": text_kr, "type": "kr"})
                    indices.append((idx, key, "kr"))

    return to_translate, indices

def process_file(file_name: str, input_dir: str, output_dir: str, terms: List[str], deepseek_config: Dict, schema_config: Dict, batch_size: int, max_workers: int):
    try:
        file_path = os.path.join(input_dir, file_name)
        output_path = os.path.join(output_dir, file_name)

        file_deepseek_config = deepseek_config.get(file_name, {})
        prompt = file_deepseek_config.get("prompt", "")
        content = file_deepseek_config.get("content", "")

        if "${name}" in prompt:
            prompt = prompt.replace("${name}", "\n".join(terms))

        file_config = schema_config.get(file_name, [])
        jp_keys = [key for key in file_config if key.lower().endswith("jp")]
        kr_keys = [key for key in file_config if key.lower().endswith("kr")]

        if not jp_keys and not kr_keys:
            print(f"文件 {file_name} 中未找到以 'jp' 或 'kr' 结尾的键")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        to_translate, indices = find_texts_to_translate(data, jp_keys, kr_keys, file_name)
        if not to_translate:
            print(f"文件 {file_name} 中未检测到需要翻译的内容")
            return

        print(f"文件 {file_name} 中发现 {len(to_translate)} 处待翻译内容，启动线程池处理...")

        def translate_batch(batch_start):
            batch_end = batch_start + batch_size
            batch_items = to_translate[batch_start:batch_end]
            batch_indices = indices[batch_start:batch_end]
            
            # 分离日文和韩文文本
            jp_texts = []
            kr_texts = []
            jp_indices = []
            kr_indices = []
            
            for i, (item, (idx, key, text_type)) in enumerate(zip(batch_items, batch_indices)):
                if text_type == "jp":
                    jp_texts.append(item["text"])
                    jp_indices.append((idx, key))
                elif text_type == "kr":
                    kr_texts.append(item["text"])
                    kr_indices.append((idx, key))
            
            # 处理日文翻译（Cn和Re）
            if jp_texts:
                translated_cn = translate_with_deepseek(jp_texts, terms, prompt + " (日译中)", content)
                translated_re = translate_with_deepseek(jp_texts, terms, prompt + " (日译中)", content)
                
                if translated_cn:
                    process_translation_batch(data, jp_texts, jp_indices, translated_cn, "Cn")
                if translated_re:
                    process_translation_batch(data, jp_texts, jp_indices, translated_re, "Re")
            
            # 处理韩文翻译（Tr，仅对ScenarioScriptExcel.json）
            if kr_texts and file_name == "ScenarioScriptExcel.json":
                translated_tr = translate_with_deepseek(kr_texts, terms, prompt + " (韩译中)", content)
                if translated_tr:
                    process_translation_batch(data, kr_texts, kr_indices, translated_tr, "Tr")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(translate_batch, range(0, len(to_translate), batch_size)))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"文件 {file_name} 翻译完成并保存至 {output_path}")

    except Exception as e:
        print(f"处理文件 {file_name} 时出错：{str(e)}")

def detect_and_translate_hiragana_katakana(input_dir: str, terms_path: str, output_dir: str, config_path: str, batch_size: int = 20, max_workers: int = 5) -> None:
    try:
        config = read_config(config_path)
        if not config:
            raise ValueError("无效的配置文件")

        deepseek_config = config.get("DeepSeek", {})
        schema_config = {**config.get("DBSchema", {}), **config.get("ExcelTable", {})}
        terms = read_terms(terms_path)

        db_schema_output = os.path.join(output_dir, "DBSchema")
        excel_table_output = os.path.join(output_dir, "ExcelTable")
        os.makedirs(db_schema_output, exist_ok=True)
        os.makedirs(excel_table_output, exist_ok=True)

        db_schema_input = os.path.join(input_dir, "DBSchema")
        db_schema_files = []
        if os.path.exists(db_schema_input):
            db_schema_files = [f for f in os.listdir(db_schema_input) 
                             if f.endswith(".json") and f in schema_config]

        excel_table_input = os.path.join(input_dir, "ExcelTable")
        excel_table_files = []
        if os.path.exists(excel_table_input):
            excel_table_files = [f for f in os.listdir(excel_table_input) 
                               if f.endswith(".json") and f in schema_config]

        all_files = []
        for file in db_schema_files:
            all_files.append(("DBSchema", file, db_schema_input, db_schema_output))
        for file in excel_table_files:
            all_files.append(("ExcelTable", file, excel_table_input, excel_table_output))

        if not all_files:
            print("未找到任何需要处理的 JSON 文件")
            return

        print(f"检测到 {len(all_files)} 个文件，启动处理...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for folder_type, file_name, input_dir_path, output_dir_path in all_files:
                future = executor.submit(
                    process_file,
                    file_name, input_dir_path, output_dir_path, terms, 
                    deepseek_config, schema_config, batch_size, max_workers
                )
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"处理文件时出错：{str(e)}")

    except Exception as e:
        print(f"处理过程中发生严重错误：{str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="翻译工具")
    parser.add_argument("input_dir", help="输入目录路径")
    parser.add_argument("terms_path", help="术语表文件路径")
    parser.add_argument("output_dir", help="输出目录路径")
    parser.add_argument("config_path", help="配置文件路径")
    parser.add_argument("batch_size", type=int, help="批处理大小")
    parser.add_argument("max_workers", type=int, help="最大工作线程数")
    args = parser.parse_args()

    detect_and_translate_hiragana_katakana(
        input_dir=args.input_dir,
        terms_path=args.terms_path,
        output_dir=args.output_dir,
        config_path=args.config_path,
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )
