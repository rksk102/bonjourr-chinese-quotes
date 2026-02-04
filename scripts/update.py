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
MAX_LENGTH = 15
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 5
REQUEST_TIMEOUT = 10

API_SOURCES = [
    {
        "name": "一言（官方-动画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "a", "encode": "json", "min_length": 1, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-漫画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "b", "encode": "json", "min_length": 1, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-文学）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "d", "encode": "json", "min_length": 1, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-诗词）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "i", "encode": "json", "min_length": 1, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "韩小韩（一言镜像）",
        "url": "https://api.vvhan.com/api/hitokoto",
        "params": {"type": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "夏柔（一言镜像）",
        "url": "https://api.xygeng.cn/one",
        "params": {},
        "parser": lambda data: {"text": data.get("data", {}).get("content", "").strip(), "author": data.get("data", {}).get("origin", "佚名").strip()}
    }
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (GitHub Actions; Quote Updater)'}

class Log:
    CYAN, GREEN, YELLOW, RED, RESET = '\033[96m', '\033[92m', '\033[93m', '\033[91m', '\033[0m'
    @staticmethod
    def info(msg): print(f"{Log.CYAN}ℹ️  {msg}{Log.RESET}")
    @staticmethod
    def success(msg): print(f"{Log.GREEN}✅ {msg}{Log.RESET}")
    @staticmethod
    def warning(msg): print(f"{Log.YELLOW}⚠️  {msg}{Log.RESET}")
    @staticmethod
    def error(msg): print(f"{Log.RED}❌ {msg}{Log.RESET}")

class Stats:
    def __init__(self):
        self.api_calls = {s['name']: {'success': 0, 'fail': 0, 'too_long': 0} for s in API_SOURCES}
    def record_success(self, name): self.api_calls[name]['success'] += 1
    def record_fail(self, name): self.api_calls[name]['fail'] += 1
    def record_too_long(self, name): self.api_calls[name]['too_long'] += 1

stats_tracker = Stats()

def load_existing_quotes():
    existing_rows = []
    if not os.path.exists(OUTPUT_FILE):
        return existing_rows
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, fieldnames=['author', 'text'])
            for row in reader:
                text, author = row.get('text', '').strip(), row.get('author', '').strip()
                if text and text != 'text':
                    existing_rows.append({'author': author, 'text': text})
    except Exception as e:
        Log.error(f"Error: {e}")
    return existing_rows

def fetch_one_quote(source_index=0):
    for i in range(source_index, len(API_SOURCES)):
        source = API_SOURCES[i]
        try:
            params = "&".join([f"{k}={v}" for k, v in source["params"].items()])
            url = f"{source['url']}?{params}" if params else source['url']
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                parsed = source["parser"](data)
                text, author = parsed.get("text", ""), parsed.get("author", "佚名").replace('\n', '')
                if text:
                    if len(text) > MAX_LENGTH:
                        stats_tracker.record_too_long(source['name'])
                        continue
                    stats_tracker.record_success(source['name'])
                    return {'text': text, 'author': author, 'source_name': source['name']}
        except:
            stats_tracker.record_fail(source['name'])
    return None

def fetch_new_quotes(target, existing_rows):
    new_quotes = []
    existing_keys = {f"{r['text']}-{r['author']}" for r in existing_rows}
    consecutive_failures = 0
    Log.info(f"Target: {target} | Limit: {MAX_LENGTH}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(new_quotes) < target and consecutive_failures < 100:
            batch = [executor.submit(fetch_one_quote, random.randint(0, len(API_SOURCES)-1)) 
                     for _ in range(min(target - len(new_quotes) + 5, MAX_WORKERS * 2))]
            round_success = False
            for future in concurrent.futures.as_completed(batch):
                res = future.result()
                if res:
                    u_key = f"{res['text']}-{res['author']}"
                    if u_key not in existing_keys:
                        new_quotes.append(res)
                        existing_keys.add(u_key)
                        round_success = True
                        sys.stdout.write(f"\r🚀 Progress: {len(new_quotes)}/{target}")
                        sys.stdout.flush()
            consecutive_failures = 0 if round_success else consecutive_failures + 1
    print()
    return new_quotes

def prune_rows(rows, count_to_remove):
    if not rows or count_to_remove <= 0:
        return rows
    actual_remove = min(len(rows), count_to_remove)
    Log.warning(f"Pruning {actual_remove} items...")
    random.shuffle(rows)
    return rows[actual_remove:]

def generate_report(new_quotes, total_count, removed_count):
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path: return
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# ✨ 语录自动更新报告\n")
        f.write(f"| 今日新增 | 今日移除 | 库存总量 | 长度限制 |\n")
        f.write(f"| :---: | :---: | :---: | :---: |\n")
        f.write(f"| `{len(new_quotes)}` | `{removed_count}` | `{total_count}` | `{MAX_LENGTH}字` |\n\n")
        f.write("### 📡 API 统计\n| 接口名称 | 成功 | 太长过滤 | 失败 |\n| :--- | :---: | :---: | :---: |\n")
        for name, data in stats_tracker.api_calls.items():
            if any(data.values()):
                f.write(f"| {name} | {data['success']} | {data['too_long']} | {data['fail']} |\n")
        if new_quotes:
            f.write("\n### 🎲 新增内容预览\n| 字数 | 语录内容 | 作者 |\n| :---: | :--- | :--- |\n")
            for q in new_quotes:
                f.write(f"| {len(q['text'])} | {q['text']} | {q['author']} |\n")

if __name__ == "__main__":
    try:
        old_rows = load_existing_quotes()
        new_list = fetch_new_quotes(TARGET_COUNT, old_rows)
        if new_list:
            kept_rows = prune_rows(old_rows, len(new_list))
            final_rows = kept_rows + new_list
            with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['author', 'text'], extrasaction='ignore')
                writer.writerows(final_rows)
            generate_report(new_list, len(final_rows), len(old_rows) - len(kept_rows))
            Log.success(f"Success! +{len(new_list)} / -{len(old_rows) - len(kept_rows)}")
        else:
            Log.warning("No new quotes found.")
    except Exception as e:
        Log.error(f"Fatal: {e}")
        sys.exit(1)
