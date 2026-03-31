import os
import sys
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

USE_NLP = os.environ.get('USE_NLP', 'false').lower() == 'true'

MODEL_LOADED = False
embedder = None

CATEGORY_EXAMPLES = {
    'poetry': [
        '海内存知己，天涯若比邻',
        '人生自古谁无死',
        '路漫漫其修远兮',
        '春眠不觉晓',
        '床前明月光',
        '举头望明月',
        '桃花潭水深千尺',
        '明月几时有',
        '但愿人长久',
        '千里共婵娟'
    ],
    'philosophy': [
        '知之为知之，不知为不知',
        '三人行必有我师',
        '学而不思则罔',
        '己所不欲勿施于人',
        '天行健君子以自强不息',
        '上善若水',
        '道可道非常道',
        '知足常乐',
        '宁静致远',
        '淡泊明志'
    ],
    'literature': [
        '生活不止眼前的苟且',
        '愿你出走半生',
        '归来仍是少年',
        '世界那么大',
        '我想去看看',
        '人生若只如初见',
        '何事秋风悲画扇',
        '山重水复疑无路',
        '柳暗花明又一村',
        '此情可待成追忆'
    ],
    'other': [
        '加油',
        '努力',
        '奋斗',
        '坚持',
        '梦想',
        '希望',
        '明天会更好',
        '相信自己',
        '永不放弃',
        '勇往直前'
    ]
}

THEME_KEYWORDS = {
    '励志': ['奋斗', '努力', '坚持', '梦想', '成功', '拼搏', '进取', '向上', '自强'],
    '爱情': ['爱', '情', '恋', '思念', '相思', '牵挂', '眷恋', '深情', '挚爱'],
    '友情': ['友', '知己', '朋友', '情谊', '患难', '相知', '莫逆', '挚友'],
    '人生': ['人生', '命运', '生死', '轮回', '缘分', '际遇', '沧桑', '浮沉'],
    '自然': ['山', '水', '花', '月', '风', '雨', '雪', '云', '春', '秋'],
    '哲理': ['道', '理', '悟', '智', '慧', '心', '性', '命', '空', '静'],
    '家国': ['国', '家', '天下', '民族', '兴亡', '社稷', '苍生', '黎民'],
    '时光': ['岁月', '时光', '年华', '青春', '往事', '回忆', '流年', '光阴']
}

SENTIMENT_POSITIVE = [
    '爱', '美', '善', '真', '好', '喜', '乐', '福', '安', '康',
    '希望', '光明', '温暖', '幸福', '快乐', '美好', '成功', '胜利',
    '勇敢', '坚强', '智慧', '善良', '真诚', '友爱', '和谐', '圆满',
    '春', '花', '月', '阳光', '彩虹', '星辰', '黎明', '朝阳'
]

SENTIMENT_NEGATIVE = [
    '恨', '怨', '愁', '悲', '苦', '痛', '伤', '泪', '死', '亡',
    '绝望', '黑暗', '寒冷', '孤独', '悲伤', '痛苦', '失败', '毁灭',
    '恐惧', '愤怒', '嫉妒', '贪婪', '仇恨', '战争', '灾难', '悲剧',
    '秋', '落叶', '黄昏', '黑夜', '阴霾', '风雨', '寒冬', '暮色'
]

QUALITY_INDICATORS = {
    'high': {
        'patterns': ['，', '。', '？', '！', '；', '：', '·'],
        'keywords': ['兮', '矣', '哉', '也', '乎', '者', '之']
    },
    'medium': {
        'patterns': ['，', '。'],
        'keywords': []
    }
}

def initialize_nlp():
    global MODEL_LOADED, embedder
    
    if MODEL_LOADED or not USE_NLP:
        return True
    
    try:
        print("🧠 Initializing GTE-large-zh NLP model...")
        
        from sentence_transformers import SentenceTransformer
        
        print("📥 Loading GTE-large-zh (Alibaba DAMO Academy)...")
        print("   Model size: ~670MB | Dimension: 1024 | C-MTEB Score: 66.72")
        embedder = SentenceTransformer('thenlper/gte-large-zh', device='cpu')
        
        print("🔧 Pre-computing category embeddings...")
        _precompute_category_embeddings()
        
        MODEL_LOADED = True
        print("✅ GTE-large-zh model loaded successfully!")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not load NLP models: {e}")
        print("💡 Falling back to rule-based scoring only.")
        return False

_category_embeddings = {}

def _precompute_category_embeddings():
    global _category_embeddings
    for category, examples in CATEGORY_EXAMPLES.items():
        embeddings = embedder.encode(examples)
        _category_embeddings[category] = np.mean(embeddings, axis=0)
    print(f"   ✓ Pre-computed embeddings for {len(_category_embeddings)} categories")

def get_embedding(text: str) -> Optional[np.ndarray]:
    if not USE_NLP or not MODEL_LOADED or embedder is None:
        return None
    try:
        return embedder.encode([text])[0]
    except:
        return None

def calculate_semantic_similarity(text1: str, text2: str) -> float:
    if not USE_NLP or not MODEL_LOADED:
        return 0.0
    
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)
    
    if emb1 is None or emb2 is None:
        return 0.0
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return float(similarity)
    except:
        return 0.0

def smart_categorize_quote(quote: Dict[str, str]) -> Tuple[str, float]:
    if not USE_NLP or not MODEL_LOADED:
        return 'other', 0.0
    
    text = quote.get('text', '')
    text_emb = get_embedding(text)
    
    if text_emb is None or not _category_embeddings:
        return 'other', 0.0
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        
        best_category = 'other'
        best_score = 0.0
        
        for category, cat_emb in _category_embeddings.items():
            similarity = cosine_similarity([text_emb], [cat_emb])[0][0]
            if similarity > best_score:
                best_score = similarity
                best_category = category
        
        return best_category, float(best_score)
    except:
        return 'other', 0.0

def analyze_sentiment(text: str) -> Dict[str, Any]:
    positive_count = sum(1 for word in SENTIMENT_POSITIVE if word in text)
    negative_count = sum(1 for word in SENTIMENT_NEGATIVE if word in text)
    
    total = positive_count + negative_count
    if total == 0:
        sentiment = 'neutral'
        score = 0.5
    else:
        score = positive_count / total
        if score > 0.6:
            sentiment = 'positive'
        elif score < 0.4:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
    
    return {
        'sentiment': sentiment,
        'positive_score': round(score, 3),
        'negative_score': round(1 - score, 3),
        'positive_words': positive_count,
        'negative_words': negative_count
    }

def identify_themes(text: str) -> List[Tuple[str, float]]:
    themes = []
    
    for theme, keywords in THEME_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            score = min(count / len(keywords) * 2, 1.0)
            themes.append((theme, round(score, 3)))
    
    themes.sort(key=lambda x: x[1], reverse=True)
    return themes[:3]

def assess_quality(quote: Dict[str, str]) -> Dict[str, Any]:
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    scores = {}
    
    length = len(text)
    if 6 <= length <= 12:
        scores['length'] = 1.0
    elif 4 <= length <= 15:
        scores['length'] = 0.8
    else:
        scores['length'] = 0.3
    
    high_quality_patterns = sum(1 for p in QUALITY_INDICATORS['high']['patterns'] if p in text)
    high_quality_keywords = sum(1 for kw in QUALITY_INDICATORS['high']['keywords'] if kw in text)
    scores['literary'] = min((high_quality_patterns + high_quality_keywords) * 0.2, 1.0)
    
    has_author = len(author) > 0 and author not in ['佚名', '未知', '匿名']
    scores['attribution'] = 1.0 if has_author else 0.3
    
    sentiment = analyze_sentiment(text)
    if sentiment['sentiment'] == 'positive':
        scores['sentiment'] = 0.9
    elif sentiment['sentiment'] == 'neutral':
        scores['sentiment'] = 0.7
    else:
        scores['sentiment'] = 0.4
    
    themes = identify_themes(text)
    scores['depth'] = min(len(themes) * 0.3, 1.0)
    
    weights = {
        'length': 0.15,
        'literary': 0.25,
        'attribution': 0.15,
        'sentiment': 0.25,
        'depth': 0.20
    }
    
    total_score = sum(scores[k] * weights[k] for k in weights)
    
    return {
        'total_score': round(total_score, 3),
        'breakdown': {k: round(v, 3) for k, v in scores.items()},
        'grade': 'A' if total_score > 0.8 else 'B' if total_score > 0.6 else 'C' if total_score > 0.4 else 'D'
    }

def nlp_analyze_quote(quote: Dict[str, str]) -> Dict[str, Any]:
    if not USE_NLP or not MODEL_LOADED:
        return {
            'nlp_available': False,
            'category': 'other',
            'category_confidence': 0.0,
            'sentiment': 'neutral',
            'themes': [],
            'quality': {'total_score': 0, 'grade': 'D'}
        }
    
    text = quote.get('text', '')
    
    category, cat_confidence = smart_categorize_quote(quote)
    
    sentiment_result = analyze_sentiment(text)
    
    themes = identify_themes(text)
    
    quality_result = assess_quality(quote)
    
    return {
        'nlp_available': True,
        'category': category,
        'category_confidence': round(cat_confidence, 3),
        'sentiment': sentiment_result['sentiment'],
        'sentiment_scores': {
            'positive': sentiment_result['positive_score'],
            'negative': sentiment_result['negative_score']
        },
        'themes': themes,
        'quality': quality_result,
        'embedding_dimension': 1024
    }

def deduplicate_quotes(quotes: List[Dict], threshold: float = 0.85) -> List[Dict]:
    if not USE_NLP or not MODEL_LOADED:
        return quotes
    
    unique_quotes = []
    seen_embeddings = []
    
    for quote in quotes:
        text = quote.get('text', '')
        emb = get_embedding(text)
        
        if emb is None:
            unique_quotes.append(quote)
            continue
        
        is_duplicate = False
        for seen_emb in seen_embeddings:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                sim = cosine_similarity([emb], [seen_emb])[0][0]
                if sim > threshold:
                    is_duplicate = True
                    break
            except:
                pass
        
        if not is_duplicate:
            unique_quotes.append(quote)
            seen_embeddings.append(emb)
    
    return unique_quotes

def filter_quotes_by_quality(quotes: List[Dict], min_grade: str = 'C') -> List[Dict]:
    grade_order = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
    min_level = grade_order.get(min_grade, 2)
    
    filtered = []
    for quote in quotes:
        quality = assess_quality(quote)
        quote_level = grade_order.get(quality['grade'], 1)
        
        if quote_level >= min_level:
            quote['quality_grade'] = quality['grade']
            quote['quality_score'] = quality['total_score']
            filtered.append(quote)
    
    return filtered

def filter_negative_quotes(quotes: List[Dict]) -> tuple:
    positive_quotes = []
    negative_quotes = []
    
    for quote in quotes:
        text = quote.get('text', '')
        sentiment = analyze_sentiment(text)
        
        if sentiment['sentiment'] == 'negative':
            quote['negative_reason'] = f"情感得分: {sentiment['negative_score']:.2f}"
            negative_quotes.append(quote)
        else:
            quote['sentiment'] = sentiment['sentiment']
            quote['sentiment_score'] = sentiment['positive_score']
            positive_quotes.append(quote)
    
    return positive_quotes, negative_quotes

def nlp_score_quote(quote: Dict[str, str]) -> Dict[str, Any]:
    analysis = nlp_analyze_quote(quote)
    
    if not analysis['nlp_available']:
        return {
            'nlp_available': False,
            'total_nlp_score': 0
        }
    
    quality = analysis['quality']
    total_nlp_score = int(quality['total_score'] * 40)
    
    return {
        'nlp_available': True,
        'total_nlp_score': total_nlp_score,
        'quality_grade': quality['grade'],
        'category': analysis['category'],
        'sentiment': analysis['sentiment']
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Enhanced GTE-large-zh NLP System")
    print("=" * 60)
    initialize_nlp()
    
    test_quotes = [
        {'text': '海内存知己，天涯若比邻', 'author': '王勃'},
        {'text': '人生自古谁无死', 'author': '文天祥'},
        {'text': '好好学习天天向上', 'author': '佚名'},
        {'text': '路漫漫其修远兮，吾将上下而求索', 'author': '屈原'},
        {'text': '天下兴亡匹夫有责', 'author': '顾炎武'},
        {'text': '悲伤逆流成河', 'author': '郭敬明'},
        {'text': '愿你出走半生，归来仍是少年', 'author': '佚名'},
    ]
    
    print("\n" + "=" * 60)
    print("Full NLP Analysis Results:")
    print("=" * 60)
    
    for i, quote in enumerate(test_quotes):
        print(f"\n📝 {i+1}. {quote['text']} —— {quote['author']}")
        analysis = nlp_analyze_quote(quote)
        
        print(f"   📂 Category: {analysis['category']} (confidence: {analysis['category_confidence']})")
        print(f"   😊 Sentiment: {analysis['sentiment']} (pos: {analysis['sentiment_scores']['positive']:.2f})")
        print(f"   🏷️  Themes: {', '.join([f'{t[0]}({t[1]})' for t in analysis['themes']])}")
        print(f"   ⭐ Quality: Grade {analysis['quality']['grade']} (score: {analysis['quality']['total_score']:.3f})")
