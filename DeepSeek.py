import re
import json
import requests
import os
import time
from typing import List, Dict, Union

# 从环境变量中获取DeepSeek API密钥
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # DeepSeek API 地址

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

def read_config(file_path: str) -> Dict[str, List[str]]:
    """从配置文件中读取配置信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            config = json.load(file)
            return config.get("DBSchema", {}).get("日服", {})
    except FileNotFoundError:
        print(f"配置文件未找到：{file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"配置文件格式错误：{file_path}")
        return {}

def translate_with_deepseek(texts: List[str], terms: List[str], prompt: str, content: str, model: str = "deepseek-chat", max_retries: int = 3) -> List[str]:
    """发送翻译请求并严格保持原始格式
    
    Args:
        texts: 待翻译的文本列表
        terms: 术语表
        prompt: 从配置中读取的prompt，已包含术语表
        content: 从配置中读取的content
        model: 使用的模型
        max_retries: 最大重试次数
    
    Returns:
        翻译后的文本列表，保持与输入相同的顺序和数量
    """
    retries = 0
    while retries < max_retries:
        try:
            # 构建完整的消息内容
            messages = [
                {
                    "role": "system",
                    "content": content
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n待翻译内容（请保持原格式）：\n=====\n" + "\n=====\n".join(texts)
                }
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
                
                # 严格校对数量
                if len(translated_texts) == len(texts):
                    return translated_texts
                
                print(f"警告：返回结果数量不匹配（预期{len(texts)}，实际{len(translated_texts)}）")
                print(f"原始响应：{translated}")
                
            else:
                print(f"API请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常（{retries+1}/{max_retries}）：{str(e)}")
            time.sleep(5 * (retries + 1))  # 指数退避
            
        except Exception as e:
            print(f"处理异常（{retries+1}/{max_retries}）：{str(e)}")
            time.sleep(2)
            
        retries += 1
    
    print(f"翻译失败，已达最大重试次数。最后一批文本：{texts[:3]}...（共{len(texts)}条）")
    return []  # 返回空列表表示失败


def detect_and_translate_hiragana_katakana(input_dir: str, terms_path: str, output_dir: str, config_path: str, batch_size: int = 20) -> None:
    hiragana = '\u3040-\u309F'
    katakana = '\u30A0-\u30FF'
    japanese_pattern = f'[{hiragana}{katakana}]'
    
    try:
        # 读取配置文件
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 获取DeepSeek配置和DBSchema配置
        deepseek_config = config.get("DBSchema", {}).get("DeepSeek", {})
        schema_config = config.get("DBSchema", {}).get("日服", {})
        
        # 读取汉化表
        terms = read_terms(terms_path)
        
        # 遍历输入目录中的所有文件
        for file_name in os.listdir(input_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(input_dir, file_name)
                output_path = os.path.join(output_dir, file_name)
                
                # 获取该文件的DeepSeek配置
                file_deepseek_config = deepseek_config.get(file_name, {})
                prompt = file_deepseek_config.get("prompt", "")
                content = file_deepseek_config.get("content", "")
                
                # 如果prompt中包含占位符，则替换为名词表
                if "${name}" in prompt:
                    prompt = prompt.replace("${name}", "\n".join(terms))
                
                # 读取文件字段配置
                file_config = schema_config.get(file_name, [])
                jp_keys = [key for key in file_config if key.lower().endswith("jp")]
                
                if not jp_keys:
                    print(f"文件 {file_name} 中未找到以 'jp' 结尾的键")
                    continue
                
                # 读取原始数据
                with open(file_path, 'r', encoding='utf-8') as f:
                    data: List[Dict[str, Union[str, int]]] = json.load(f)
                
                # 按键名顺序处理
                all_translated = False
                while not all_translated:
                    all_translated = True
                    for key in jp_keys:
                        to_translate = []
                        indices = []
                        
                        for idx, item in enumerate(data):
                            text_jp = item.get(key, "")
                            cn_key = key.replace("Jp", "Cn").replace("jp", "cn").replace("JP", "CN")
                            if text_jp and re.search(japanese_pattern, text_jp) and cn_key not in item:
                                to_translate.append(text_jp)
                                indices.append((idx, key))
                        
                        if not to_translate:
                            print(f"文件 {file_name} 中未检测到需要翻译的 {key} 内容")
                            continue
                        
                        print(f"文件 {file_name} 中发现 {len(to_translate)} 处待翻译的 {key} 内容")
                        
                        # 分批处理
                        for batch_start in range(0, len(to_translate), batch_size):
                            batch_end = batch_start + batch_size
                            batch_texts = to_translate[batch_start:batch_end]
                            batch_indices = indices[batch_start:batch_end]
                            
                            print(f"正在翻译第 {batch_start//batch_size+1} 批（{len(batch_texts)} 条）...")
                            
                            # 使用从配置文件中读取的prompt和content
                            translated = translate_with_deepseek(
                                batch_texts, 
                                terms, 
                                prompt, 
                                content
                            )
                            
                            if translated and len(translated) == len(batch_texts):
                                # 按索引写回结果
                                for i, (original, translation) in enumerate(zip(batch_texts, translated)):
                                    idx, key = batch_indices[i]
                                    cn_key = key.replace("Jp", "Cn").replace("jp", "cn").replace("JP", "CN")
                                    data[idx][cn_key] = translation
                                
                                # 实时保存进度
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                with open(output_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                                
                                print(f"成功保存第 {batch_start//batch_size++1} 批翻译结果到 {output_path}")
                        else:
                            print(f"第 {batch_start//batch_size+1} 批翻译失败，已跳过")
                
    except Exception as e:
        print(f"处理过程中发生严重错误：{str(e)}")
        raise

if __name__ == "__main__":
    detect_and_translate_hiragana_katakana(
        input_dir="BA-Text/日服",
        terms_path="汉化名词.txt",
        output_dir="BA-Text/汉化后",
        config_path="配置.json",
        batch_size=50
    )
