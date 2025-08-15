import re
import json
import requests
import os
import time
from typing import List, Dict, Union, Tuple, Optional

# 从环境变量中获取DeepSeek API密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 初始化请求头
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def read_terms(file_path: str) -> List[str]:
    """从文件中读取名词和人名"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"文件未找到：{file_path}")
        return []
    except Exception as e:
        print(f"读取术语表出错：{str(e)}")
        return []

def read_config(file_path: str) -> Dict[str, Dict[str, List[str]]]:
    """从配置文件中读取配置信息"""
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

def translate_with_deepseek(
    texts: List[str], 
    terms: List[str], 
    prompt: str, 
    content: str, 
    model: str = "deepseek-chat", 
    max_retries: int = 3
) -> Optional[List[str]]:
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # 构建完整的消息内容
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
                
                # 按原始分隔符拆分结果
                translated_texts = [t.strip() for t in translated.split("=====") if t.strip()]
                
                # 校对数量
                if len(translated_texts) == len(texts):
                    return translated_texts
                
                # 数量不匹配时的处理
                error_msg = f"返回结果数量不匹配（预期{len(texts)}，实际{len(translated_texts)}）"
                print(f"警告：{error_msg}")
                
                # 尝试对齐结果
                if len(translated_texts) == len(texts) - 1:
                    last_part = translated.rsplit("=====", 1)[-1].strip()
                    if last_part:
                        translated_texts.append(last_part)
                        if len(translated_texts) == len(texts):
                            print("通过合并最后一个分隔符修复了数量不匹配问题")
                            return translated_texts
                
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

def find_texts_to_translate(
    data: List[Dict[str, Union[str, int]]],
    jp_keys: List[str]
) -> Tuple[List[str], List[Tuple[int, str]]]:
    to_translate = []
    indices = []

    for idx, item in enumerate(data):
        for key in jp_keys:
            cn_key = get_cn_key(key)
            text_jp = item.get(key, "")

            # 只判断 JP 字段有内容且没有 CN 字段即可
            if text_jp and cn_key not in item:
                to_translate.append(text_jp)
                indices.append((idx, key))

    return to_translate, indices

def process_translation_batch(
    data: List[Dict], 
    batch_texts: List[str], 
    batch_indices: List[Tuple[int, str]], 
    translated_texts: List[str]
) -> bool:
    if len(translated_texts) != len(batch_texts):
        print(f"错误：翻译结果数量不匹配（预期{len(batch_texts)}，实际{len(translated_texts)}），本批次跳过")
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

def detect_and_translate_hiragana_katakana(
    input_dir: str, 
    terms_path: str, 
    output_dir: str, 
    config_path: str, 
    batch_size: int = 20
) -> None:
    try:
        config = read_config(config_path)
        if not config:
            raise ValueError("无效的配置文件")

        deepseek_config = config.get("DBSchema", {}).get("DeepSeek", {})
        schema_config = config.get("DBSchema", {}).get("日服", {})
        terms = read_terms(terms_path)
        
        for file_name in os.listdir(input_dir):
            if not file_name.endswith(".json"):
                continue
                
            file_path = os.path.join(input_dir, file_name)
            output_path = os.path.join(output_dir, file_name)
            
            file_deepseek_config = deepseek_config.get(file_name, {})
            prompt = file_deepseek_config.get("prompt", "")
            content = file_deepseek_config.get("content", "")
            
            # 替换占位符
            if "${name}" in prompt:
                prompt = prompt.replace("${name}", "\n".join(terms))
            
            # 读取文件字段配置
            file_config = schema_config.get(file_name, [])
            jp_keys = [key for key in file_config if key.lower().endswith("jp")]
            
            if not jp_keys:
                print(f"文件 {file_name} 中未找到以 'jp' 结尾的键")
                continue
            
            # 读取原始数据
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data: List[Dict[str, Union[str, int]]] = json.load(f)
            except Exception as e:
                print(f"读取文件 {file_name} 出错：{str(e)}")
                continue
            
            # 找出所有需要翻译的文本
            to_translate, indices = find_texts_to_translate(data, jp_keys)
            
            if not to_translate:
                print(f"文件 {file_name} 中未检测到需要翻译的内容")
                continue
            
            print(f"文件 {file_name} 中发现 {len(to_translate)} 处待翻译内容")
            
            # 分批处理
            for batch_start in range(0, len(to_translate), batch_size):
                batch_end = batch_start + batch_size
                batch_texts = to_translate[batch_start:batch_end]
                batch_indices = indices[batch_start:batch_end]
                
                print(f"正在翻译第 {batch_start//batch_size+1} 批（{len(batch_texts)} 条）...")
                
                translated = translate_with_deepseek(batch_texts, terms, prompt, content)
                
                if translated is None:
                    print(f"第 {batch_start//batch_size+1} 批翻译失败，已跳过")
                    continue
                
                if process_translation_batch(data, batch_texts, batch_indices, translated):
                    # 实时保存进度
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        print(f"成功保存第 {batch_start//batch_size+1} 批翻译结果到 {output_path}")
                    except Exception as e:
                        print(f"保存文件 {file_name} 出错：{str(e)}")
                else:
                    print(f"第 {batch_start//batch_size+1} 批处理失败，已跳过")
                    
    except Exception as e:
        print(f"处理过程中发生严重错误：{str(e)}")
        raise

if __name__ == "__main__":
    detect_and_translate_hiragana_katakana(
        input_dir="BA-Text/日服",
        terms_path="汉化名词.txt",
        output_dir="BA-Text/DeepSeek",
        config_path="配置.json",
        batch_size=50
    )
