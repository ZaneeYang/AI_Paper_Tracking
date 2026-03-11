"""
大模型驱动的论文处理流水线：
1. select_top_papers()  —— 从候选中精选 TOP K
2. enrich_papers()      —— 为每篇提取机构、关键词、一句话总结
3. detailed_analysis()  —— 详细分析每篇论文（背景、动机、创新点、技术难点、不足、展望）
"""
import json
import logging
import re
from typing import List, Optional, Tuple

from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    ZHIPU_API_KEY,
    ZHIPU_BASE_URL,
    ZHIPU_MODEL,
    USER_PROFILE,
)
from sources.base import Paper

logger = logging.getLogger(__name__)


def _get_client() -> Optional[Tuple[OpenAI, str]]:
    """返回 (client, model) 或 None。"""
    if ZHIPU_API_KEY:
        return OpenAI(api_key=ZHIPU_API_KEY, base_url=ZHIPU_BASE_URL), ZHIPU_MODEL
    if OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL), OPENAI_MODEL
    return None


# ─────────────────── 1. 精选 TOP K ───────────────────


def select_top_papers(papers: List[Paper], top_k: int = 10) -> List[Paper]:
    """
    让大模型从候选列表中精选出 top_k 篇最值得关注的论文。
    评估维度：与用户画像的相关性、作者/机构可信度、实践价值。
    """
    if len(papers) <= top_k:
        return papers

    result = _get_client()
    if result is None:
        logger.warning("未配置 API Key，按默认顺序取前 %d 篇", top_k)
        return papers[:top_k]

    client, model = result

    papers_text = "\n".join(
        f"[{i}] 标题: {p.title}\n    作者: {p.authors or '未知'}\n    摘要: {p.summary[:300]}"
        for i, p in enumerate(papers)
    )

    prompt = f"""你是一位资深 AI 论文审稿人。以下是今日拉取的 {len(papers)} 篇 AI 论文候选列表。

用户画像：{USER_PROFILE}

请从中精选出 {top_k} 篇对该用户**最值得阅读**的论文。评判标准（按优先级）：
1. **相关性**：与用户关注方向（Agent / LLM / Memory / RAG / 工具调用 / 规划推理等）的匹配度
2. **可信度**：作者来自知名机构或本身是该领域知名研究者
3. **实践价值**：有实际系统/框架/工具落地，或提出了可直接应用于工业界的方法

请只返回一个 JSON 数组，包含你选出论文的编号（从 0 开始的索引），按推荐优先级排列。
例如：[3, 0, 7, 12, ...]
不要输出任何其他内容，只输出 JSON 数组。

候选论文：
{papers_text}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是论文推荐专家，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
        )
        raw = (response.choices[0].message.content or "").strip()
        match = re.search(r"\[[\d\s,]+\]", raw)
        if match:
            indices = json.loads(match.group())
            selected = []
            seen = set()
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(papers) and idx not in seen:
                    selected.append(papers[idx])
                    seen.add(idx)
                if len(selected) >= top_k:
                    break
            if selected:
                logger.info("LLM 精选出 %d 篇论文", len(selected))
                return selected

        logger.warning("LLM 精选返回格式异常: %s，退回默认", raw[:200])
    except Exception as e:
        logger.warning("LLM 精选调用失败: %s，退回默认", e)

    return papers[:top_k]


# ─────────────────── 2. 丰富每篇论文信息 ───────────────────


def enrich_papers(papers: List[Paper]) -> List[Paper]:
    """
    让大模型为每篇论文提取：
    - institution: 作者所属机构（简短，如 "Stanford / Google"）
    - keywords_tags: 2～3 个关键词标签（如 "Agent / Planning"）
    - one_line_summary: 一句话中文总结（20～40 字）
    若 LLM 调用失败，用简易规则填充。
    """
    result = _get_client()
    if result is None:
        logger.warning("未配置 API Key，使用简易规则丰富论文信息")
        return _fallback_enrich(papers)

    client, model = result

    papers_input = []
    for i, p in enumerate(papers):
        papers_input.append(
            f"[{i}]\n标题: {p.title}\n作者: {p.authors or '未知'}\n摘要: {p.summary[:400]}"
        )

    prompt = f"""以下是 {len(papers)} 篇精选 AI 论文。请为每篇提取以下信息：

1. **institution**: 作者所属的主要机构。要求：
   - 根据作者姓名、论文标题、论文内容综合推断
   - 很多 AI 论文来自知名机构（OpenAI, Google DeepMind, Meta, Microsoft Research, Anthropic, Stanford, MIT, CMU, 清华, 北大, 阿里巴巴, 字节跳动等），请积极识别
   - 如果论文标题中包含产品/项目名（如 AgentScope→阿里巴巴, Mem0→Mem0.ai, LightRAG 等），请根据你的知识推断其背后机构
   - 简短表述，如 "Stanford" / "OpenAI / Microsoft"
   - 只有在完全无法推断时才写 "Unknown"

2. **keywords**: 2～3 个最核心的关键词标签，用 " / " 分隔（如 "Agent / Planning / LLM"）

3. **summary**: 中文总结，约 50 字，重点突出论文的**创新点**和**核心方法**，说清楚"做了什么、怎么做的、效果如何"

请返回一个 JSON 数组，每个元素包含 index、institution、keywords、summary 四个字段。
例如：
[
  {{"index": 0, "institution": "Stanford", "keywords": "Agent / Planning", "summary": "提出基于层次化目标分解的 Agent 规划框架，通过将复杂任务拆解为可验证的子目标链，在 WebArena 等基准上比现有方法提升 15% 成功率。"}},
  ...
]
只返回 JSON，不要输出其他内容。

论文列表：
{chr(10).join(papers_input)}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 AI 论文分析专家，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
        )
        raw = (response.choices[0].message.content or "").strip()
        # 提取 JSON 数组
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            arr = json.loads(raw[start:end + 1])
            enriched_map = {}
            for item in arr:
                if isinstance(item, dict) and "index" in item:
                    enriched_map[item["index"]] = item

            for i, p in enumerate(papers):
                info = enriched_map.get(i, {})
                p.institution = info.get("institution") or _guess_institution(p)
                p.keywords_tags = info.get("keywords") or "AI"
                p.one_line_summary = info.get("summary") or p.summary[:60]

            logger.info("LLM 成功丰富 %d 篇论文信息", len(papers))
            return papers

        logger.warning("LLM enrich 返回格式异常，退回简易规则")
    except Exception as e:
        logger.warning("LLM enrich 调用失败: %s，退回简易规则", e)

    return _fallback_enrich(papers)


def _fallback_enrich(papers: List[Paper]) -> List[Paper]:
    """无 LLM 时的简易填充。"""
    for p in papers:
        p.institution = _guess_institution(p)
        p.keywords_tags = "AI"
        p.one_line_summary = p.summary[:80] + ("…" if len(p.summary) > 80 else "")
    return papers


def _guess_institution(p: Paper) -> str:
    """从作者字符串中猜测机构（非常粗糙，仅作兜底）。"""
    if not p.authors:
        return "Unknown"
    # 简单启发式：取第一作者姓氏
    first = p.authors.split(",")[0].strip()
    return first.split()[-1] if first else "Unknown"


# ─────────────────── 3. 详细分析每篇论文 ───────────────────


def detailed_analysis(papers: List[Paper]) -> List[Paper]:
    """
    为每篇论文生成详细分析，包括：
    - 背景
    - 动机  
    - 创新点
    - 技术难点
    - 不足/待解决
    - 展望/应用
    
    若 LLM 调用失败，返回空分析。
    """
    result = _get_client()
    if result is None:
        logger.warning("未配置 API Key，跳过详细分析")
        for p in papers:
            p.detailed_analysis = {
                "background": "未进行分析",
                "motivation": "未进行分析",
                "innovation": "未进行分析",
                "challenge": "未进行分析",
                "limitation": "未进行分析",
                "future": "未进行分析"
            }
        return papers

    client, model = result

    papers_input = []
    for i, p in enumerate(papers):
        papers_input.append(
            f"[{i}]\n标题: {p.title}\n作者: {p.authors or '未知'}\n机构: {p.institution or '未知'}\n摘要: {p.summary}"
        )

    prompt = f"""以下是 {len(papers)} 篇精选 AI 论文。请为每篇论文生成详细分析，包含以下6个维度：

1. **背景** (Background): 该研究领域的基本情况、现有方法的主要问题
2. **动机** (Motivation): 作者为什么要做这项研究？解决了什么痛点？
3. **创新点** (Innovation): 本文的核心创新是什么？方法上有何独特之处？
4. **技术难点** (Technical Challenges): 实现该方法的主要技术挑战是什么？
5. **不足/待解决** (Limitations): 论文中提到的局限性或未来需要解决的问题
6. **展望/应用** (Future/Applications): 该研究的未来发展方向和潜在应用场景

要求：
- 每个维度用1-2句话简明扼要说明
- 语言为中文，专业但易懂
- 基于论文内容进行合理推断

请返回一个 JSON 数组，每个元素包含 index 和6个分析字段：
[
  {{
    "index": 0,
    "background": "...",
    "motivation": "...", 
    "innovation": "...",
    "challenge": "...",
    "limitation": "...",
    "future": "..."
  }},
  ...
]
只返回 JSON，不要输出其他内容。

论文列表：
{chr(10).join(papers_input)}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 AI 论文分析专家，请为每篇论文提供详细分析，只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=4000,
        )
        raw = (response.choices[0].message.content or "").strip()
        # 提取 JSON 数组
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            arr = json.loads(raw[start:end + 1])
            analysis_map = {}
            for item in arr:
                if isinstance(item, dict) and "index" in item:
                    analysis_map[item["index"]] = {
                        "background": item.get("background", "未提供"),
                        "motivation": item.get("motivation", "未提供"),
                        "innovation": item.get("innovation", "未提供"),
                        "challenge": item.get("challenge", "未提供"),
                        "limitation": item.get("limitation", "未提供"),
                        "future": item.get("future", "未提供")
                    }

            for i, p in enumerate(papers):
                p.detailed_analysis = analysis_map.get(i, {
                    "background": "分析失败",
                    "motivation": "分析失败",
                    "innovation": "分析失败",
                    "challenge": "分析失败",
                    "limitation": "分析失败",
                    "future": "分析失败"
                })

            logger.info("LLM 成功完成 %d 篇论文详细分析", len(papers))
            return papers

        logger.warning("LLM detailed_analysis 返回格式异常，跳过详细分析")
    except Exception as e:
        logger.warning("LLM detailed_analysis 调用失败: %s，跳过详细分析", e)

    # 失败时的兜底
    for p in papers:
        p.detailed_analysis = {
            "background": "分析失败",
            "motivation": "分析失败",
            "innovation": "分析失败",
            "challenge": "分析失败",
            "limitation": "分析失败",
            "future": "分析失败"
        }
    return papers
