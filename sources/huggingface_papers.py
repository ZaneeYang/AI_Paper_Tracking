"""从 Hugging Face Papers 拉取前一天论文，支持关键词过滤。"""
import logging
import re
from datetime import date, timedelta
from typing import List, Optional

import requests

from .base import Paper

logger = logging.getLogger(__name__)

HF_PAPERS_SEARCH = "https://huggingface.co/api/papers/search"


def fetch_huggingface_trending_papers(
    limit: int = 30,
    keywords: Optional[List[str]] = None,
) -> List[Paper]:
    """
    从 Hugging Face 拉取前一天的论文。
    先尝试 API，失败再爬取 trending 页面。
    keywords 不为空时只保留标题/摘要含关键词的论文。
    """
    papers: List[Paper] = []
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    try:
        r = requests.get(
            HF_PAPERS_SEARCH,
            params={"date": yesterday, "limit": limit * 3},
            timeout=15,
            headers={"User-Agent": "AI-Paper-Tracking/1.0"},
        )
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "papers" in data:
            items = data["papers"]
        elif isinstance(data, dict) and "data" in data:
            items = data["data"]
        else:
            items = data if isinstance(data, list) else []

        for item in items:
            if len(papers) >= limit:
                break
            if isinstance(item, dict):
                paper = _item_to_paper(item, yesterday)
                if paper and _matches_keywords(paper, keywords):
                    papers.append(paper)
    except requests.RequestException as e:
        logger.warning("Hugging Face API 请求失败，尝试爬取 trending 页面: %s", e)
        papers = _scrape_trending_fallback(limit, keywords)

    # 对缺少作者的论文，通过 arXiv ID 回查补全
    _backfill_authors_from_arxiv(papers)
    return papers[:limit]


def _matches_keywords(paper: Paper, keywords: Optional[List[str]]) -> bool:
    """关键词过滤。keywords 为空时全部通过。"""
    if not keywords:
        return True
    text = (paper.title + " " + paper.summary).lower()
    return any(kw.lower() in text for kw in keywords)


def _item_to_paper(item: dict, default_date: str) -> Paper | None:
    """将 API 返回的一条记录转为 Paper。"""
    title = item.get("title") or item.get("name") or ""
    if not title:
        return None
    summary = item.get("summary") or item.get("description") or item.get("abstract") or ""
    url = item.get("url") or item.get("link") or ""
    if url and not url.startswith("http"):
        url = f"https://huggingface.co{url}"
    arxiv_id = item.get("arxiv_id") or item.get("arxivId")

    # 作者：可能是列表或字符串
    authors = item.get("authors")
    if isinstance(authors, list):
        # 每个元素可能是 str 或 dict
        names = []
        for a in authors[:10]:
            if isinstance(a, str):
                names.append(a)
            elif isinstance(a, dict):
                names.append(a.get("name") or a.get("user", ""))
        authors = ", ".join(n for n in names if n)
    elif not isinstance(authors, str):
        authors = None

    published = item.get("published") or item.get("date") or default_date
    return Paper(
        title=title,
        summary=summary or "(无摘要)",
        source="huggingface",
        url=url or "https://huggingface.co/papers",
        arxiv_id=arxiv_id,
        authors=authors or None,
        published=published,
    )


def _scrape_trending_fallback(
    limit: int, keywords: Optional[List[str]] = None,
) -> List[Paper]:
    """当 API 不可用时，爬取 trending 页面。"""
    from bs4 import BeautifulSoup

    papers = []
    try:
        r = requests.get(
            "https://huggingface.co/papers/trending",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("[data-testid='paper-card'], article, .paper-card"):
            if len(papers) >= limit:
                break
            title_el = card.select_one("h2, h3, .title, [class*='title']")
            desc_el = card.select_one("p, .summary, [class*='summary'], [class*='description']")
            link_el = card.select_one("a[href*='/papers/']")
            if title_el and link_el:
                href = link_el.get("href", "")
                url = href if href.startswith("http") else f"https://huggingface.co{href}"
                arxiv_id = _extract_arxiv_id_from_url(url)
                p = Paper(
                    title=title_el.get_text(strip=True),
                    summary=desc_el.get_text(strip=True) if desc_el else "",
                    source="huggingface",
                    url=url,
                    arxiv_id=arxiv_id,
                )
                if _matches_keywords(p, keywords):
                    papers.append(p)
    except Exception as e:
        logger.warning("Hugging Face trending 页面爬取失败: %s", e)
    return papers


def _extract_arxiv_id_from_url(url: str) -> Optional[str]:
    """从 HuggingFace 论文 URL 中提取 arXiv ID（如 2504.19413）。"""
    m = re.search(r"/papers/(\d{4}\.\d{4,5})", url)
    return m.group(1) if m else None


def _backfill_authors_from_arxiv(papers: List[Paper]) -> None:
    """对缺少作者的论文，批量用 arXiv API 回查补全作者信息。"""
    need_backfill = [p for p in papers if not p.authors and p.arxiv_id]
    if not need_backfill:
        return

    logger.info("正在为 %d 篇 HF 论文从 arXiv 回查作者...", len(need_backfill))
    try:
        import arxiv as arxiv_lib
        client = arxiv_lib.Client()
        ids = [p.arxiv_id for p in need_backfill]
        search = arxiv_lib.Search(id_list=ids)
        results_map = {}
        for result in client.results(search):
            short_id = result.get_short_id()
            # arXiv short_id 可能带版本号如 "2504.19413v1"，去掉
            base_id = re.sub(r"v\d+$", "", short_id)
            results_map[base_id] = result

        filled = 0
        for p in need_backfill:
            result = results_map.get(p.arxiv_id)
            if result and result.authors:
                p.authors = ", ".join(a.name for a in result.authors[:10])
                if not p.summary or p.summary == "(无摘要)":
                    p.summary = (result.summary or "").replace("\n", " ").strip()
                filled += 1
        logger.info("arXiv 回查补全了 %d 篇论文的作者", filled)
    except Exception as e:
        logger.warning("arXiv 回查作者失败: %s", e)
