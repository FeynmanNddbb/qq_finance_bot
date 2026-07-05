"""
新闻分析模块。

支持三种大模型后端，通过环境变量 LLM_PROVIDER 切换：
  - zhipu  : 智谱 GLM
  - openai : OpenAI GPT
  - claude : Anthropic Claude

所有密钥均从环境变量读取，请在 .env 中配置（参考 .env.example）。
"""
import os

from dotenv import load_dotenv

load_dotenv()


# 分析新闻用的统一提示词
#
# 模型边界（重要）：分析严格限定在下方「新闻」内容之内。
# 模型不联网、不检索外部资料、不调用任何工具，也不引入新闻之外的信息或个人臆测，
# 仅对已抓取到的这批新闻做归纳与分析。
PROMPT_TEMPLATE = """你是一个专业的A股分析师。请**严格且仅**依据下方「新闻」中给出的内容进行总结与分析。

必须遵守的边界：
- 只能使用下方「新闻」里出现的信息，不得联网搜索、不得调用任何工具、不得引用新闻之外的任何资料或数据。
- 不得编造、推测或补充新闻中没有提到的事实、数字、公司或事件。
- 如果新闻内容不足以支撑某一项判断，请直接写明「新闻中信息不足，无法判断」，不要强行给出结论。
- 你的所有结论都应能在下方新闻中找到出处。

请基于上述新闻生成:

1. 3条核心要点（均须来自新闻原文）
2. 利好板块（并简述依据的新闻）
3. 利空板块（并简述依据的新闻）
4. 总结一句话

新闻：
{news}
"""


def _build_prompt(news_list: list[str]) -> str:
    text = "\n".join(news_list[:40])
    return PROMPT_TEMPLATE.format(news=text)


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"缺少环境变量 {name}，请在 .env 中配置（可参考 .env.example）"
        )
    return value


# ===== 智谱 GLM =====
def _analyze_with_zhipu(prompt: str) -> str:
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=_require_env("ZHIPUAI_API_KEY"))
    model = os.getenv("ZHIPUAI_MODEL", "glm-4.6").strip()

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ===== OpenAI GPT =====
def _analyze_with_openai(prompt: str) -> str:
    from openai import OpenAI

    kwargs = {"api_key": _require_env("OPENAI_API_KEY")}
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    model = os.getenv("OPENAI_MODEL", "gpt-4o").strip()

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ===== Anthropic Claude =====
def _analyze_with_claude(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=_require_env("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8").strip()

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    # response.content 是内容块列表，取出其中的文本块
    return "".join(block.text for block in response.content if block.type == "text")


_PROVIDERS = {
    "zhipu": _analyze_with_zhipu,
    "openai": _analyze_with_openai,
    "claude": _analyze_with_claude,
}


def analyze(news_list: list[str]) -> str:
    provider = os.getenv("LLM_PROVIDER", "zhipu").strip().lower()
    handler = _PROVIDERS.get(provider)
    if handler is None:
        raise ValueError(
            f"未知的 LLM_PROVIDER: {provider!r}，可选值：{', '.join(_PROVIDERS)}"
        )

    prompt = _build_prompt(news_list)
    return handler(prompt)
