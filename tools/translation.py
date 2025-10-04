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

def contains_hiragana_or_katakana(text: str) -> bool:
    return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text))

def is_ruby_format(text: str) -> bool:
    return bool(re.search(r'\[ruby=[^\]]+\].*?\[/ruby\]', text))

def needs_retranslation(text: str) -> bool:
    return contains_hiragana_or_katakana(text) and not is_ruby_format(text)

def translate_with_deepseek(texts: List[str], terms: List[str], prompt: str, content: str, model: str = "deepseek-chat", max_retries: int = 3) -> Optional[List[str]]:
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            messages = [
                {"role": "system", "content": content},
                {"role": "user", "content": f"{prompt}\n=====\n" + "\n=====\n".join(texts)}
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
                print(f"{error_msg}")
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
    translated_texts: List[str]
) -> bool:
    if len(translated_texts) != len(batch_texts):
        print(f"翻译结果数量不匹配（预期{len(batch_texts)}，实际{len(translated_texts)}），本批次跳过")
        return False
    
    try:
        for i, (original, translation) in enumerate(zip(batch_texts, translated_texts)):
            idx, key = batch_indices[i]
            cn_key = get_cn_key(key)
            data[idx][cn_key] = translation
        return True
    except Exception as e:
        print(f"更新数据时出错：{str(e)}")
        return False

def find_texts_to_translate(data: List[Dict[str, Union[str, int]]], jp_keys: List[str]) -> Tuple[List[str], List[Tuple[int, str]]]:
    to_translate = []
    indices = []

    for idx, item in enumerate(data):
        for key in jp_keys:
            cn_key = get_cn_key(key)
            text_jp = item.get(key, "")
            text_cn = item.get(cn_key, "")

            if text_jp and cn_key not in item:
                to_translate.append(text_jp)
                indices.append((idx, key))
            elif text_cn and needs_retranslation(text_cn):
                to_translate.append(text_jp)
                indices.append((idx, key))

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

        if not jp_keys:
            print(f"文件 {file_name} 中未找到以 'jp' 结尾的键")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        to_translate, indices = find_texts_to_translate(data, jp_keys)
        if not to_translate:
            print(f"文件 {file_name} 中未检测到需要翻译的内容")
            return

        print(f"文件 {file_name} 中发现 {len(to_translate)} 处待翻译内容，启动线程池处理...")

        def translate_batch(batch_start):
            batch_end = batch_start + batch_size
            batch_texts = to_translate[batch_start:batch_end]
            batch_indices = indices[batch_start:batch_end]

            translated = translate_with_deepseek(batch_texts, terms, prompt, content)
            if translated is None:
                print(f"文件 {file_name} 第 {batch_start//batch_size+1} 批翻译失败")
                return

            process_translation_batch(data, batch_texts, batch_indices, translated)

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

        deepseek_config = config.get("DBSchema", {}).get("DeepSeek", {})
        schema_config = config.get("DBSchema", {}).get("日服", {})
        terms = read_terms(terms_path)

        json_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
        if not json_files:
            print("未找到任何 JSON 文件")
            return

        print(f"检测到 {len(json_files)} 个文件，启动多线程处理...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(
                lambda file: process_file(
                    file, input_dir, output_dir, terms, deepseek_config, schema_config, batch_size, max_workers
                ),
                json_files
            )

    except Exception as e:
        print(f"处理过程中发生严重错误：{str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True, help="输入 JSON 文件目录")
    parser.add_argument("--terms_path", required=True, help="汉化名词文件路径")
    parser.add_argument("--output_dir", required=True, help="输出目录")
    parser.add_argument("--config_path", required=True, help="配置文件路径")
    parser.add_argument("--batch_size", type=int, default=50, help="单次翻译数量")
    parser.add_argument("--max_workers", type=int, default=5, help="线程数量")
    args = parser.parse_args()

    detect_and_translate_hiragana_katakana(
        input_dir=args.input_dir,
        terms_path=args.terms_path,
        output_dir=args.output_dir,
        config_path=args.config_path,
        batch_size=args.batch_size
    )