import csv
import os
import sys
import random
import json
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime

TARGET_COUNT = 100
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 15 
API_URL = "https://v1.hitokoto.cn/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def log(message, type='info'):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    if type == 'error':
        print(f"::error file={__file__},line={sys._getframe(1).f_lineno}::{message}")
    elif type == 'warning':
        print(f"::warning::{message}")
    else:
        print(f"[{timestamp}] {message}")

def fetch_one_quote():
    """
    单次请求逻辑（无 sleep，依赖网络延迟）
    """
    params = {
        'c': ['i', 'l', 'k'],
        'encode': 'json',
        'min_length': 5,
        'max_length': 25
    }
    full_url = f"{API_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    req = urllib.request.Request(full_url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            text = data.get('hitokoto', '').strip()
            author = data.get('from', '佚名').strip()
            
            if text:
                return {'text': text, 'author': author}
    except Exception as e:
        pass
    return None
def fetch_quotes_concurrent(count):
    quotes = []
    seen = set()
    errors = 0
    
    log(f"🚀 启动 {MAX_WORKERS} 线程并发获取 {count} 条语录...", 'info')
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(quotes) < count:
            needed = count - len(quotes)
            batch_size = min(needed, MAX_WORKERS * 2) 
            
            futures = [executor.submit(fetch_one_quote) for _ in range(batch_size)]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    unique_key = f"{result['text']}-{result['author']}"
                    if unique_key not in seen:
                        seen.add(unique_key)
                        quotes.append(result)

                        sys.stdout.write(f"\r   进度: {len(quotes)}/{count}")
                        sys.stdout.flush()

                if len(quotes) >= count:
                    for f in futures:
                        f.cancel()
                    break

            if not quotes and errors > 50:
                log("连续错误过多，可能 API 不可用。", 'error')
                break
                
    elapsed = time.time() - start_time
    print()
    log(f"✅ 获取完成！耗时: {elapsed:.2f} 秒", 'info')
    return quotes

def save_csv(quotes):
    print("::group::💾 写入 CSV 文件")
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['text', 'author'])
            writer.writeheader()
            writer.writerows(quotes)
        print(f"文件已保存: {OUTPUT_FILE} ({len(quotes)} 条)")
        print("::endgroup::")
        return True
    except Exception as e:
        log(f"保存 CSV 失败: {e}", 'error')
        return False

def generate_summary(quotes):
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        return

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# ⚡ 极速更新报告\n\n")
        f.write(f"**⏱️ 耗时**: 极速并发模式 \n\n")
        f.write(f"**📊 数量**: `{len(quotes)}` 条 \n\n")
        
        f.write("### 🎲 预览\n")
        f.write("| 内容 | 出处 |\n")
        f.write("| :--- | :--- |\n")
        for q in random.sample(quotes, min(5, len(quotes))):
            safe_text = q['text'].replace('|', '\\|')
            safe_author = q['author'].replace('|', '\\|')
            f.write(f"| {safe_text} | {safe_author} |\n")

if __name__ == "__main__":
    try:
        data = fetch_quotes_concurrent(TARGET_COUNT)
        if save_csv(data):
            generate_summary(data)
            log("🎉 任务极速完成！", 'info')
        else:
            sys.exit(1)
    except Exception as e:
        log(f"严重错误: {e}", 'error')
        sys.exit(1)
