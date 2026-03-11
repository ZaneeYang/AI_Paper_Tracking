"""论文数据结构。"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Paper:
    """单篇论文的元信息。"""
    title: str
    summary: str
    source: str
    url: str
    arxiv_id: Optional[str] = None
    authors: Optional[str] = None
    published: Optional[str] = None
    # 以下由 LLM enrich 阶段填充
    institution: Optional[str] = None
    keywords_tags: Optional[str] = None
    one_line_summary: Optional[str] = None
    detailed_analysis: Optional[dict] = None  # 详细分析：背景、动机、创新点、技术难点、不足、展望
    extra: dict = field(default_factory=dict)

    def to_text(self) -> str:
        """供大模型分析用的文本。"""
        parts = [f"标题: {self.title}", f"摘要: {self.summary}"]
        if self.authors:
            parts.append(f"作者: {self.authors}")
        if self.published:
            parts.append(f"发表: {self.published}")
        return "\n".join(parts)
