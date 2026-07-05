# QQ 财经机器人（qq_finance_bot）

自动抓取财经新闻 → 调用大模型做 A 股分析 → 定时推送到 QQ 群的财经机器人。

抓取财联社、华尔街见闻、证监会、金融监管总局等来源的最新资讯，用大模型（智谱 GLM / OpenAI GPT / Anthropic Claude 任选其一）生成核心要点与利好利空分析，再通过 [NapCat](https://github.com/NapNeko/NapCatQQ) 的 HTTP 接口发送到指定 QQ 群，支持每日早晚定时推送。

## 功能特性

- **多源抓取**：财联社、华尔街见闻、中国证监会、国家金融监督管理总局，支持 requests / Selenium / 混合模式，自动兜底
- **多模型分析（严格限定边界）**：通过环境变量一键切换 智谱 GLM、OpenAI GPT、Anthropic Claude；模型**只对抓取到的新闻做总结与分析**，不联网、不检索、不调用工具、不编造新闻之外的内容（详见下方「AI 模型的使用与边界」）
- **定时推送**：基于 APScheduler，默认每天 08:30 早盘、20:30 晚盘各推送一次
- **长消息分段**：超长消息自动分段发送，规避 QQ 单条长度限制
- **密钥零硬编码**：所有密钥、群号均从环境变量读取，`.env` 不入库
- **本地调试**：`print_local.py` 可不依赖 QQ 直接在终端预览结果

## AI 模型的使用与边界（重要）

> ⚠️ **请务必理解模型的能力边界，再使用本项目的分析结果。**

本项目中大模型只承担**一件事**：对**已抓取到的新闻**做总结与分析。它的行为被严格限定，**不做任何超出输入内容的操作**。分析结果只是对既有新闻的归纳，不是独立的市场研判，更不构成投资建议。

- **严格基于新闻内容判断**：所有核心要点、利好/利空分析都必须来自本次抓取到的新闻原文，结论可在新闻中找到出处。
- **不联网、不检索**：模型不会联网搜索、不调用任何外部工具或数据源，仅处理程序传入的这批新闻文本。
- **不编造、不臆测**：不补充新闻中没有的事实、数字或事件；当信息不足时，模型会直接说明「新闻中信息不足，无法判断」，而非强行给出结论。
- **边界在提示词中显式约束**：上述规则写在 `analyzer.py` 的 `PROMPT_TEMPLATE` 中，切换 zhipu / openai / claude 任一后端时约束保持一致。

> 换言之，模型是一个「只读新闻、不外求」的分析器：输入是什么，就只分析什么。

## 项目结构

| 文件 | 说明 |
| --- | --- |
| `main.py` | 入口之一：基于 `schedule` 的简单定时任务 |
| `sender_time.py` | 推荐入口：基于 APScheduler 的定时推送（早 8:30 / 晚 20:30） |
| `sender.py` | 抓取 + 分析 + 发送的一次性执行脚本 |
| `fetcher.py` | 多源新闻抓取，站点配置集中在 `NEWS_SOURCES` |
| `analyzer.py` | 大模型分析，支持 zhipu / openai / claude 切换 |
| `print_local.py` | 本地终端预览（不发送到 QQ），方便调试 |
| `logger_utils.py` | 统一日志（滚动写入 `logs/`） |
| `.env.example` | 环境变量模板，复制为 `.env` 后填入真实值 |

## 环境要求

- Python 3.10+（代码使用了 `list[str]` 等新式类型标注）
- 一个正在运行的 [NapCat](https://github.com/NapNeko/NapCatQQ)，并开启 HTTP API（默认端口 3000）
- Selenium 抓取部分需要本机安装 Chrome 浏览器及对应驱动

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/<your-name>/qq_finance_bot.git
cd qq_finance_bot

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

> 大模型 SDK（zhipuai / openai / anthropic）按需安装即可，只用哪个装哪个。

### 2. 配置环境变量

复制模板并填入你自己的密钥：

```bash
cp .env.example .env
```

然后编辑 `.env`，**至少**配置这几项：

- `LLM_PROVIDER`：选择 `zhipu` / `openai` / `claude`
- 对应模型的 API Key（如 `ZHIPUAI_API_KEY`）
- `NAPCAT_HTTP`、`NAPCAT_TOKEN`、`QQ_GROUP_ID`

> `.env` 已被 `.gitignore` 忽略，不会上传到 GitHub。**切勿把真实密钥写进 `.env.example` 或提交到仓库。**

### 3. 本地预览（不发送）

```bash
python print_local.py
```

### 4. 启动定时推送

```bash
python sender_time.py
```

保持进程运行即可，默认每天 08:30 和 20:30 各推送一次。需要立即测试推送时，可临时取消 `sender_time.py` 中 `send_news_to_qq_group()` 那一行的注释。

## 环境变量说明

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `LLM_PROVIDER` | 使用的模型后端：`zhipu` / `openai` / `claude` | `zhipu` |
| `ZHIPUAI_API_KEY` | 智谱 API Key | — |
| `ZHIPUAI_MODEL` | 智谱模型名 | `glm-4.6` |
| `OPENAI_API_KEY` | OpenAI API Key | — |
| `OPENAI_MODEL` | OpenAI 模型名 | `gpt-4o` |
| `OPENAI_BASE_URL` | OpenAI 代理/中转地址，官方直连留空 | — |
| `ANTHROPIC_API_KEY` | Anthropic Claude API Key | — |
| `ANTHROPIC_MODEL` | Claude 模型名 | `claude-opus-4-8` |
| `NAPCAT_HTTP` | NapCat HTTP API 地址 | `http://127.0.0.1:3000` |
| `NAPCAT_TOKEN` | NapCat Access Token，未设置留空 | — |
| `QQ_GROUP_ID` | 目标 QQ 群号 | — |
| `NEWS_SOURCES` | 只启用部分源（逗号分隔，如 `cls,wallstreet`），留空为全部 | 全部 |

## 安全提示

- 本项目所有密钥均通过环境变量读取，请务必保管好 `.env`，不要提交或分享。
- 如果曾经把真实密钥提交进 Git 历史，请到对应平台**吊销并重新生成**密钥。

## 免责声明

本项目仅供学习与技术交流。新闻内容与分析结果由第三方网站与大模型生成，不构成任何投资建议，据此操作风险自负。请遵守各新闻站点的爬虫协议与使用条款。
