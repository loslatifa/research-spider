# CODEX 项目规则

Codex 修改本项目时必须遵守以下规则，除非用户明确要求例外。

## 1. 目录边界

- 业务代码统一放在 `research_spider/`。
- 命令行入口和工具脚本放在 `scripts/`。
- 配置放在 `config/`，静态资源放在 `resources/`，文档放在 `docs/`，测试放在 `tests/`。
- 不要在根目录新增业务模块。
- 从项目根目录运行命令，优先使用 `python -m scripts.<entrypoint>`。

## 2. 数据与产物

- 不提交抓取数据、数据库、digest、图表、日志、缓存、虚拟环境等生成物。
- 新增生成物路径时同步更新 `.gitignore`。
- 不删除、不回滚用户生成的数据，除非用户明确要求。

## 3. 代码规则

- 代码注释、docstring、开发文档使用英文。
- 中文用户输出、AI prompt、中文摘要、研究主题等产品行为内容可以保留中文。
- 优先沿用现有模式，改动保持小而聚焦。
- 新增论文来源时优先选择官方 API、RSS 或结构化 JSON，避免脆弱 HTML。
- 新来源必须尽量提取稳定 ID，例如 DOI、arXiv ID、PMID、OpenAlex ID、Semantic Scholar ID、Europe PMC ID。

## 4. 测试与校验

- 代码改动后运行 `python3 -m pytest`。
- CLI 或配置变更后运行 `python3 -m scripts.run_spider --list`。
- 编辑 JSON 后运行 `python3 -m json.tool <path>`。
- 单元测试不要依赖真实网络请求。

## 5. 规划记录

- 每次完成改进后更新 `docs/planning/codex-progress.txt`。
- 每次完成改进后更新 `docs/planning/feature_list.json`。
- `feature_list.json` 必须保持合法 JSON。
- 规划文件默认是本地记录，除非用户要求，否则不提交。

## 6. Git 规则

- commit message 使用英文，简短、清楚、严谨。
- 提交前检查 `git diff --cached --name-status`。
- 每个 commit 聚焦一类改动。
- 不把生成物、缓存、数据库、图表放进 commit。
- push 只推用户要求发布的已提交代码。

## 7. 安全规则

- 不使用 `git reset --hard`、`git checkout --` 等破坏性命令，除非用户明确要求。
- 不覆盖用户未提交改动。
- 不随意新增依赖；确需新增时同步更新 `requirements.txt`。
- 需要越权执行命令时，说明原因并请求批准。
