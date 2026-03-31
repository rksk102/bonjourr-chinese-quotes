import os
import time
import json
import httpx
from typing import Dict, Any, Optional

AIHUBMIX_API_KEY = os.environ.get('AIHUBMIX_API_KEY', '')
AIHUBMIX_MODEL = os.environ.get('AIHUBMIX_MODEL', 'gpt-4o-mini')
AIHUBMIX_BASE_URL = os.environ.get('AIHUBMIX_BASE_URL', 'https://aihubmix.com/v1')
USE_AI_JUDGE = os.environ.get('USE_AI_JUDGE', 'false').lower() == 'true'

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

重要：只返回JSON，不要任何其他文字、解释或markdown标记！"""

SIMPLE_QUOTE_JUDGE_PROMPT = """判断这条语录是否是好的、积极的、值得保留的。

语录："{text}"
作者："{author}"

返回JSON格式：
{{
  "should_keep": true/false,
  "score": 0-100,
  "category": "poetry/philosophy/literature/other"
}}"""


# 全局变量：AI失败计数和自动禁用标志
_ai_fail_count = 0
_ai_disabled = False
MAX_AI_FAILURES = 5

# 全局变量：AI速率限制
_ai_request_times = []
AI_RATE_LIMIT = 2
AI_RATE_LIMIT_PERIOD = 60


def judge_quote_with_ai(quote: Dict[str, str]) -> Optional[Dict[str, Any]]:
    global _ai_fail_count, _ai_disabled, _ai_request_times
    
    if _ai_disabled:
        return None
    
    if not USE_AI_JUDGE or not AIHUBMIX_API_KEY:
        return None
    
    # 速率限制检查
    current_time = time.time()
    # 清理超过周期的请求记录
    _ai_request_times = [t for t in _ai_request_times if current_time - t < AI_RATE_LIMIT_PERIOD]
    
    if len(_ai_request_times) >= AI_RATE_LIMIT:
        oldest_time = _ai_request_times[0]
        wait_time = AI_RATE_LIMIT_PERIOD - (current_time - oldest_time)
        if wait_time > 0:
            print(f"⏳ AI速率限制，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
            # 等待后再次清理
            current_time = time.time()
            _ai_request_times = [t for t in _ai_request_times if current_time - t < AI_RATE_LIMIT_PERIOD]
    
    # 在发起请求之前记录时间，确保严格遵守速率限制
    request_time = time.time()
    _ai_request_times.append(request_time)
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    try:
        headers = {
            "Authorization": f"Bearer {AIHUBMIX_API_KEY}",
            "Content-Type": "application/json"
        }
        
        full_prompt = "你是一位专业的语录鉴赏专家，只返回JSON格式。\n\n" + QUOTE_JUDGE_PROMPT.format(text=text, author=author)
        
        data = {
            "model": AIHUBMIX_MODEL,
            "messages": [
                {"role": "user", "content": full_prompt}
            ]
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AIHUBMIX_BASE_URL}/chat/completions",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print(f"🤖 AI Response: {content}")
                
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    cleaned_content = content.strip()
                    if cleaned_content.startswith('```json'):
                        cleaned_content = cleaned_content[7:]
                    if cleaned_content.startswith('```'):
                        cleaned_content = cleaned_content[3:]
                    if cleaned_content.endswith('```'):
                        cleaned_content = cleaned_content[:-3]
                    cleaned_content = cleaned_content.strip()
                    
                    try:
                        parsed = json.loads(cleaned_content)
                    except json.JSONDecodeError:
                        print(f"⚠️  Failed to parse AI response, using defaults")
                        parsed = {
                            "is_famous": True,
                            "literary_score": 80,
                            "depth_score": 80,
                            "positive_score": 80,
                            "overall_score": 80,
                            "should_keep": True,
                            "reasoning": "默认保留",
                            "category": "philosophy"
                        }
                
                _ai_fail_count = 0
                parsed['ai_judged'] = True
                parsed['model_used'] = AIHUBMIX_MODEL
                return parsed
            else:
                _ai_fail_count += 1
                print(f"⚠️  AIHubMix API error: {response.status_code}")
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
    global _ai_request_times
    
    if not USE_AI_JUDGE or not AIHUBMIX_API_KEY:
        return None
    
    # 速率限制检查
    current_time = time.time()
    # 清理超过周期的请求记录
    _ai_request_times = [t for t in _ai_request_times if current_time - t < AI_RATE_LIMIT_PERIOD]
    
    if len(_ai_request_times) >= AI_RATE_LIMIT:
        oldest_time = _ai_request_times[0]
        wait_time = AI_RATE_LIMIT_PERIOD - (current_time - oldest_time)
        if wait_time > 0:
            print(f"⏳ AI速率限制，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
            # 等待后再次清理
            current_time = time.time()
            _ai_request_times = [t for t in _ai_request_times if current_time - t < AI_RATE_LIMIT_PERIOD]
    
    # 在发起请求之前记录时间，确保严格遵守速率限制
    request_time = time.time()
    _ai_request_times.append(request_time)
    
    text = quote.get('text', '')
    author = quote.get('author', '')
    
    try:
        headers = {
            "Authorization": f"Bearer {AIHUBMIX_API_KEY}",
            "Content-Type": "application/json"
        }
        
        full_prompt = "只返回JSON格式。\n\n" + SIMPLE_QUOTE_JUDGE_PROMPT.format(text=text, author=author)
        
        data = {
            "model": AIHUBMIX_MODEL,
            "messages": [
                {"role": "user", "content": full_prompt}
            ]
        }
        
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f"{AIHUBMIX_BASE_URL}/chat/completions",
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
        'use_openrouter': USE_AI_JUDGE,
        'has_api_key': bool(AIHUBMIX_API_KEY),
        'model': AIHUBMIX_MODEL,
        'base_url': AIHUBMIX_BASE_URL,
        'ai_disabled': _ai_disabled,
        'ai_fail_count': _ai_fail_count
    }


def reset_ai_state():
    global _ai_fail_count, _ai_disabled, _ai_request_times
    _ai_fail_count = 0
    _ai_disabled = False
    _ai_request_times = []


if __name__ == "__main__":
    print("=" * 60)
    print("Testing AIHubMix AI Judge")
    print("=" * 60)
    
    config = get_env_config()
    print(f"\n📋 Configuration:")
    print(f"   USE_AI_JUDGE: {config['use_openrouter']}")
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
        print("\n⚠️  AIHubMix not configured. Set USE_AI_JUDGE=true and AIHUBMIX_API_KEY.")
