# 📚 Research Spider Framework

科研通用爬虫框架，支持稳定、低速、可迁移抓取公开科研或行业网站数据，并自动生成 CSV、可验证抓取完整性，适用于科研选题、学术分析和建模。
## ！！！！前排高亮：还在编写当中，目前仅为框架（也就是废物）！！！！！勿喷勿喷

---

## ✨ 功能特性

✅ 通用可迁移，可快速适配不同目标网站  
✅ 串行慢速爬取，防封与可持续挂载  
✅ robots.txt 自动检测，自动判断是否允许爬取  
✅ 随机 UA + 随机 sleep，真实模拟用户行为  
✅ 自动写入带【域名+日期】命名的 CSV 文件，避免覆盖  
✅ 自动验证抓取完整性（列信息、缺失值、样本预览）  
✅ 完整日志记录，便于溯源排错  
✅ 可选递归同域抓取（扩展多页抓取）  
✅ 可视化分析与词云生成便于科研选题展示

---

## 🗂️ 项目结构

```
research_spider_project/
├── data/                       # 存放抓取结果 CSV / JSON
├── figures/                    # 可视化图表输出
├── logs/                       # 日志存储
├── proxy_pool/                 # 可选：代理池与检测
├── spider/                     # 核心爬虫模块
│   ├── fetcher.py              # 请求封装模块
│   ├── parser.py               # 页面解析模块（需根据目标站替换）
│   ├── runner.py               # 调度与抓取控制
│   ├── utils.py                # 工具函数
│   ├── validator.py            # 数据验证
│   └── robots_checker.py       # robots.txt 自动检测
├── tests/                      # 测试脚本（可选）
├── run_spider.py               # 项目入口文件（已由 main.py 改名）
├── analyze_data.py             # 可视化分析脚本
└── requirements.txt            # 依赖文件
```

---

## 🚀 快速使用

1️⃣ 克隆或复制本项目至本地  
2️⃣ 安装依赖：
```bash
pip install -r requirements.txt
```

3️⃣ 执行主程序：
```bash
python run_spider.py
```

4️⃣ 输入目标 URL（如 https://books.toscrape.com/）和最大抓取页数（默认 3）  
5️⃣ 程序自动执行【robots.txt 检查 ➔ 抓取 ➔ 验证 ➔ 保存 CSV】流程

6️⃣ 执行分析与可视化：
```bash
python analyze_data.py
```
生成词频柱状图、词云、域名分布图保存在 `figures/` 文件夹内，用于论文与选题展示。

---

## ⚙️ 模块说明

### `run_spider.py`
用户交互入口，接收 URL 和页数，执行 robots 检查后进行爬取和验证。

### `spider/robots_checker.py`
自动检测 robots.txt，判断是否允许爬取后决定是否执行。

### `spider/fetcher.py`
封装请求逻辑，支持随机 UA、防封重试和可选代理接入。

### `spider/parser.py`
页面解析模块（**需根据目标网站结构修改**）。

### `spider/runner.py`
抓取调度与控制，自动生成【带域名+日期】命名的 CSV。

### `spider/utils.py`
随机 sleep、日志写入、时间戳获取等通用工具。

### `spider/validator.py`
抓取后自动验证 CSV 文件是否正确并显示摘要信息。

### `analyze_data.py`
分析最新抓取数据并生成可视化图表（词频、词云、域名分布）。

---

## 🛡️ 注意事项
✅ 合理使用，遵守目标站 `robots.txt` 与使用条款  
✅ 串行慢速抓取，避免高频触发封禁  
✅ 建议用于科研和公开数据采集分析场景

---

## ❤️ 后续可扩展功能
✅ 自动代理池抓取  
✅ 持续断点续跑  
✅ 自动生成报告 PDF  
✅ Telegram / 邮件推送抓取进度  
✅ Docker / Jupyter 自动化挂载

如需继续扩展项目以服务长期科研选题和数据抓取，请继续联系完善链条。
