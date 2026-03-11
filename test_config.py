"""测试配置"""
import sys
sys.path.insert(0, '.')

from config import *

print("=== AI_Paper_Tracking 配置测试 ===")
print(f"输出模式: {OUTPUT_MODE}")
print(f"关键词: {PAPER_KEYWORDS}")
print(f"精选数量: {TOP_K_PAPERS}")
print(f"输出目录: {OUTPUT_DIR}")
print(f"企业微信Webhook: {'已配置' if WECOM_WEBHOOK_URL else '未配置'}")

if not ZHIPU_API_KEY and not OPENAI_API_KEY:
    print("\n⚠️ 警告: 未配置API密钥，将无法调用LLM功能")
else:
    print("\n✅ API密钥已配置")