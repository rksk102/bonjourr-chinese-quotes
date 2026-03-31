import os
import json
import httpx
from typing import Dict, Any, Optional

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
OPENROUTER_BASE_URL = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
USE_OPENROUTER = os.environ.get('USE_AI_JUDGE', 'false').lower() == 'true'

# 全局变量：AI失败计数和自动禁用标志
_ai_fail_count = 0
_ai_disabled = False
MAX_AI_FAILURES = 5

QUOTE_JUDGE_PROMPT = """你是一位专业的中国文化和语录鉴赏专家。请判断以下语录的质量，并给出评分和评价。

语录内容："{text}"
作者："{author}"

请从以下几个维度评价：
1. 是否是知名的名言名句或经典诗词？
2. 语录的文学性和文采如何？
3. 语录的思想深度和哲理内涵如何？
4. 语录是否积极向上，适合作为每日语录展示？
5. 整体质量如何？

请以JSON格式返回，格式如下：
{{
  "is_famous": true/false,
  "literary_score": 0-100,
  "depth_score": 0-100,
  "positive_score": 0-100,
  "overall_score": 0-100,
  "should_keep": true/false,
  "reasoning": "简短的评价理由（50字以内）",
  "category": "poetry/philosophy/literature/other"
}}

要求：
- is_famous: 如果是知名名言或经典诗词则为true
- literary_score: 文学性得分
- depth_score: 思想深度得分
- positive_score: 积极向上程度得分
- overall_score: 综合得分（0-100）
- should_keep: 是否应该保留这条语录
- reasoning: 简短的评价理由
- category: 分类（poetry=诗词, philosophy=哲理, literature=文学, other=其他）

只返回JSON，不要其他文字！"""

SIMPLE_QUOTE_JUDGE_PROMPT = """判断这条语录是否是好的、积极的、值得保留的。

语录："{text}"
作者："{author}"

返回JSON格式：
{{
  "should_keep": true/false,
  "score": 0-100,
  "category": "poetry/philosophy/literature/other"
}}"""


def judge_quote_with_ai(quote: Dict[str, str]) -> Optional[Dict[str, Any]]:
    global _ai_fail_count, _ai_disabled
    
    if _ai_disabled:
        return None
    
    if not USE_OPENROUTER or not OPENROUTER_API_KEY:
        return None
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Bonjourr Chinese Quotes",
            "Content-Type": "application/json"
        }
        
        prompt = QUOTE_JUDGE_PROMPT.format(text=text, author=author)
        
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "你是一位专业的语录鉴赏专家，只返回JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                parsed = json.loads(content)
                
                _ai_fail_count = 0
                parsed['ai_judged'] = True
                parsed['model_used'] = OPENROUTER_MODEL
                return parsed
            else:
                _ai_fail_count += 1
                print(f"⚠️  OpenRouter API error: {response.status_code}")
                print(f"Response: {response.text}")
                print(f"   Failure count: {_ai_fail_count}/{MAX_AI_FAILURES}")
                
                if _ai_fail_count >= MAX_AI_FAILURES:
                    _ai_disabled = True
                    print(f"⚠️  AI judge disabled after {_ai_fail_count} failures")
                return None
                
    except Exception as e:
        _ai_fail_count += 1
        print(f"⚠️  AI judge failed: {e}")
        print(f"   Failure count: {_ai_fail_count}/{MAX_AI_FAILURES}")
        
        if _ai_fail_count >= MAX_AI_FAILURES:
            _ai_disabled = True
            print(f"⚠️  AI judge disabled after {_ai_fail_count} failures")
        return None


def quick_judge_with_ai(quote: Dict[str, str]) -> Optional[Dict[str, Any]]:
    if not USE_OPENROUTER or not OPENROUTER_API_KEY:
        return None
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com",
            "X-Title": "Bonjourr Chinese Quotes",
            "Content-Type": "application/json"
        }
        
        prompt = SIMPLE_QUOTE_JUDGE_PROMPT.format(text=text, author=author)
        
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "只返回JSON格式。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 200,
            "response_format": {"type": "json_object"}
        }
        
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                parsed = json.loads(content)
                parsed['ai_judged'] = True
                return parsed
            else:
                return None
                
    except Exception as e:
        print(f"⚠️  Quick AI judge failed: {e}")
        return None


def get_env_config() -> Dict[str, Any]:
    return {
        'use_openrouter': USE_OPENROUTER,
        'has_api_key': bool(OPENROUTER_API_KEY),
        'model': OPENROUTER_MODEL,
        'base_url': OPENROUTER_BASE_URL,
        'ai_disabled': _ai_disabled,
        'ai_fail_count': _ai_fail_count
    }

def reset_ai_state():
    global _ai_fail_count, _ai_disabled
    _ai_fail_count = 0
    _ai_disabled = False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing OpenRouter AI Judge")
    print("=" * 60)
    
    config = get_env_config()
    print(f"\n📋 Configuration:")
    print(f"   USE_OPENROUTER: {config['use_openrouter']}")
    print(f"   Has API Key: {config['has_api_key']}")
    print(f"   Model: {config['model']}")
    
    test_quotes = [
        {'text': '臣鞠躬尽瘁，死而后已', 'author': '诸葛亮'},
        {'text': '人生自古谁无死', 'author': '文天祥'},
        {'text': '好好学习天天向上', 'author': '佚名'},
    ]
    
    if config['use_openrouter'] and config['has_api_key']:
        print("\n🤖 Testing AI judge...")
        for quote in test_quotes:
            print(f"\n📝 Testing: {quote['text']}")
            result = judge_quote_with_ai(quote)
            if result:
                print(f"   Should keep: {result.get('should_keep')}")
                print(f"   Overall score: {result.get('overall_score')}")
                print(f"   Category: {result.get('category')}")
                print(f"   Reasoning: {result.get('reasoning')}")
    else:
        print("\n⚠️  OpenRouter not configured. Set USE_OPENROUTER=true and OPENROUTER_API_KEY.")
