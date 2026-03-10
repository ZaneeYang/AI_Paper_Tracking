"""论文数据源：从 Hugging Face、arXiv 等拉取热门论文。"""
from .base import Paper
from .huggingface_papers import fetch_huggingface_trending_papers
from .arxiv_papers import fetch_arxiv_recent_papers

__all__ = [
    "Paper",
    "fetch_huggingface_trending_papers",
    "fetch_arxiv_recent_papers",
]
