import requests
import csv
import time
import os
import sys
from datetime import datetime

TARGET_COUNT = 100
OUTPUT_FILE = "quotes.csv"
API_URL = "https://v1.hitokoto.cn/"

def log(message, type='info'):
    """
    输出带格式的日志，GitHub Actions 会识别这些特殊格式
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    if type == 'error':
        print(f"::error file={__file__},line={sys._getframe(1).f_lineno}::{message}")
    elif type == 'warning':
        print(f"::warning::{message}")
    else:
        print(f"[{timestamp}] {message}")

def fetch_quotes(count):
    quotes = []
    seen = set()
    errors = 0
    log(f"🚀 开始任务：目标获取 {count} 条中文语录", 'info')
    print("::group::🌐 正在请求数据源 (Hitokoto API)")
    
    while len(quotes) < count:
        try:
            params = {
                'c': ['i', 'l', 'k'],
                'encode': 'json',
                'min_length': 5,
                'max_length': 25
            }
            
            response = requests.get(API_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get('hitokoto', '').strip()
                author = data.get('from', '佚名').strip()
                if not text:
                    continue
                unique_key = f"{text}-{author}"
                if unique_key not in seen:
                    seen.add(unique_key)
                    quotes.append({'text': text, 'author': author})
                    if len(quotes) % 20 == 0:
                        print(f"   当前进度: {len(quotes)}/{count}")
            else:
                log(f"API 返回状态码异常: {response.status_code}", 'warning')
                
        except Exception as e:
            errors += 1
            log(f"请求发生异常: {str(e)}", 'warning')
            if errors > 5:
                log("连续错误过多，终止任务以防被限流。", 'error')
                sys.exit(1)
            time.sleep(2)
        time.sleep(0.5)
    print("::endgroup::")
    log(f"✅ 数据获取完成，共 {len(quotes)} 条，失败 {errors} 次", 'info')
    return quotes
def save_csv(quotes):
    print("::group::💾 正在写入 CSV 文件")
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['text', 'author'])
            writer.writeheader()
            writer.writerows(quotes)
        print(f"文件已保存: {OUTPUT_FILE}")
        print("前 3 条预览:")
        for i, q in enumerate(quotes[:3]):
            print(f"  {i+1}. {q['text']} —— {q['author']}")
        print("::endgroup::")
        return True
    except Exception as e:
        log(f"保存 CSV 失败: {e}", 'error')
        return False

def generate_summary(quotes):
    """
    生成 GitHub Actions 顶部的摘要卡片
    """
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path:
        return

    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# 📜 语录更新报告\n\n")
        f.write(f"**⏰ 运行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n\n")
        f.write(f"**📊 更新数量**: `{len(quotes)}` 条 \n\n")
        f.write(f"**📁 输出文件**: `quotes.csv` \n\n")
        f.write("### 🎲 随机预览 (5条)\n")
        f.write("| 序号 | 内容 | 出处 |\n")
        f.write("| :--- | :--- | :--- |\n")
        import random
        preview_quotes = random.sample(quotes, min(5, len(quotes)))
        for i, q in enumerate(preview_quotes):
            safe_text = q['text'].replace('|', '\\|')
            safe_author = q['author'].replace('|', '\\|')
            f.write(f"| {i+1} | {safe_text} | {safe_author} |\n")
        f.write("\n---\n")
        f.write("*由 GitHub Actions 自动生成*")

if __name__ == "__main__":
    try:
        data = fetch_quotes(TARGET_COUNT)
        if save_csv(data):
            generate_summary(data)
            log("🎉 所有任务执行成功！", 'info')
        else:
            sys.exit(1)
    except Exception as e:
        log(f"程序未捕获的严重错误: {e}", 'error')
        sys.exit(1)
