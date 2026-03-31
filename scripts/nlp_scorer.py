import os
import sys
from typing import Dict, Any, Optional

USE_NLP = os.environ.get('USE_NLP', 'false').lower() == 'true'
MODEL_LOADED = False
embedder = None


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
        
        MODEL_LOADED = True
        print("✅ GTE-large-zh model loaded successfully!")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not load NLP models: {e}")
        print("💡 Falling back to rule-based scoring only.")
        return False


def get_embedding(text: str) -> Optional[Any]:
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
        import numpy as np
        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return float(similarity)
    except:
        return 0.0


def deduplicate_quotes(quotes, threshold=0.85):
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


def nlp_score_quote(quote: Dict[str, str]) -> Dict[str, Any]:
    if not USE_NLP or not MODEL_LOADED:
        return {
            'nlp_available': False,
            'semantic_quality_score': 0,
            'total_nlp_score': 0
        }
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    text_length = len(text)
    length_score = 0.0
    if 6 <= text_length <= 12:
        length_score = 1.0
    elif 4 <= text_length <= 15:
        length_score = 0.8
    elif text_length < 4 or text_length > 15:
        length_score = 0.3
    
    has_punctuation = any(p in text for p in ['，', '。', '？', '！', '；', '：'])
    punctuation_score = 0.8 if has_punctuation else 0.3
    
    has_author = len(author) > 0 and author != '佚名'
    author_score = 0.6 if has_author else 0.3
    
    quality_score = (
        length_score * 0.4 +
        punctuation_score * 0.35 +
        author_score * 0.25
    )
    
    total_nlp_score = int(quality_score * 40)
    
    return {
        'nlp_available': True,
        'quality_score': round(quality_score, 3),
        'length_score': round(length_score, 3),
        'punctuation_score': round(punctuation_score, 3),
        'author_score': round(author_score, 3),
        'total_nlp_score': total_nlp_score
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Testing GTE-large-zh NLP scorer...")
    print("=" * 60)
    initialize_nlp()
    
    test_quotes = [
        {'text': '海内存知己，天涯若比邻', 'author': '王勃'},
        {'text': '人生自古谁无死', 'author': '文天祥'},
        {'text': '好好学习天天向上', 'author': '佚名'},
        {'text': '路漫漫其修远兮', 'author': '屈原'},
        {'text': '天下兴亡匹夫有责', 'author': '顾炎武'},
    ]
    
    print("\n" + "=" * 60)
    print("Testing semantic similarity (deduplication):")
    print("=" * 60)
    
    for i, quote in enumerate(test_quotes):
        print(f"\n📝 {i+1}. {quote['text']} —— {quote['author']}")
        score = nlp_score_quote(quote)
        print(f"   NLP Score: {score}")
    
    if len(test_quotes) >= 2:
        print("\n" + "=" * 60)
        print("Semantic Similarity Matrix:")
        print("=" * 60)
        for i in range(len(test_quotes)):
            for j in range(i+1, len(test_quotes)):
                sim = calculate_semantic_similarity(test_quotes[i]['text'], test_quotes[j]['text'])
                print(f"{test_quotes[i]['text'][:6]}... <-> {test_quotes[j]['text'][:6]}... : {sim:.3f}")
