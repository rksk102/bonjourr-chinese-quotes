import csv
import os
import sys
import random
import json
import time
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime

TARGET_COUNT = 100
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 2
REQUEST_TIMEOUT = 10

API_SOURCES = [
    {
        "name": "Hitokoto 国际版",
        "url": "https://international.v1.hitokoto.cn/",
        "params": {
            "c": ["i", "l", "k"],
            "encode": "json",
            "min_length": 5,
            "max_length": 25
        },
        "parser": lambda data: {
            "text": data.get("hitokoto", "").strip(),
            "author": data.get("from", "佚名").strip()
        }
    },
    {
        "name": "今日诗词",
        "url": "https://v2.jinrishici.com/one.json",
        "params": {},
        "parser": lambda data: {
            "text": data.get("data", {}).get("content", "").strip(),
            "author": data.get("data", {}).get("origin", {}).get("author", "佚名").strip()
        }
    },
    {
        "name": "一言旧版",
        "url": "https://hitokoto.cn/api.php",
        "params": {
            "c": "i",
            "encode": "json"
        },
        "parser": lambda data: {
            "text": data.get("hitokoto", "").strip(),
            "author": data.get("from", "佚名").strip()
        }
    }
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def log(message, type='info'):
    timestamp = datetime.now().strftime("%H:%M:%S")
    if type == 'error':
        print(f"::error::{message}")
    elif type == 'warning':
        print(f"::warning::{message}")
    else:
        print(f"[{timestamp}] {message}")

def fetch_one_quote(source_index=0):
    """
    从指定索引的 API 源获取一条语录，失败则尝试下一个源
    """
    for i in range(source_index, len(API_SOURCES)):
        source = API_SOURCES[i]
        try:
            params_str = "&".join([f"{k}={v}" for k, v in source["params"].items()])
            url = f"{source['url']}?{params_str}" if params_str else source['url']
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))
                parsed = source["parser"](data)
                text = parsed.get("text", "")
                author = parsed.get("author", "佚名")
                
                if text:
                    return {'text': text, 'author': author}
        except Exception as e:
            pass
    return None

def fetch_quotes_concurrent(count):
    quotes = []
    seen = set()
    consecutive_failures = 0
    MAX_FAILURES = 30
    
    log(f"🚀 启动 {MAX_WORKERS} 线程获取 {count} 条语录...", 'info')
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(quotes) < count:
            needed = count - len(quotes)
            batch_size = min(needed, MAX_WORKERS * 2)
            source_index = random.randint(0, len(API_SOURCES) - 1)
            futures = [executor.submit(fetch_one_quote, source_index) for _ in range(batch_size)]
            
            round_success = 0
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    unique_key = f"{result['text']}-{result['author']}"
                    if unique_key not in seen:
                        seen.add(unique_key)
                        quotes.append(result)
                        round_success += 1
                        sys.stdout.write(f"\r   进度: {len(quotes)}/{count}")
                        sys.stdout.flush()
            
            if round_success == 0:
                consecutive_failures += 1
                log(f"⚠️ 第 {consecutive_failures} 次尝试未获取到数据，切换 API 源...", 'warning')
            else:
                consecutive_failures = 0
            
            if consecutive_failures >= MAX_FAILURES:
                log(f"❌ 连续 {MAX_FAILURES} 次获取失败，所有 API 源可能都不可用。任务终止。", 'error')
                break
    
    elapsed = time.time() - start_time
    print() 
    log(f"✅ 结束。获取 {len(quotes)} 条，耗时: {elapsed:.2f} 秒", 'info')
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
        f.write("# ⚡ 多源网络抓取报告\n\n")
        f.write(f"**⏱️ 耗时**: {time.time() - start_time:.2f} 秒\n\n")
        f.write(f"**📊 数量**: `{len(quotes)}` 条 \n\n")
        f.write(f"**🌐 来源**: 多源轮询 (Hitokoto 国际版、今日诗词等) \n\n")
        
        if len(quotes) > 0:
            f.write("### 🎲 预览\n")
            f.write("| 内容 | 出处 |\n")
            f.write("| :--- | :--- |\n")
            for q in random.sample(quotes, min(5, len(quotes))):
                safe_text = q['text'].replace('|', '\\|')
                safe_author = q['author'].replace('|', '\\|')
                f.write(f"| {safe_text} | {safe_author} |\n")
        else:
            f.write("⚠️ 未获取到数据。")

if __name__ == "__main__":
    start_time = time.time()
    
    try:
        data = fetch_quotes_concurrent(TARGET_COUNT)
        
        if len(data) > 0:
            if save_csv(data):
                generate_summary(data)
                log("🎉 任务完成！", 'info')
            else:
                sys.exit(1)
        else:
            log("⚠️ 没有获取到任何数据，跳过保存。", 'warning')
            sys.exit(1)
            
    except Exception as e:
        log(f"端到端错误: {e}", 'error')
        sys.exit(1)
