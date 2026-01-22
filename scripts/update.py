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
PRUNE_COUNT = 15
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 4
REQUEST_TIMEOUT = 8
API_SOURCES = [
    {
        "name": "一言（官方-动画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "a", "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-漫画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "b", "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-文学）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "d", "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-诗词）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "i", "encode": "json", "min_length": 5, "max_length": 30},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()}
    },
    {
        "name": "一言（官方-哲学）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "k", "encode": "json", "min_length": 5, "max_length": 30},
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class Log:
    RESET = '\033[0m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    @staticmethod
    def info(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Log.BLUE}[{timestamp}] ℹ️  {msg}{Log.RESET}")
    @staticmethod
    def success(msg):
        print(f"{Log.GREEN}✅ {msg}{Log.RESET}")
    @staticmethod
    def warning(msg):
        print(f"{Log.YELLOW}⚠️  {msg}{Log.RESET}")
    @staticmethod
    def error(msg):
        print(f"{Log.RED}❌ {msg}{Log.RESET}")
    @staticmethod
    def group_start(title):
        print(f"::group::{title}")
    @staticmethod
    def group_end():
        print("::endgroup::")

class Stats:
    def __init__(self):
        self.api_calls = {source['name']: {'success': 0, 'fail': 0} for source in API_SOURCES}
    def record_success(self, name):
        if name in self.api_calls:
            self.api_calls[name]['success'] += 1
    def record_fail(self, name):
        if name in self.api_calls:
            self.api_calls[name]['fail'] += 1
stats_tracker = Stats()

def load_existing_quotes():
    """读取 CSV 返回集合和列表"""
    Log.group_start("📖 正在读取历史数据")
    existing_set = set()
    existing_rows = []
    if not os.path.exists(OUTPUT_FILE):
        Log.warning(f"文件 {OUTPUT_FILE} 不存在，将初始化新文件")
        Log.group_end()
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
        Log.info(f"读取成功 | 当前总数: {len(existing_rows)}")
    except Exception as e:
        Log.error(f"读取文件时发生错误: {e}")
    Log.group_end()
    return existing_set, existing_rows

def prune_old_quotes(existing_rows, count_to_remove):
    """随机删除旧数据"""
    current_count = len(existing_rows)
    Log.group_start(f"✂️ 数据修剪 (目标删除: {count_to_remove})")
    if current_count <= count_to_remove:
        Log.warning(f"当前条数 ({current_count}) 不足，跳过删除操作")
        Log.group_end()
        return existing_rows
    Log.info(f"正在从 {current_count} 条数据中随机移除 {count_to_remove} 条...")
    random.shuffle(existing_rows)
    kept_rows = existing_rows[:current_count - count_to_remove]
    Log.success(f"修剪完成 | 剩余: {len(kept_rows)}")
    Log.group_end()
    return kept_rows

def fetch_one_quote(source_index=0):
    """单条抓取逻辑（带详细错误记录）"""
    start_time = time.time()
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
                    stats_tracker.record_success(source['name'])
                    return {
                        'text': text, 
                        'author': author, 
                        'source_name': source['name']
                    }
        except Exception as e:
            stats_tracker.record_fail(source['name'])
            pass
    return None

def draw_progress_bar(current, total, bar_length=30):
    percent = float(current) * 100 / total
    arrow = '▓' * int(percent / 100 * bar_length)
    spaces = '░' * (bar_length - len(arrow))
    sys.stdout.write(f"\r{Log.CYAN}🚀 正在抓取: [{arrow}{spaces}] {int(percent)}% ({current}/{total}){Log.RESET}")
    sys.stdout.flush()

def fetch_new_quotes(target, existing_set):
    """并发抓取主循环"""
    new_quotes = []
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 50
    print("\n")
    Log.info(f"开始网络作业 | 目标新增: {target} 条")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(new_quotes) < target:
            needed = target - len(new_quotes)
            batch_size = min(needed + 2, MAX_WORKERS * 2) 
            futures = []
            for _ in range(batch_size):
                src_idx = random.randint(0, len(API_SOURCES) - 1)
                futures.append(executor.submit(fetch_one_quote, src_idx))
            round_has_success = False
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    u_key = f"{result['text']}-{result['author']}"
                    if u_key not in existing_set:
                        current_new_keys = {f"{q['text']}-{q['author']}" for q in new_quotes}
                        if u_key not in current_new_keys:
                            new_quotes.append(result)
                            existing_set.add(u_key)
                            round_has_success = True
                            if len(new_quotes) <= target:
                                draw_progress_bar(len(new_quotes), target)
            if not round_has_success:
                consecutive_failures += 1
            else:
                consecutive_failures = 0
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print()
                Log.error(f"连续 {MAX_CONSECUTIVE_FAILURES} 次抓取失败，提前终止。")
                break
    print()
    Log.success(f"抓取作业完成 | 实际获取: {len(new_quotes)} 条")
    return new_quotes

def rewrite_csv(all_quotes):
    """重写文件"""
    Log.group_start("💾 数据回写")
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['author', 'text'], extrasaction='ignore')
            writer.writerows(all_quotes)
        Log.success(f"文件覆写成功 ({len(all_quotes)} 条记录)")
        Log.group_end()
        return True
    except Exception as e:
        Log.error(f"文件写入失败: {e}")
        Log.group_end()
        return False

def generate_report(new_quotes, total_count):
    """生成漂亮的 GitHub Summary"""
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        return
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# ✨ 每日语录自动更新报告\n")
        f.write(f"> **⏰ 运行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n")
        f.write("### 📊 核心指标\n")
        f.write("| 🆕 今日新增 | 📉 今日移除 | 📚 当前库存 |\n")
        f.write("| :---: | :---: | :---: |\n")
        f.write(f"| `{len(new_quotes)}` | `{PRUNE_COUNT}` | `{total_count}` |\n\n")
        f.write("<details><summary><b>📡 API 调用统计 (点此展开)</b></summary>\n\n")
        f.write("| API 名称 | ✅ 成功次数 | ❌ 失败/跳过 |\n")
        f.write("| :--- | :---: | :---: |\n")
        for name, data in stats_tracker.api_calls.items():
            if data['success'] > 0 or data['fail'] > 0:
                f.write(f"| {name} | {data['success']} | {data['fail']} |\n")
        f.write("\n</details>\n\n")
        f.write("### 🎲 新增条目预览 (Top 10)\n")
        f.write("| 内容 | 作者/出处 | 来源渠道 |\n")
        f.write("| :--- | :--- | :--- |\n")
        for q in new_quotes[:min(10, len(new_quotes))]:
            safe_text = q['text'].replace('|', '\\|').replace('\n', ' ')
            safe_author = q['author'].replace('|', '\\|')
            safe_source = q.get('source_name', '未知')
            f.write(f"| {safe_text} | {safe_author} | `{safe_source}` |\n")

if __name__ == "__main__":
    Log.info("脚本启动...")
    
    try:
        exist_set, exist_rows = load_existing_quotes()
        if len(exist_rows) >= PRUNE_COUNT:
            exist_rows = prune_old_quotes(exist_rows, PRUNE_COUNT)
            exist_set = {f"{r['text']}-{r['author']}" for r in exist_rows}
        new_data = fetch_new_quotes(TARGET_COUNT, exist_set)
        
        if len(new_data) > 0:
            final_data = exist_rows + new_data
            if rewrite_csv(final_data):
                generate_report(new_data, len(final_data))
            else:
                sys.exit(1)
        else:
            Log.warning("本次运行未获取到任何新数据。")
            
    except KeyboardInterrupt:
        Log.error("用户中断操作")
        sys.exit(130)
    except Exception as e:
        Log.error(f"未捕获的异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
