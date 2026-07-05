"""
本地打印新闻脚本。

用途：
- 不依赖 QQ 机器人接口
- 直接在终端打印生成的新闻消息，便于本地调试
"""

from datetime import datetime

from analyzer import analyze
from fetcher import NEWS_SOURCES
from fetcher import fetch_news_by_source


def _source_limit(source_key: str) -> int:
    return 10 if source_key in {"cls", "wallstreet"} else 5


def _build_news_bundle() -> tuple[list[str], dict[str, int]]:
    source_counts = {
        "cls": 0,
        "wallstreet": 0,
        "csrc": 0,
        "nfra": 0,
    }
    merged_news = []

    for source_key in source_counts:
        source_news = fetch_news_by_source(source_key)
        limited_news = source_news[:_source_limit(source_key)]
        source_counts[source_key] = len(limited_news)
        merged_news.extend(limited_news)

    return merged_news, source_counts

def print_news_local() -> None:
    """抓取并分析新闻，然后打印到本地终端。"""
    print(f"开始执行本地打印: {datetime.now()}")

    news, source_counts = _build_news_bundle()
    result = analyze(news)

    now = datetime.now()
    # 根据时间确定标题
    time_day = "今日早盘最新消息" if now.hour < 12 else "今日晚盘最新消息"
    # 格式化日期时间，例如：03月24日 14:30
    date_str = now.strftime("%m月%d日 %H:%M")

    total_count = len(news)
    title = f"""📰 {time_day}（{date_str}）
    {NEWS_SOURCES['cls']['name']}条数: {source_counts['cls']} 条
    {NEWS_SOURCES['wallstreet']['name']}条数: {source_counts['wallstreet']} 条
    {NEWS_SOURCES['csrc']['name']}条数: {source_counts['csrc']} 条
    {NEWS_SOURCES['nfra']['name']}条数: {source_counts['nfra']} 条
    共抓取到 {total_count} 条新闻"""

    print(title)

    for idx, news in enumerate(news, 1):
        print(f"{idx}. {news}")
    print(result)
    print("========== 结束 ==========")


if __name__ == "__main__":
    try:
        print_news_local()
        print("\n本地打印完成")
    except Exception as exc:
        print("\n本地打印失败:", exc)