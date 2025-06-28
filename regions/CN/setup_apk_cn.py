from utils.util import ZipUtils
from os import path
import glob
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from lib.downloader import FileDownloader
from lib.console import ProgressBar, notice

TEMP_DIR = "Temp"  # 临时文件目录
CHUNK_SIZE = 1024 * 1024  # 每个分块大小为1MB
THREADS = 8  # 下载线程数

def extract_apk_file(apk_path: str) -> None:
    """解压APK文件到指定目录"""
    ZipUtils.extract_zip(apk_path, path.join(TEMP_DIR, "Data"))

def get_apk_url() -> str:
    """从官网获取APK下载链接"""
    print("正在从官网获取APK下载链接...")
    response = FileDownloader("https://bluearchive-cn.com/").get_response()
    
    # 查找JavaScript文件链接
    js_match = re.search(r'<script[^>]+type="module"[^>]+crossorigin[^>]+src="([^"]+)"[^>]*>', response.text)
    if not js_match:
        raise LookupError("错误: 无法找到JavaScript文件链接")

    js_url = js_match.group(1)
    print(f"找到JavaScript文件: {js_url}")
    
    # 从JavaScript文件中查找APK链接
    js_response = FileDownloader(js_url).get_response()
    apk_match = re.search(r'http[s]?://[^\s"<>]+?\.apk', js_response.text)
    if not apk_match:
        raise LookupError("错误: 无法找到APK下载链接")

    apk_url = apk_match.group()
    print(f"[成功] 找到APK下载链接: {apk_url}")
    return apk_url

def download_chunk(url, start, end, part_num, temp_dir):
    """下载文件的一个分块"""
    print(f"[下载] 开始下载分块 {part_num} (字节范围: {start}-{end})")
    headers = {'Range': f'bytes={start}-{end}'}
    response = requests.get(url, headers=headers, stream=True)
    chunk_path = path.join(temp_dir, f"part_{part_num}")
    
    with open(chunk_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
    
    print(f"[完成] 分块 {part_num} 下载完成")
    return part_num

def merge_chunks(temp_dir, output_path, total_size):
    """合并所有下载的分块"""
    print("开始合并下载的分块文件...")
    with open(output_path, 'wb') as outfile:
        for part_num in range(THREADS):
            chunk_path = path.join(temp_dir, f"part_{part_num}")
            print(f"[合并] 正在合并分块 {part_num}...")
            with open(chunk_path, 'rb') as infile:
                outfile.write(infile.read())
            os.remove(chunk_path)
    print(f"[成功] 所有分块已合并到: {output_path}")

def download_apk_multithreaded(apk_url: str) -> str:
    """多线程下载APK文件"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    print("开始多线程下载APK文件...")
    
    # 获取文件总大小
    print("正在获取APK文件大小...")
    response = requests.head(apk_url)
    total_size = int(response.headers.get('Content-Length', 0))
    print(f"APK文件大小: {total_size/1024/1024:.2f}MB")
    
    # 创建临时目录用于存储分块
    temp_dir = path.join(TEMP_DIR, "chunks")
    os.makedirs(temp_dir, exist_ok=True)
    print(f"临时分块目录: {temp_dir}")
    
    # 计算每个线程的下载范围
    chunk_size = total_size // THREADS
    ranges = [(i * chunk_size, (i + 1) * chunk_size - 1) for i in range(THREADS - 1)]
    ranges.append(((THREADS - 1) * chunk_size, total_size - 1))
    print(f"分块范围计算完成，使用 {THREADS} 个线程下载")
    
    # 使用线程池并行下载
    print("启动多线程下载...")
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []
        for i, (start, end) in enumerate(ranges):
            futures.append(executor.submit(
                download_chunk, apk_url, start, end, i, temp_dir
            ))
        
        # 等待所有线程完成
        for future in futures:
            future.result()
    
    # 合并分块
    apk_filename = "com.RoamingStar.BlueArchive.bilibili.apk"
    apk_path = path.join(TEMP_DIR, apk_filename)
    
    # 检查文件是否已存在且完整
    if path.exists(apk_path) and path.getsize(apk_path) == total_size:
        print("APK文件已存在且完整，跳过下载")
        return apk_path.replace("\\", "/")
    
    merge_chunks(temp_dir, apk_path, total_size)
    
    # 清理临时目录
    os.rmdir(temp_dir)
    print("[成功] APK文件下载完成")
    return apk_path.replace("\\", "/")
