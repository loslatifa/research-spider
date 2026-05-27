# 🚀 Research Spider Framework - Updated README

## 简介
Research Spider 是一个支持定时定点批量爬取多个科研网站（如 arXiv、PubMed、DOAJ、IEEE、OpenAlex）并自动完成论文增量更新检测、AI 分析、优先级筛选与摘要推送的科研抓取分析框架。

## 功能特点
- **robots.txt 检测与合规抓取**
- 可配置站点管理 (`config/sites_to_crawl.csv`)
- 自动定时每日凌晨 3:00 批量抓取 (`scripts/auto_runner.py`)
- 自动保存 `result/master` CSV 并做增量更新检测
- 支持共享论文 schema，输出 `abstract` / `keywords` / `record_hash` / `change_type`
- 支持 SQLite 结构化存储 (`data/research_spider.db`)
- 支持 AI 论文分析流水线，输出稳定 JSON
- 支持推荐打分、主题节流、重复推送抑制
- 支持控制台 + Markdown + JSON digest 推送
- 支持停用词过滤与 TF-IDF 关键词提取
- 支持 n-gram (2-3 gram) 复合词频率统计与可视化
- 可输出词云、柱状图与关键词频率表

## 目录结构
- `research_spider/` 业务源码包
- `research_spider/spider/` 爬虫核心模块 (fetcher, parser, runner, utils)
- `research_spider/analyzer/` AI 论文分析模块
- `research_spider/storage/` 共享 schema 与 SQLite 存储
- `research_spider/recommender/` 优先级评分与推送过滤
- `research_spider/notifier/` 推送与 digest 输出
- `research_spider/pipeline/` 编排层，串联抓取结果到分析/推送
- `scripts/` 命令行入口与一次性工具脚本
- `resources/` 停用词等静态资源
- `docs/` 项目结构、规划与需求记录
- `config/sites_to_crawl.csv` 配置待抓取网站列表
- `config/pipeline_config.json` AI/推荐/推送配置
- `config/user_preferences.json` 用户关注主题与关键词
- `data/` 保存抓取的 CSV
- `figures/` 保存生成的可视化图表和表格
- `logs/` 可选保存抓取日志
- `scripts/auto_runner.py` 定时批量抓取执行脚本
- `scripts/analyze_data.py` 数据分析与可视化脚本
- `scripts/run_paper_pipeline.py` 对增量 CSV 执行 AI 分析与推送

## 使用方法
1️⃣ **安装依赖**：
```bash
pip install pandas matplotlib wordcloud scikit-learn requests beautifulsoup4 schedule
```

2️⃣ **配置 AI 模型（可选）**：

复制模板并填写本地密钥：
```bash
cp .env.example .env
```

默认配置使用 Qwen OpenAI-compatible API，模型为 `qwen3.5-plus`，`.env` 已被 `.gitignore` 忽略，不会提交密钥。
也兼容 `DASHSCOPE_API_KEY` 作为 Qwen API key。如需切回 OpenAI，可在 `.env` 中改为 `AI_PROVIDER=openai` 并配置 `OPENAI_API_KEY` / `OPENAI_MODEL` / `OPENAI_BASE_URL`。

如果未配置对应 provider 的 API key，系统会自动回退到本地启发式分析，流程仍可跑通。

3️⃣ **编辑抓取与推送配置**：
- `config/sites_to_crawl.csv` / `config/sites_to_crawl_full.csv`
- `config/pipeline_config.json`
- `config/user_preferences.json`

4️⃣ **按配置抓取常用源**：
```bash
python -m scripts.run_spider
```
默认读取 `config/sites_to_crawl.csv`，抓取所有 `enable=1` 的常用源。抓取完成后会自动触发：
- CSV 增量更新检测
- 基础可视化
- AI 分析与 digest 推送

常用命令：
```bash
python -m scripts.run_spider --list
python -m scripts.run_spider --site arxiv
python -m scripts.run_spider --site arxiv --site openalex
python -m scripts.run_spider --url https://api.openalex.org/works?filter=title.search:machine%20learning
```

5️⃣ **关键词抓取**：
```bash
python -m scripts.keyword_crawl_all
```

6️⃣ **仅处理已有增量 CSV**：
```bash
python -m scripts.run_paper_pipeline --latest 1
python -m scripts.run_paper_pipeline --csv data/result_api_openalex_org_20260304.csv
```

7️⃣ **每日定时自动抓取**：
直接运行：
```bash
python -m scripts.auto_runner
```
将于每天凌晨 03:00 自动抓取所有启用站点。

8️⃣ **抓取完成后仅进行分析可视化**：
```bash
python -m scripts.analyze_data
```
生成词频柱状图、词云及关键词频率表。

## AI 分析输出
AI 分析模块输出稳定 JSON，核心字段包括：
- `title_zh`
- `summary_zh`
- `research_problem`
- `methodology`
- `innovations`
- `topic_tags`
- `attention_score`
- `attention_recommendation`
- `limitations_or_risks`
- `confidence`

## TODO
- [ ] 集成可选的自动报告生成 (Markdown/PDF)
- [ ] 可选邮件/Telegram/Webhook 报告推送
- [ ] 支持更多公开科研网站与 API 模块 (Europe PMC, OpenAlex 等)
