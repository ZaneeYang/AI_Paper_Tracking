# AI Paper Tracking

每日自动追踪 AI 领域热门论文，通过 LLM 智能筛选并推送到企业微信。

## 功能特性

- **多源拉取** — 同时从 [Hugging Face Papers](https://huggingface.co/papers) 和 [arXiv](https://arxiv.org/) 获取前一天发布的论文
- **关键词过滤** — 支持自定义关键词（LLM / Agent / Memory / RAG 等），只保留相关论文
- **LLM 智能精选** — 调用大模型从候选池中挑选最值得阅读的 Top K 篇，综合评估相关性、机构可信度和实践价值
- **结构化信息提取** — LLM 自动提取每篇论文的机构、关键词标签和一句话中文总结（突出创新点）
- **企业微信推送** — 自动拆分为多条消息（≤ 4096 字节），避免截断
- **GitHub Actions 定时运行** — 每天北京时间 8:00 自动执行，也支持手动触发
- **报告存档** — 每次运行生成 Markdown 报告，GitHub Actions 中保存为 Artifact（30 天）

## 输出示例

```
# 今日热门 Paper 快讯 · 2026-03-10

1、Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory
  机构：Mem0.ai
  关键词：Memory / LLM / Coherence
  总结：Mem0 引入图结构内存，提升 LLM 长期对话连贯性，在准确性和计算效率上优于现有系统。

2、Very Large-Scale Multi-Agent Simulation in AgentScope
  机构：阿里巴巴
  关键词：Simulation / Scalability / Multi-Agent
  总结：AgentScope 平台通过分布式机制，提升大规模多智能体模拟的扩展性和效率。

...
```

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/ZaneeYang/AI_Paper_Tracking.git
cd AI_Paper_Tracking
```

### 2. 安装依赖

```bash
# 推荐使用虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 填入你的配置：

| 变量 | 必填 | 说明 |
|---|---|---|
| `ZHIPU_API_KEY` | 是 | 智谱 AI API Key，[申请地址](https://open.bigmodel.cn/) |
| `WECOM_WEBHOOK_URL` | 否 | 企业微信群机器人 Webhook URL |
| `PAPER_KEYWORDS` | 否 | 关键词过滤，逗号分隔，留空不过滤 |
| `TOP_K_PAPERS` | 否 | 精选论文数量，默认 10 |
| `MAX_PAPERS_PER_SOURCE` | 否 | 每个数据源拉取上限，默认 30 |
| `USER_PROFILE` | 否 | 用户画像，LLM 精选时参考 |

> 也支持 OpenAI 兼容接口，设置 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 即可。

### 4. 运行

```bash
# 手动执行一次
python run_daily.py

# 输出为 JSON 格式
python run_daily.py --format json

# 仅打印不保存文件
python run_daily.py --no-save
```

### 5. 定时任务（本地）

```bash
# 使用内置 scheduler（默认每天 8:00）
python scheduler.py
```

## GitHub Actions 自动化

本项目已配置 GitHub Actions，每天北京时间 8:00（UTC 0:00）自动运行。

### 配置步骤

1. Fork 或推送本仓库到你的 GitHub
2. 进入仓库 **Settings → Secrets and variables → Actions**
3. 添加以下 **Secrets**：
   - `ZHIPU_API_KEY` — 智谱 API Key
   - `WECOM_WEBHOOK_URL` — 企业微信 Webhook URL
4. （可选）添加 **Variables** 自定义参数：
   - `PAPER_KEYWORDS` — 关键词过滤
   - `TOP_K_PAPERS` — 精选数量
   - `MAX_PAPERS_PER_SOURCE` — 拉取上限

### 手动触发

进入 **Actions → Daily Paper Tracking → Run workflow**，可随时手动触发一次。

### 查看报告

每次运行完成后，在 Actions 运行详情页的 **Artifacts** 区域可下载当天的 Markdown 报告。

## 项目结构

```
AI_Paper_Tracking/
├── .github/workflows/
│   └── daily_paper.yml     # GitHub Actions 定时任务
├── sources/
│   ├── __init__.py
│   ├── base.py             # Paper 数据结构
│   ├── huggingface_papers.py  # HuggingFace 论文拉取
│   └── arxiv_papers.py     # arXiv 论文拉取
├── summarizer.py           # LLM 精选 + 信息提取
├── formatter.py            # 报告格式化（Markdown / JSON / 企业微信）
├── wecom.py                # 企业微信推送
├── run_daily.py            # 每日任务入口
├── scheduler.py            # 本地定时调度器
├── config.py               # 配置管理
├── requirements.txt
├── .env.example            # 环境变量模板
└── output/                 # 报告输出目录（git ignored）
```

## 处理流程

```
拉取论文（HuggingFace + arXiv，前一天，关键词过滤）
    ↓
去重（按标题）
    ↓
LLM 精选 Top K（评估相关性、机构可信度、实践价值）
    ↓
LLM 信息提取（机构 / 关键词 / 一句话总结）
    ↓
格式化报告 → 保存 Markdown
    ↓
企业微信推送（自动拆分多条消息）
```

## 企业微信配置

1. 在企业微信群中添加**群机器人**
2. 复制 Webhook URL（格式：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`）
3. 填入 `.env` 的 `WECOM_WEBHOOK_URL` 或 GitHub Secrets

> 单条消息限制 4096 字节，程序会自动拆分为多条发送，间隔 1 秒以遵守频率限制。

## License

MIT
