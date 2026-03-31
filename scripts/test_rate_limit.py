#!/usr/bin/env python3
import time
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_judge import (
    judge_quote_with_ai, 
    reset_ai_state,
    AI_RATE_LIMIT,
    AI_RATE_LIMIT_PERIOD
)

def test_rate_limit():
    print("=" * 70)
    print("测试AI速率限制")
    print(f"限制: {AI_RATE_LIMIT}次 / {AI_RATE_LIMIT_PERIOD}秒")
    print("=" * 70)
    
    # 重置状态
    reset_ai_state()
    
    test_quotes = [
        {'text': '臣鞠躬尽瘁，死而后已', 'author': '诸葛亮'},
        {'text': '人生自古谁无死', 'author': '文天祥'},
        {'text': '好好学习天天向上', 'author': '佚名'},
        {'text': '路漫漫其修远兮', 'author': '屈原'},
    ]
    
    print(f"\n📝 准备测试 {len(test_quotes)} 条语录...\n")
    
    start_time = time.time()
    
    for i, quote in enumerate(test_quotes):
        print(f"\n[{i+1}/{len(test_quotes)}] 开始评估: {quote['text']}")
        quote_start = time.time()
        
        result = judge_quote_with_ai(quote)
        
        quote_end = time.time()
        elapsed = quote_end - quote_start
        
        if result:
            print(f"  ✅ 评估成功 (耗时 {elapsed:.2f}秒)")
            print(f"  📊 结果: should_keep={result.get('should_keep')}, score={result.get('overall_score', 'N/A')}")
        else:
            print(f"  ❌ 评估失败 (耗时 {elapsed:.2f}秒)")
    
    total_elapsed = time.time() - start_time
    print(f"\n{'=' * 70}")
    print(f"测试完成！总耗时: {total_elapsed:.2f}秒")
    print(f"{'=' * 70}")

if __name__ == "__main__":
    test_rate_limit()
