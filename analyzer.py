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
PROMPT_TEMPLATE = """你是一个专业的A股分析师，请根据以下新闻生成:

1. 3条核心要点
2. 利好板块
3. 利空板块
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
