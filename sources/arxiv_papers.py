"""从 arXiv 拉取前一天发布的 AI/ML 论文，支持关键词过滤。"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import arxiv

from .base import Paper

logger = logging.getLogger(__name__)

ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]


def fetch_arxiv_recent_papers(
    limit: int = 30,
    keywords: Optional[List[str]] = None,
) -> List[Paper]:
    """
    拉取 arXiv 上前一天发布的 AI/ML 论文。
    - 按提交时间降序排列，只保留 published 日期为昨天的论文。
    - keywords 不为空时，用关键词构建查询 + 本地二次过滤。
    - 作者信息完整保留（最多 10 人）。
    """
    yesterday = date.today() - timedelta(days=1)
    papers: List[Paper] = []
    try:
        client = arxiv.Client()
        query = _build_query(keywords)
        fetch_count = limit * 5 if keywords else limit * 3
        search = arxiv.Search(
            query=query,
            max_results=fetch_count,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        skipped_newer = 0
        skipped_older = 0
        for result in client.results(search):
            if len(papers) >= limit:
                break

            pub_date = result.published.date() if result.published else None
            if pub_date is None:
                continue
            if pub_date > yesterday:
                skipped_newer += 1
                continue
            if pub_date < yesterday:
                skipped_older += 1
                if skipped_older > 20:
                    break
                continue

            title = result.title or ""
            abstract = (result.summary or "").replace("\n", " ").strip()

            if keywords and not _matches_keywords(title, abstract, keywords):
                continue

            authors_str = ", ".join(a.name for a in (result.authors or [])[:10])
            published_str = pub_date.isoformat()
            papers.append(
                Paper(
                    title=title,
                    summary=abstract,
                    source="arxiv",
                    url=result.entry_id or "https://arxiv.org/",
                    arxiv_id=result.get_short_id() if result.entry_id else None,
                    authors=authors_str or None,
                    published=published_str,
                )
            )
    except Exception as e:
        logger.warning("arXiv 拉取失败: %s", e)

    logger.info("arXiv 前一天（%s）共匹配 %d 篇", yesterday.isoformat(), len(papers))
    return papers


def _build_query(keywords: Optional[List[str]] = None) -> str:
    """构建 arXiv 查询字符串，将分类和关键词结合。"""
    cat_part = " OR ".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    if not keywords:
        return cat_part
    kw_clauses = " OR ".join(
        f'ti:"{kw}" OR abs:"{kw}"' for kw in keywords
    )
    return f"({cat_part}) AND ({kw_clauses})"


def _matches_keywords(title: str, abstract: str, keywords: List[str]) -> bool:
    """本地二次过滤：标题或摘要中是否含任一关键词（大小写不敏感）。"""
    text = (title + " " + abstract).lower()
    return any(kw.lower() in text for kw in keywords)
