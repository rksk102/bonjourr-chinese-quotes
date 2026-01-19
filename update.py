import requests
import csv
import time
import random

TARGET_COUNT = 100
OUTPUT_FILE = "quotes.csv"
API_URL = "https://v1.hitokoto.cn/"

def fetch_quotes(count):
    quotes = []
    seen = set()
    
    print(f"开始获取 {count} 条中文语录...")
    
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
                    print(f"进度: {len(quotes)}/{count} - {text[:10]}...")

            time.sleep(0.5)
            
        except Exception as e:
            print(f"请求出错: {e}")
            time.sleep(2)
            
    return quotes

def save_csv(quotes):
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['text', 'author'])
        writer.writeheader()
        writer.writerows(quotes)
    print(f"成功生成 {OUTPUT_FILE}，共 {len(quotes)} 条语录。")

if __name__ == "__main__":
    data = fetch_quotes(TARGET_COUNT)
    save_csv(data)
