"""项目配置，从环境变量读取。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── 大模型 API（智谱优先；未设置时使用 OpenAI 兼容接口）──
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4-flash")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── 定时 ──
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "8"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))

# ── 抓取 ──
MAX_PAPERS_PER_SOURCE = int(os.getenv("MAX_PAPERS_PER_SOURCE", "30"))

# 论文关键词过滤（逗号分隔），只拉取标题/摘要中含这些关键词的论文
# 留空 = 不过滤
PAPER_KEYWORDS = [
    kw.strip()
    for kw in os.getenv("PAPER_KEYWORDS", "LLM,Agent,Memory,RAG,Tool Use,Function Calling,Planning,Reasoning,Multi-Agent,Autonomous").split(",")
    if kw.strip()
]

# 最终精选推送的论文数量
TOP_K_PAPERS = int(os.getenv("TOP_K_PAPERS", "10"))

# 用户画像：LLM 精选论文时参考
USER_PROFILE = os.getenv(
    "USER_PROFILE",
    "工业界 Agent 算法工程师，关注 LLM Agent / 多智能体 / 工具调用 / 记忆机制 / RAG / 推理规划等方向，"
    "偏好来自头部实验室（OpenAI / DeepMind / Meta FAIR / Microsoft Research / 清华 / 北大等）"
    "或有实际落地验证的论文，重视实践价值和可复现性。",
)

# ── 输出 ──
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent / "output"))

# 企业微信群机器人 Webhook（可选，配置后每日报告会推送到该群）
WECOM_WEBHOOK_URL = os.getenv("WECOM_WEBHOOK_URL", "").strip() or None
