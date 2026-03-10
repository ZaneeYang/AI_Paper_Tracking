"""将精选论文格式化为指定模板的消息（Markdown / JSON / 企业微信多条）。"""
import json
from datetime import date
from pathlib import Path
from typing import List

from sources.base import Paper

DEFAULT_FORMAT = "markdown"
_WECOM_MAX_BYTES = 4096


# ─────────────────── 单篇论文格式化（核心模板）───────────────────


def _paper_entry(i: int, p: Paper) -> str:
    """
    按模板格式化单篇论文：
      1、[论文标题](链接)
        **机构**：xxx
        **关键词**：xxx / xxx
        **总结**：一句话中文总结
    """
    lines = [f"{i}、[{p.title}]({p.url})"]
    if p.institution and p.institution != "Unknown":
        lines.append(f"  **机构**：{p.institution}")
    lines.append(f"  **关键词**：{p.keywords_tags or 'AI'}")
    lines.append(f"  **总结**：{p.one_line_summary or p.summary[:80]}")
    return "\n".join(lines)


# ─────────────────── 完整版报告（本地保存）───────────────────


def format_daily_report(
    papers: List[Paper],
    output_format: str = DEFAULT_FORMAT,
) -> str:
    today = date.today().isoformat()
    if output_format == "json":
        return _to_json(today, papers)
    return _to_markdown(today, papers)


def _to_markdown(today: str, papers: List[Paper]) -> str:
    lines = [f"# 今日热门 Paper 快讯 · {today}", ""]
    for i, p in enumerate(papers, 1):
        lines.append(_paper_entry(i, p))
        lines.append("")
    return "\n".join(lines)


def _to_json(today: str, papers: List[Paper]) -> str:
    data = {
        "date": today,
        "papers": [
            {
                "title": p.title,
                "url": p.url,
                "authors": p.authors,
                "institution": p.institution,
                "keywords": p.keywords_tags,
                "summary": p.one_line_summary,
                "abstract": p.summary,
                "source": p.source,
                "published": p.published,
            }
            for p in papers
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ─────────────────── 企业微信多条消息 ───────────────────


def format_wecom_messages(papers: List[Paper]) -> List[str]:
    """
    拆分成多条 ≤ 4096 字节的企业微信 Markdown 消息。
    所有论文按模板格式发出，不截断。
    """
    today = date.today().isoformat()
    messages: List[str] = []

    header = f"# 今日热门 Paper 快讯\n{today} · 共 {len(papers)} 篇精选\n"

    paper_entries = [_paper_entry(i, p) for i, p in enumerate(papers, 1)]

    # 贪心拼装：第一条带 header
    current = header
    current_size = len(current.encode("utf-8"))

    for entry in paper_entries:
        entry_with_sep = "\n\n" + entry
        entry_bytes = len(entry_with_sep.encode("utf-8"))

        if current_size + entry_bytes > _WECOM_MAX_BYTES:
            messages.append(current)
            current = entry
            current_size = len(entry.encode("utf-8"))
        else:
            current += entry_with_sep
            current_size += entry_bytes

    if current:
        messages.append(current)

    return messages


# ─────────────────── 保存文件 ───────────────────


def save_report(content: str, output_dir: Path, filename_prefix: str = "daily") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    ext = "json" if content.strip().startswith("{") else "md"
    path = output_dir / f"{filename_prefix}_{today}.{ext}"
    path.write_text(content, encoding="utf-8")
    return path
