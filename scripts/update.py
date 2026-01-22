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

TARGET_COUNT = 15
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 3
REQUEST_TIMEOUT = 10
API_SOURCES = [
    {
        "name": "一言（官方）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": ["i", "l", "k"], "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（国际版）",
        "url": "https://international.v1.hitokoto.cn/",
        "params": {"c": ["i", "l", "k"], "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（CN镜像）",
        "url": "https://cn.hitokoto.cn/",
        "params": {"c": ["i", "l", "k"], "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（备用域名）",
        "url": "https://sentence-api.qpchan.com/",
        "params": {"c": ["i", "l", "k"], "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（PHP版）",
        "url": "https://hitokoto.cn/api.php",
        "params": {"c": "i", "encode": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言诗词",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "k", "encode": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言文学",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "l", "encode": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言文言",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "d", "encode": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "今日诗词",
        "url": "https://v2.jinrishici.com/one.json",
        "params": {},
        "parser": lambda data: {"text": data.get("data", {}).get("content", "").strip(), "author": data.get("data", {}).get("origin", {}).get("author", "佚名").strip()}
    },
    {
        "name": "古诗词API",
        "url": "https://api.gushi.ci/all.json",
        "params": {},
        "parser": lambda data: {"text": data[0].get("content", "").strip() if isinstance(data, list) and len(data) > 0 else "", "author": data[0].get("origin", {}).get("author", "佚名").strip() if isinstance(data, list) and len(data) > 0 else "佚名"}
    },
    {
        "name": "爱词建诗词",
        "url": "https://ciapi.xygeng.cn/one",
        "params": {},
        "parser": lambda data: {"text": data.get("content", "").strip(), "author": data.get("author", "").strip() if data.get("author") else "佚名"}
    },
    {
        "name": "随机句子",
        "url": "https://api.xygeng.cn/one",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": data.get("author", "佚名").strip()}
    },
    {
        "name": "句子迷API",
        "url": "https://api.juzimi.com/api/random",
        "params": {},
        "parser": lambda data: {"text": data.get("content", "").strip(), "author": data.get("author", "句子迷").strip()}
    },
    {
        "name": "一言代理",
        "url": "https://api.vvhan.com/api/一言",
        "params": {},
        "parser": lambda data: {"text": data.get("data", {}).get("hitokoto", "").strip(), "author": data.get("data", {}).get("from", "佚名").strip()}
    },
    {
        "name": "励志名言",
        "url": "https://api.oick.cn/dutang/api.php",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": data.get("author", "佚名").strip()}
    },
    {
        "name": "名人名言",
        "url": "https://api.oick.cn/mingyan/api.php",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": data.get("author", "佚名").strip()}
    },
    {
        "name": "心灵鸡汤",
        "url": "https://api.oick.cn/yulu/api.php",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": data.get("author", "佚名").strip()}
    },
    {
        "name": "文艺句子",
        "url": "https://api.oick.cn/wenyi/api.php",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": data.get("author", "佚名").strip()}
    },
    {
        "name": "随机情话",
        "url": "https://api.uomg.com/api/rand.qinghua",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip(), "author": "情话API"}
    },
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def log(message, type='info'):
    timestamp = datetime.当前().strftime("%H:%M:%S")
    if type == 'error':
        print(f"::error::{message}")
    elif type == 'warning':
        print(f"::warning::{message}")
    else:
        print(f"[{timestamp}] {message}")

def load_existing_quotes():
    """
    读取现有的 CSV 文件
    """
    existing_set = set()
    existing_rows = []
    if not os.path.exists(OUTPUT_FILE):
        log(f"📁 文件 {OUTPUT_FILE} 不存在，将创建新文件", 'info')
        return existing_set, existing_rows
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, fieldnames=['author', 'text'])
            for row in reader:
                text = row.get('text', '').strip()
                author = row.get('author', '').strip()
                if text == 'text' and author == 'author':
                    continue
                if text:
                    unique_key = f"{text}-{author}"
                    existing_set.add(unique_key)
                    existing_rows.append({'author': author, 'text': text})   
        log(f"📚 已加载 {len(existing_rows)} 条历史语录", 'info')
    except Exception as e:
        log(f"⚠️ 读取现有文件失败: {e}，将创建新文件", 'warning')
    return existing_set, existing_rows

def prune_old_quotes(existing_rows, count_to_remove):
    """
    随机删除指定数量的旧语录
    """
    current_count = len(existing_rows)
    if current_count <= count_to_remove:
        log(f"⚠️ 当前语录只有 {current_count} 条，少于或等于要删除的 {count_to_remove} 条，不清空，保留全部。", 'warning')
        return existing_rows
    log(f"✂️ 正在随机删除 {count_to_remove} 条旧语录...", 'info')
    random.shuffle(existing_rows)
    kept_rows = existing_rows[:current_count - count_to_remove]
    log(f"📉 删除完毕，剩余 {len(kept_rows)} 条历史语录", 'info')
    return kept_rows

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

def fetch_new_quotes(count, existing_set):
    """
    获取新的语录
    """
    new_quotes = []
    consecutive_failures = 0
    MAX_FAILURES = 20
    log(f"🚀 开始获取 {count} 条新语录...", 'info')
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(new_quotes) < count:
            needed = count - len(new_quotes)
            batch_size = min(needed, MAX_WORKERS * 2)
            source_index = random.randint(0, len(API_SOURCES) - 1)
            futures = [executor.submit(fetch_one_quote, source_index) for _ in range(batch_size)]
            round_success = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    unique_key = f"{result['text']}-{result['author']}"
                    if unique_key not in existing_set:
                        new_keys = {f"{q['text']}-{q['author']}" for q in new_quotes}
                        if unique_key not in new_keys:
                            existing_set.add(unique_key)
                            new_quotes.append(result)
                            round_success += 1
                            sys.stdout.write(f"\r   进度: {len(new_quotes)}/{count}")
                            sys.stdout.flush()
            if round_success == 0:
                consecutive_failures += 1
                log(f"⚠️ 第 {consecutive_failures} 次尝试未获取到新数据", 'warning')
            else:
                consecutive_failures = 0
            if consecutive_failures >= MAX_FAILURES:
                log(f"❌ 连续 {MAX_FAILURES} 次失败，终止获取", 'error')
                break
    elapsed = time.time() - start_time
    print()
    log(f"✅ 获取完成！新增 {len(new_quotes)} 条，耗时: {elapsed:.2f} 秒", 'info')
    return new_quotes

def rewrite_csv(all_quotes):
    """
    覆盖写入 CSV 文件
    """
    print("::group::💾 重写 CSV 文件")
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['author', 'text'])
            writer.writerows(all_quotes)
        print(f"✅ 文件已更新（无Header），当前总条数: {len(all_quotes)}")
        print("::endgroup::")
        return True
    except Exception as e:
        log(f"保存失败: {e}", 'error')
        return False

def generate_summary(new_quotes, total_count):
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        return
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# 📅 每日语录更新报告\n\n")
        f.write(f"**⏰ 更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n\n")
        f.write(f"**🆕 今日新增**: `{len(new_quotes)}` 条 \n\n")
        f.write(f"**📚 总计**: `{total_count}` 条 \n\n")
        f.write("### 🎲 今日新增预览\n")
        f.write("| 内容 | 出处 |\n")
        f.write("| :--- | :--- |\n")
        for q in new_quotes[:min(5, len(new_quotes))]:
            safe_text = q['text'].replace('|', '\\|')
            safe_author = q['author'].replace('|', '\\|')
            f.write(f"| {safe_text} | {safe_author} |\n")

if __name__ == "__main__":
    start_time = time.time()
    
    try:
        existing_set, existing_rows = load_existing_quotes()
        if len(existing_rows) >= TARGET_COUNT: 
            existing_rows = prune_old_quotes(existing_rows, TARGET_COUNT)
            existing_set = {f"{row['text']}-{row['author']}" for row in existing_rows}
        new_quotes = fetch_new_quotes(TARGET_COUNT, existing_set)
        if len(new_quotes) > 0:
            final_list = existing_rows + new_quotes
            if rewrite_csv(final_list):
                generate_summary(new_quotes, len(final_list))
                log("🎉 任务完成！", 'info')
            else:
                sys.exit(1)
        else:
            log("⚠️ 没有获取到新语录，文件保持不变", 'warning') 
    except Exception as e:
        log(f"严重错误: {e}", 'error')
        sys.exit(1)
