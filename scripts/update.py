import csv
import os
import sys
import random
import json
import time
import urllib.request
import urllib.error
import concurrent.futures
import re
from datetime import datetime

try:
    from nlp_scorer import (
        initialize_nlp, 
        nlp_score_quote, 
        deduplicate_quotes,
        smart_categorize_quote,
        filter_quotes_by_quality,
        filter_negative_quotes,
        nlp_analyze_quote,
        initialize_ai_judge,
        get_ai_stats
    )
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    print("⚠️  NLP module not available, using rule-based scoring only")

TARGET_COUNT = 15
MAX_LENGTH = 15
MIN_LENGTH = 3
OUTPUT_FILE = "quotes.csv"
MAX_WORKERS = 5
REQUEST_TIMEOUT = 10
SCORE_THRESHOLD = 60

CATEGORY_TARGETS = {
    "poetry": 0.25,
    "philosophy": 0.25,
    "literature": 0.25,
    "other": 0.25
}

BLACKLIST_WORDS = [
    "卧槽", "尼玛", "傻逼", "妈的", "老子", 
    "劳资", "草", "滚", "去死", "垃圾", "废物",
    "傻逼", "智障", "白痴", "弱智", "脑残",
    "打钱", "赚钱", "加盟", "代理", "推广", "广告",
    "加微信", "加好友", "扫码", "关注", "公众号"
]

BLACKLIST_AUTHORS = ["佚名"]

POETRY_KEYWORDS = [
    "兮", "矣", "哉", "也", "乎", "者", "之", "兮",
    "·", "诗", "词", "曲", "赋", "令", "引", "歌",
    "行", "吟", "叹", "调", "序", "记", "传", "铭",
    "李白", "杜甫", "苏轼", "辛弃疾", "王维", "白居易",
    "李清照", "陶渊明", "李商隐", "杜牧", "韩愈", "柳宗元",
    "欧阳修", "王安石", "黄庭坚", "陆游", "杨万里",
    "诗经", "楚辞", "汉赋", "唐诗", "宋词", "元曲",
    "临江仙", "蝶恋花", "浣溪沙", "鹧鸪天", "菩萨蛮",
    "满江红", "水调歌头", "念奴娇", "沁园春"
]

PHILOSOPHY_KEYWORDS = [
    "人生", "生命", "意义", "价值", "理想", "信念", "真理",
    "智慧", "哲理", "哲言", "名言", "格言", "箴言", "警句",
    "孔子", "孟子", "老子", "庄子", "墨子", "韩非子", "荀子",
    "苏格拉底", "柏拉图", "亚里士多德", "尼采", "叔本华",
    "康德", "黑格尔", "马克思", "罗素", "培根"
]

LITERATURE_KEYWORDS = [
    "小说", "散文", "杂文", "随笔", "文学", "名著", "经典",
    "鲁迅", "茅盾", "巴金", "老舍", "冰心", "张爱玲",
    "钱钟书", "沈从文", "朱自清", "徐志摩", "郭沫若",
    "村上春树", "马尔克斯", "海明威", "托尔斯泰",
    "陀思妥耶夫斯基", "卡夫卡", "博尔赫斯"
]

BEAUTIFUL_WORDS = [
    "温柔", "温暖", "美好", "幸福", "快乐", "希望", "梦想",
    "星空", "月光", "阳光", "清风", "花开", "叶落", "雪舞",
    "诗意", "浪漫", "温馨", "宁静", "安详", "从容", "淡定",
    "优雅", "高贵", "纯洁", "真诚", "善良", "勇敢", "坚强"
]

WISDOM_KEYWORDS = [
    "知", "智", "慧", "悟", "道", "理", "明", "觉", "思", "省",
    "心", "性", "命", "运", "缘", "空", "色", "寂", "静", "定",
    "取舍", "进退", "得失", "成败", "荣辱", "贵贱", "贫富",
    "生死", "别离", "聚散", "因缘", "果报", "轮回", "解脱",
    "放下", "执着", "分别", "妄想", "烦恼", "菩提", "涅槃",
    "自知", "知人", "知足", "知止", "知己", "知彼", "知命",
    "明理", "明道", "见性", "明心", "见道", "悟道", "证道",
    "修身", "养性", "齐家", "治国", "平天下", "格物", "致知",
    "诚意", "正心", "慎独", "自省", "自察", "自觉", "自悟",
    "淡泊", "宁静", "致远", "明志", "弘毅", "致远", "博学",
    "审问", "慎思", "明辨", "笃行", "勤学", "好问", "善思",
    "真理", "正义", "良知", "良心", "道德", "仁义", "礼智",
    "诚信", "忠恕", "孝悌", "廉耻", "气节", "风骨", "操守"
]

POSITIVE_WORDS = [
    "爱", "善", "美", "真", "诚", "信", "义", "仁", "礼", "智",
    "希望", "光明", "温暖", "美好", "幸福", "快乐", "喜悦", "安康",
    "平安", "吉祥", "如意", "圆满", "和谐", "和睦", "和顺", "和畅",
    "精进", "向上", "向善", "向美", "向好", "向阳", "向光",
    "勇敢", "坚强", "坚韧", "坚持", "坚定", "坚决", "坚毅",
    "宽容", "包容", "理解", "体谅", "关怀", "关爱", "关心",
    "感恩", "感谢", "感激", "感动", "感悟", "感慨", "感念"
]

def is_all_chinese(text):
    pattern = re.compile(r'^[\u4e00-\u9fa5，。？！；：""''（）【】、·\s]+$')
    return bool(pattern.match(text))

def has_wisdom_characteristics(text):
    wisdom_score = 0
    
    wisdom_count = sum(1 for kw in WISDOM_KEYWORDS if kw in text)
    if wisdom_count >= 2:
        wisdom_score += 30
    elif wisdom_count == 1:
        wisdom_score += 15
    
    if text.startswith("不") or text.startswith("无") or text.startswith("莫"):
        if len(text) >= 6:
            wisdom_score += 10
    
    if "知" in text and "不" in text:
        wisdom_score += 15
    if "心" in text and "静" in text:
        wisdom_score += 15
    if "道" in text and "理" in text:
        wisdom_score += 15
    
    if len(text) >= 6 and "，" in text:
        parts = text.split("，")
        if len(parts) >= 2 and len(parts[0]) >= 2 and len(parts[1]) >= 2:
            wisdom_score += 10
    
    return wisdom_score

def calculate_score(quote, source_name):
    score = 50
    text = quote['text']
    author = quote['author']
    
    if any(word in text for word in BLACKLIST_WORDS):
        return 0
    
    length = len(text)
    if MIN_LENGTH <= length <= 12:
        score += 25
    elif 12 < length <= MAX_LENGTH:
        score += 15
    elif length < MIN_LENGTH or length > MAX_LENGTH:
        score -= 25
    
    poetry_score = sum(1 for kw in POETRY_KEYWORDS if kw in text or kw in author)
    if poetry_score > 0:
        score += 25
        if "诗词" in source_name or "诗" in source_name:
            score += 10
    
    philosophy_score = sum(1 for kw in PHILOSOPHY_KEYWORDS if kw in text or kw in author)
    if philosophy_score > 0:
        score += 20
    
    literature_score = sum(1 for kw in LITERATURE_KEYWORDS if kw in text or kw in author)
    if literature_score > 0:
        score += 15
    
    wisdom_score = has_wisdom_characteristics(text)
    if wisdom_score > 0:
        score += wisdom_score
    
    positive_score = sum(1 for kw in POSITIVE_WORDS if kw in text)
    score += min(positive_score * 4, 20)
    
    beautiful_score = sum(1 for kw in BEAUTIFUL_WORDS if kw in text)
    score += min(beautiful_score * 2, 10)
    
    if author not in BLACKLIST_AUTHORS and len(author) > 1:
        score += 5
    
    if "·" in text or "，" in text or "。" in text:
        if poetry_score > 0 or wisdom_score > 0:
            score += 10
    
    if NLP_AVAILABLE:
        try:
            nlp_result = nlp_score_quote(quote)
            if nlp_result.get('nlp_available', False):
                nlp_bonus = nlp_result.get('total_nlp_score', 0)
                score += nlp_bonus
        except Exception as e:
            pass
    
    return min(max(score, 0), 100)

def categorize_quote(quote, source_name):
    if NLP_AVAILABLE:
        try:
            category, confidence = smart_categorize_quote(quote)
            if confidence > 0.5:
                return category
        except:
            pass
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    poetry_score = sum(1 for kw in POETRY_KEYWORDS if kw in text or kw in author)
    if poetry_score > 0 or "诗词" in source_name or "诗" in source_name:
        return "poetry"
    
    philosophy_score = sum(1 for kw in PHILOSOPHY_KEYWORDS if kw in text or kw in author)
    if philosophy_score > 0 or "哲学" in source_name:
        return "philosophy"
    
    literature_score = sum(1 for kw in LITERATURE_KEYWORDS if kw in text or kw in author)
    if literature_score > 0 or "文学" in source_name:
        return "literature"
    
    return "other"

API_SOURCES = [
    {
        "name": "一言（官方-诗词）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "i", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 4
    },
    {
        "name": "一言（官方-文学）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "d", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 3
    },
    {
        "name": "一言（官方-哲学）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "k", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 3
    },
    {
        "name": "一言（官方-动画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "a", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "一言（官方-漫画）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "b", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "一言（官方-影视）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "h", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "一言（官方-网易云）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "j", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "一言（官方-原创）",
        "url": "https://v1.hitokoto.cn/",
        "params": {"c": "e", "encode": "json", "min_length": 3, "max_length": MAX_LENGTH},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "apiopen.top-古诗文",
        "url": "https://api.apiopen.top/api/sentences",
        "params": {},
        "parser": lambda data: {"text": data.get("result", {}).get("name", "").strip(), "author": data.get("result", {}).get("from", "佚名").strip()},
        "weight": 4
    },
    {
        "name": "韩小韩（一言镜像）",
        "url": "https://api.vvhan.com/api/hitokoto",
        "params": {"type": "json"},
        "parser": lambda data: {"text": data.get("hitokoto", "").strip(), "author": data.get("from", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "夏柔（一言镜像）",
        "url": "https://api.xygeng.cn/one",
        "params": {},
        "parser": lambda data: {"text": data.get("data", {}).get("content", "").strip(), "author": data.get("data", {}).get("origin", "佚名").strip()},
        "weight": 1
    },
    {
        "name": "oick-随机一言",
        "url": "https://api.oick.cn/yiyan/api.php",
        "params": {},
        "parser": lambda data: {"text": data.get("text", "").strip() if isinstance(data, dict) else str(data).strip(), "author": "佚名"},
        "weight": 1
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
        self.api_calls = {s['name']: {'success': 0, 'fail': 0, 'too_long': 0, 'low_score': 0, 'not_chinese': 0} for s in API_SOURCES}
        self.category_counts = {'poetry': 0, 'philosophy': 0, 'literature': 0, 'other': 0}
        self.filtered_quotes = []
        self.negative_quotes = []
        self.low_quality_quotes = []
        self.duplicate_quotes = []
        self.semantic_duplicates = []
    def record_success(self, name): self.api_calls[name]['success'] += 1
    def record_fail(self, name): self.api_calls[name]['fail'] += 1
    def record_too_long(self, name): self.api_calls[name]['too_long'] += 1
    def record_low_score(self, name): self.api_calls[name]['low_score'] += 1
    def record_not_chinese(self, name): self.api_calls[name]['not_chinese'] += 1
    def add_filtered(self, quote, reason): self.filtered_quotes.append({'quote': quote, 'reason': reason})
    def add_negative(self, quote, reason): self.negative_quotes.append({'quote': quote, 'reason': reason})
    def add_low_quality(self, quote, grade, score): self.low_quality_quotes.append({'quote': quote, 'grade': grade, 'score': score})
    def add_duplicate(self, quote): self.duplicate_quotes.append(quote)
    def add_semantic_duplicate(self, quote): self.semantic_duplicates.append(quote)

stats_tracker = Stats()

def get_weighted_source_index():
    weights = [s.get('weight', 1) for s in API_SOURCES]
    total = sum(weights)
    r = random.uniform(0, total)
    cum_weight = 0
    for i, w in enumerate(weights):
        cum_weight += w
        if r <= cum_weight:
            return i
    return len(API_SOURCES) - 1

def get_category_deficit(existing_rows, target_total):
    category_counts = {'poetry': 0, 'philosophy': 0, 'literature': 0, 'other': 0}
    for row in existing_rows:
        cat = categorize_quote(row, "")
        category_counts[cat] += 1
    
    deficits = {}
    for cat, target_pct in CATEGORY_TARGETS.items():
        target_count = int(target_total * target_pct)
        deficits[cat] = target_count - category_counts[cat]
    
    return deficits

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

def fetch_one_quote():
    source_idx = get_weighted_source_index()
    source = API_SOURCES[source_idx]
    try:
        params = "&".join([f"{k}={v}" for k, v in source["params"].items()])
        url = f"{source['url']}?{params}" if params else source['url']
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            parsed = source["parser"](data)
            text, author = parsed.get("text", ""), parsed.get("author", "佚名").replace('\n', '')
            if text:
                if len(text) > MAX_LENGTH or len(text) < MIN_LENGTH:
                    stats_tracker.record_too_long(source['name'])
                    return None
                
                if not is_all_chinese(text):
                    stats_tracker.record_not_chinese(source['name'])
                    return None
                
                quote = {'text': text, 'author': author, 'source_name': source['name']}
                score = calculate_score(quote, source['name'])
                
                if score < SCORE_THRESHOLD:
                    stats_tracker.record_low_score(source['name'])
                    return None
                
                stats_tracker.record_success(source['name'])
                quote['score'] = score
                quote['category'] = categorize_quote(quote, source['name'])
                return quote
    except Exception as e:
        stats_tracker.record_fail(source['name'])
    return None

def fetch_new_quotes(target, existing_rows):
    new_quotes = []
    existing_keys = {f"{r['text']}-{r['author']}" for r in existing_rows}
    consecutive_failures = 0
    
    target_total = len(existing_rows) + target
    Log.info(f"Target: {target} | Limit: {MIN_LENGTH}-{MAX_LENGTH}字 | Score Threshold: {SCORE_THRESHOLD}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while len(new_quotes) < target and consecutive_failures < 150:
            batch = [executor.submit(fetch_one_quote) 
                     for _ in range(min(target - len(new_quotes) + 10, MAX_WORKERS * 3))]
            round_success = False
            
            deficits = get_category_deficit(existing_rows + new_quotes, target_total)
            
            for future in concurrent.futures.as_completed(batch):
                res = future.result()
                if res:
                    u_key = f"{res['text']}-{res['author']}"
                    if u_key not in existing_keys:
                        cat = res['category']
                        
                        if deficits.get(cat, 0) > 0 or len(new_quotes) < target * 0.5:
                            new_quotes.append(res)
                            existing_keys.add(u_key)
                            stats_tracker.category_counts[cat] += 1
                            round_success = True
                            sys.stdout.write(f"\r🚀 Progress: {len(new_quotes)}/{target} | {res['category']}({res['score']}分)")
                            sys.stdout.flush()
            
            consecutive_failures = 0 if round_success else consecutive_failures + 1
    
    print()
    new_quotes.sort(key=lambda x: x['score'], reverse=True)
    return new_quotes[:target]

def prune_rows(rows, count_to_remove):
    if not rows or count_to_remove <= 0:
        return rows
    
    actual_remove = min(len(rows), count_to_remove)
    Log.warning(f"Pruning {actual_remove} items...")
    
    scored_rows = []
    for row in rows:
        score = calculate_score(row, "existing")
        scored_rows.append({'row': row, 'score': score, 'category': categorize_quote(row, "")})
    
    category_counts = {}
    for sr in scored_rows:
        cat = sr['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    target_total = len(rows) - actual_remove
    keep = []
    for cat, target_pct in CATEGORY_TARGETS.items():
        target_keep = max(1, int(target_total * target_pct))
        cat_rows = [sr for sr in scored_rows if sr['category'] == cat]
        cat_rows.sort(key=lambda x: x['score'], reverse=True)
        keep.extend(cat_rows[:target_keep])
    
    remaining_needed = target_total - len(keep)
    if remaining_needed > 0:
        remaining = [sr for sr in scored_rows if sr not in keep]
        remaining.sort(key=lambda x: x['score'], reverse=True)
        keep.extend(remaining[:remaining_needed])
    
    return [sr['row'] for sr in keep]

def generate_report(new_quotes, total_count, removed_count):
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_path: return
    
    category_dist = {}
    sentiment_dist = {'positive': 0, 'neutral': 0, 'negative': 0}
    quality_dist = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    theme_dist = {}
    
    ai_stats = get_ai_stats() if NLP_AVAILABLE else None
    
    for q in new_quotes:
        cat = q.get('category', 'other')
        category_dist[cat] = category_dist.get(cat, 0) + 1
        
        if 'nlp_analysis' in q:
            analysis = q['nlp_analysis']
            sentiment = analysis.get('sentiment', 'neutral')
            sentiment_dist[sentiment] = sentiment_dist.get(sentiment, 0) + 1
            
            quality = analysis.get('quality', {})
            grade = quality.get('grade', 'D')
            quality_dist[grade] = quality_dist.get(grade, 0) + 1
            
            themes = analysis.get('themes', [])
            for theme, score in themes:
                theme_dist[theme] = theme_dist.get(theme, 0) + 1
    
    cat_names = {'poetry': '古诗词', 'philosophy': '哲学/名言', 'literature': '文学', 'other': '其他'}
    sentiment_names = {'positive': '积极', 'neutral': '中性', 'negative': '消极'}
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("# ✨ 语录自动更新报告\n\n")
        
        if ai_stats:
            f.write("## 🤖 AI 评估系统状态\n")
            ai_available = ai_stats.get('ai_available', False)
            ai_disabled = ai_stats.get('ai_disabled', False)
            
            if ai_disabled:
                f.write(f"| AI评估器状态: {'🔴 已禁用'}\n")
                f.write(f"\n**原因**: 连续失败超过阈值，已自动禁用\n")
                f.write(f"\n**使用的模型**: `{ai_stats.get('model_used', 'unknown')}`\n")
                f.write(f"\n| 指标 | 数量 |\n")
                f.write(f"| :--- | :---: |\n")
                f.write(f"| AI成功评估 | {ai_stats.get('ai_success_count', 0)} |\n")
                f.write(f"| AI失败次数 | {ai_stats.get('ai_fail_count', 0)} |\n")
                f.write(f"| NLP回退次数 | {ai_stats.get('nlp_fallback_count', 0)} |\n")
            elif ai_available:
                f.write(f"| AI评估器状态: {'✅ 运行中'}\n")
                f.write(f"\n**使用的模型**: `{ai_stats.get('model_used', 'unknown')}`\n")
                f.write(f"\n| 指标 | 数量 |\n")
                f.write(f"| :--- | :---: |\n")
                f.write(f"| AI成功评估 | {ai_stats.get('ai_success_count', 0)} |\n")
                f.write(f"| AI失败次数 | {ai_stats.get('ai_fail_count', 0)} |\n")
                f.write(f"| NLP回退次数 | {ai_stats.get('nlp_fallback_count', 0)} |\n")
            else:
                f.write(f"| AI评估器状态: {'❌ 未启用'}\n")
            f.write("\n")
        
        f.write("## 📈 总体统计\n")
        f.write(f"| 今日新增 | 今日移除 | 库存总量 | 长度限制 | 评分阈值 |\n")
        f.write(f"| :---: | :---: | :---: | :---: | :---: |\n")
        f.write(f"| `{len(new_quotes)}` | `{removed_count}` | `{total_count}` | `{MIN_LENGTH}-{MAX_LENGTH}字` | `{SCORE_THRESHOLD}` |\n\n")
        
        total_filtered = (
            len(stats_tracker.filtered_quotes) + 
            len(stats_tracker.negative_quotes) + 
            len(stats_tracker.low_quality_quotes) +
            len(stats_tracker.semantic_duplicates)
        )
        if total_filtered > 0:
            f.write(f"### 🚫 过滤统计\n")
            f.write(f"| 过滤类型 | 数量 |\n")
            f.write(f"| :--- | :---: |\n")
            if len(stats_tracker.semantic_duplicates) > 0:
                f.write(f"| 语义重复 | {len(stats_tracker.semantic_duplicates)} |\n")
            if len(stats_tracker.negative_quotes) > 0:
                f.write(f"| 消极情感 | {len(stats_tracker.negative_quotes)} |\n")
            if len(stats_tracker.low_quality_quotes) > 0:
                f.write(f"| 低质量 | {len(stats_tracker.low_quality_quotes)} |\n")
            f.write("\n")
        
        f.write("## 📊 详细统计\n\n")
        
        f.write("<details>\n<summary>📈 类别分布</summary>\n\n")
        f.write("| 类别 | 数量 | 占比 |\n")
        f.write("| :--- | :---: | :---: |\n")
        total = sum(category_dist.values()) if category_dist else 1
        for cat, cnt in sorted(category_dist.items(), key=lambda x: x[1], reverse=True):
            pct = f"{cnt/total*100:.1f}%"
            f.write(f"| {cat_names.get(cat, cat)} | {cnt} | {pct} |\n")
        f.write("\n</details>\n\n")
        
        if NLP_AVAILABLE and any(sentiment_dist.values()):
            f.write("<details>\n<summary>😊 情感分布</summary>\n\n")
            f.write("| 情感 | 数量 | 占比 |\n")
            f.write("| :--- | :---: | :---: |\n")
            total_sent = sum(sentiment_dist.values()) if any(sentiment_dist.values()) else 1
            for sent, cnt in sorted(sentiment_dist.items(), key=lambda x: x[1], reverse=True):
                if cnt > 0:
                    pct = f"{cnt/total_sent*100:.1f}%"
                    f.write(f"| {sentiment_names.get(sent, sent)} | {cnt} | {pct} |\n")
            f.write("\n</details>\n\n")
            
            f.write("<details>\n<summary>⭐ 质量分布</summary>\n\n")
            f.write("| 等级 | 数量 | 占比 |\n")
            f.write("| :--- | :---: | :---: |\n")
            total_quality = sum(quality_dist.values()) if any(quality_dist.values()) else 1
            for grade in ['A', 'B', 'C', 'D']:
                cnt = quality_dist.get(grade, 0)
                if cnt > 0:
                    pct = f"{cnt/total_quality*100:.1f}%"
                    f.write(f"| {grade}级 | {cnt} | {pct} |\n")
            f.write("\n</details>\n\n")
            
            if theme_dist:
                f.write("<details>\n<summary>🏷️ 主题分布</summary>\n\n")
                f.write("| 主题 | 数量 |\n")
                f.write("| :--- | :---: |\n")
                for theme, cnt in sorted(theme_dist.items(), key=lambda x: x[1], reverse=True)[:8]:
                    f.write(f"| {theme} | {cnt} |\n")
                f.write("\n</details>\n\n")
        
        f.write("<details>\n<summary>📡 API 统计</summary>\n\n")
        f.write("| 接口名称 | 成功 | 低分过滤 | 非中文过滤 | 太长/太短 | 失败 |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for name, data in stats_tracker.api_calls.items():
            if any(data.values()):
                f.write(f"| {name} | {data['success']} | {data.get('low_score', 0)} | {data.get('not_chinese', 0)} | {data['too_long']} | {data['fail']} |\n")
        f.write("\n</details>\n\n")
        
        f.write("## 📝 语录详情\n\n")
        
        if new_quotes:
            f.write("<details>\n<summary>🎲 新增内容详情 ({len(new_quotes)}条)</summary>\n\n")
            f.write("| # | 评分 | 等级 | 类别 | 情感 | 字数 | 语录内容 | 作者 |\n")
            f.write("| :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |\n")
            for i, q in enumerate(new_quotes, 1):
                grade = q.get('quality_grade', 'N/A')
                sentiment_icon = {'positive': '😊', 'neutral': '😐', 'negative': '😢'}.get(q.get('sentiment', 'neutral'), '😐')
                f.write(f"| {i} | {q['score']} | {grade} | {cat_names.get(q['category'], q['category'])} | {sentiment_icon} | {len(q['text'])} | {q['text']} | {q['author']} |\n")
            f.write("\n</details>\n\n")
        
        if stats_tracker.negative_quotes:
            f.write("<details>\n<summary>🚫 被过滤的消极语录 ({len(stats_tracker.negative_quotes)}条)</summary>\n\n")
            f.write("| # | 语录内容 | 作者 | 过滤原因 |\n")
            f.write("| :---: | :--- | :--- | :--- |\n")
            for i, item in enumerate(stats_tracker.negative_quotes[:20], 1):
                q = item['quote']
                reason = item.get('reason', '消极情感')
                f.write(f"| {i} | {q['text']} | {q['author']} | {reason} |\n")
            if len(stats_tracker.negative_quotes) > 20:
                f.write(f"\n*还有 {len(stats_tracker.negative_quotes) - 20} 条...*\n")
            f.write("\n</details>\n\n")
        
        if stats_tracker.low_quality_quotes:
            f.write("<details>\n<summary>⚠️ 被过滤的低质量语录 ({len(stats_tracker.low_quality_quotes)}条)</summary>\n\n")
            f.write("| # | 语录内容 | 作者 | 等级 | 得分 |\n")
            f.write("| :---: | :--- | :--- | :---: | :---: |\n")
            for i, item in enumerate(stats_tracker.low_quality_quotes[:20], 1):
                q = item['quote']
                f.write(f"| {i} | {q['text']} | {q['author']} | {item['grade']} | {item['score']:.2f} |\n")
            if len(stats_tracker.low_quality_quotes) > 20:
                f.write(f"\n*还有 {len(stats_tracker.low_quality_quotes) - 20} 条...*\n")
            f.write("\n</details>\n")

if __name__ == "__main__":
    try:
        if NLP_AVAILABLE:
            initialize_nlp()
            initialize_ai_judge()
        
        old_rows = load_existing_quotes()
        new_list = fetch_new_quotes(TARGET_COUNT, old_rows)
        
        if new_list and NLP_AVAILABLE:
            try:
                Log.info("🧠 Applying NLP semantic deduplication...")
                original_count = len(new_list)
                deduplicated_list = []
                seen_texts = set()
                
                for quote in new_list:
                    text = quote.get('text', '')
                    if text not in seen_texts:
                        deduplicated_list.append(quote)
                        seen_texts.add(text)
                    else:
                        stats_tracker.add_duplicate(quote)
                
                new_list = deduplicate_quotes(deduplicated_list)
                deduplicated = original_count - len(new_list)
                if deduplicated > 0:
                    Log.info(f"Removed {deduplicated} semantic duplicates")
                    for i in range(deduplicated):
                        if i < len(stats_tracker.duplicate_quotes):
                            stats_tracker.add_semantic_duplicate(stats_tracker.duplicate_quotes[i])
                
                Log.info("😊 Filtering negative sentiment quotes...")
                original_count = len(new_list)
                new_list, negative_quotes = filter_negative_quotes(new_list)
                for nq in negative_quotes:
                    stats_tracker.add_negative(nq, nq.get('negative_reason', '消极情感'))
                if len(negative_quotes) > 0:
                    Log.info(f"Filtered {len(negative_quotes)} negative quotes")
                
                Log.info("🎯 Filtering quotes by AI judge and quality...")
                original_count = len(new_list)
                filtered_list = []
                for quote in new_list:
                    quality = nlp_analyze_quote(quote).get('quality', {})
                    grade = quality.get('grade', 'D')
                    score = quality.get('total_score', 0)
                    breakdown = quality.get('breakdown', {})
                    
                    should_keep = True
                    ai_judged = False
                    if 'ai_judged' in breakdown and 'should_keep' in breakdown:
                        should_keep = breakdown['should_keep']
                        ai_judged = True
                    
                    if should_keep and grade in ['A', 'B', 'C']:
                        quote['quality_grade'] = grade
                        quote['quality_score'] = score
                        quote['ai_should_keep'] = should_keep
                        quote['ai_judged'] = ai_judged
                        filtered_list.append(quote)
                    else:
                        reason = f"AI judge: {should_keep}, Grade: {grade}"
                        stats_tracker.add_low_quality(quote, grade, score)
                
                new_list = filtered_list
                filtered = original_count - len(new_list)
                if filtered > 0:
                    Log.info(f"Filtered {filtered} low-quality quotes")
                
                Log.info("📊 Analyzing quotes with NLP...")
                for quote in new_list:
                    analysis = nlp_analyze_quote(quote)
                    quote['nlp_analysis'] = analysis
                    quote['sentiment'] = analysis.get('sentiment', 'neutral')
                    quote['quality_grade'] = analysis.get('quality', {}).get('grade', 'C')
                    
            except Exception as e:
                Log.warning(f"NLP processing skipped: {e}")
        
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
