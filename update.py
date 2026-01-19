import requests
import csv
import time
import random

# --- 配置区域 ---
# 每次生成的语录数量（建议 50-100 条，太多加载慢，太少容易重复）
TARGET_COUNT = 100
# 输出文件名
OUTPUT_FILE = "quotes.csv"
# API 链接（一言 Hitokoto）
API_URL = "https://v1.hitokoto.cn/"
# -------------

def fetch_quotes(count):
    quotes = []
    seen = set() # 用于去重
    
    print(f"开始获取 {count} 条中文语录...")
    
    while len(quotes) < count:
        try:
            # 请求参数：c=i(一般), c=l(文学), c=k(诗词), encode=json
            # min_length/max_length 限制字数，适合放在新标签页
            params = {
                'c': ['i', 'l', 'k'],
                'encode': 'json',
                'min_length': 5,
                'max_length': 25
            }
            
            response = requests.get(API_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 提取内容
                text = data.get('hitokoto', '').strip()
                author = data.get('from', '佚名').strip()
                
                # 简单的校验
                if not text:
                    continue
                
                # 组合唯一标识进行去重
                unique_key = f"{text}-{author}"
                if unique_key not in seen:
                    seen.add(unique_key)
                    quotes.append({'text': text, 'author': author})
                    print(f"进度: {len(quotes)}/{count} - {text[:10]}...")
            
            # 稍微延时，礼貌访问，防止被限流
            time.sleep(0.5)
            
        except Exception as e:
            print(f"请求出错: {e}")
            time.sleep(2)
            
    return quotes

def save_csv(quotes):
    # 使用 utf-8 编码写入
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['text', 'author'])
        writer.writeheader()
        writer.writerows(quotes)
    print(f"成功生成 {OUTPUT_FILE}，共 {len(quotes)} 条语录。")

if __name__ == "__main__":
    data = fetch_quotes(TARGET_COUNT)
    save_csv(data)
