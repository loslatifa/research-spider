# 🚀 Research Spider Framework - Updated README

## 简介
Research Spider 是一个支持定时定点批量爬取多个科研网站（如 arXiv、PubMed、DOAJ、IEEE、Quotes to Scrape）并自动进行关键词词频分析、n-gram 复合词分析与可视化的科研抓取分析框架。

## 功能特点
- **robots.txt 检测与合规抓取**
- 可配置站点管理 (`config/sites_to_crawl.csv`)
- 自动定时每日凌晨 3:00 批量抓取 (`auto_runner.py`)
- 自动保存 CSV 数据并归类管理
- 支持停用词过滤与 TF-IDF 关键词提取
- 支持 n-gram (2-3 gram) 复合词频率统计与可视化
- 可输出词云、柱状图与关键词频率表

## 目录结构
- `spider/` 爬虫核心模块 (fetcher, parser, runner, utils)
- `config/sites_to_crawl.csv` 配置待抓取网站列表
- `data/` 保存抓取的 CSV
- `figures/` 保存生成的可视化图表和表格
- `logs/` 可选保存抓取日志
- `auto_runner.py` 定时批量抓取执行脚本
- `analyze_data.py` 数据分析与可视化脚本

## 使用方法
1️⃣ **安装依赖**：
```bash
pip install pandas matplotlib wordcloud scikit-learn requests beautifulsoup4 schedule
```

2️⃣ **编辑 `config/sites_to_crawl.csv`** 启用/禁用需要爬取的站点。

3️⃣ **单次手动抓取测试**：
```bash
python run_spider.py
```
按提示输入 URL 进行单次抓取。

4️⃣ **每日定时自动抓取**：
直接运行：
```bash
python auto_runner.py
```
将于每天凌晨 03:00 自动抓取所有启用站点。

5️⃣ **抓取完成后进行分析可视化**：
```bash
python analyze_data.py
```
生成词频柱状图、词云及关键词频率表。

## TODO
- [ ] 集成可选的自动报告生成 (Markdown/PDF)
- [ ] 可选邮件/Telegram 报告推送
- [ ] 支持更多公开科研网站与 API 模块 (Europe PMC, OpenAlex 等)
