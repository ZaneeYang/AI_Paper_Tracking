"""
每日任务入口：
  拉取（关键词过滤）→ LLM 精选 TOP K → LLM 丰富信息 → 格式化 → 保存 → 企业微信推送
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    MAX_PAPERS_PER_SOURCE,
    OUTPUT_DIR,
    PAPER_KEYWORDS,
    TOP_K_PAPERS,
    WECOM_WEBHOOK_URL,
)
from formatter import format_daily_report, format_wecom_messages, save_report
from sources import fetch_huggingface_trending_papers, fetch_arxiv_recent_papers
from summarizer import select_top_papers, enrich_papers
from wecom import send_markdown_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run(output_format: str = "markdown", save_to_file: bool = True) -> str:
    limit = MAX_PAPERS_PER_SOURCE
    keywords = PAPER_KEYWORDS or None
    all_papers = []

    # ── 1. 拉取（带关键词过滤）──
    try:
        hf = fetch_huggingface_trending_papers(limit=limit, keywords=keywords)
        all_papers.extend(hf)
        logger.info("Hugging Face 拉取 %d 篇（关键词过滤后）", len(hf))
    except Exception as e:
        logger.warning("Hugging Face 拉取异常: %s", e)

    try:
        ax = fetch_arxiv_recent_papers(limit=limit, keywords=keywords)
        all_papers.extend(ax)
        logger.info("arXiv 拉取 %d 篇（关键词过滤后）", len(ax))
    except Exception as e:
        logger.warning("arXiv 拉取异常: %s", e)

    # 去重（按标题）
    seen_titles = set()
    unique_papers = []
    for p in all_papers:
        key = p.title.strip().lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_papers.append(p)
    logger.info("去重后共 %d 篇候选论文", len(unique_papers))

    if not unique_papers:
        logger.warning("未拉取到任何论文")
        return "# 今日热门 Paper 快讯\n\n今日暂无匹配关键词的论文，请检查网络或调整关键词。"

    # ── 2. LLM 精选 TOP K ──
    selected = select_top_papers(unique_papers, top_k=TOP_K_PAPERS)
    logger.info("精选出 %d 篇论文", len(selected))

    # ── 3. LLM 丰富每篇信息（机构 / 关键词 / 一句话总结）──
    enriched = enrich_papers(selected)

    # ── 4. 格式化 ──
    report = format_daily_report(enriched, output_format=output_format)

    # 保存完整版
    if save_to_file:
        path = save_report(report, OUTPUT_DIR)
        logger.info("报告已保存: %s", path)

    # ── 5. 企业微信推送 ──
    if WECOM_WEBHOOK_URL and enriched:
        messages = format_wecom_messages(enriched)
        logger.info("企业微信共 %d 条消息待推送", len(messages))
        send_markdown_messages(WECOM_WEBHOOK_URL, messages)

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="今日热门 Paper 快讯")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--no-save", action="store_true", help="不写入文件，仅打印")
    args = parser.parse_args()
    result = run(output_format=args.format, save_to_file=not args.no_save)
    print(result)
