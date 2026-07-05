"""
@Project : qq_news_bot
@File : fetcher.py
@Author : feynman
@Time : 2026/3/24 下午4:40
"""
import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from typing import TypedDict

from logger_utils import get_logger


logger = get_logger(__name__)


COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


class NewsSource(TypedDict):
    key: str
    name: str
    url: str
    mode: str
    selectors: list[str]
    min_len: int
    max_items: int
    wait_seconds: float


def _build_chrome_options() -> Options:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={COMMON_HEADERS['User-Agent']}")
    return options


def _get_cls_block_reason(status_code: int, content: str) -> str | None:
    if status_code != 200:
        return f"HTTP状态码异常: {status_code}"

    blocked_signals = ["访问被拦截", "CloudWAF", "waf", "captcha"]
    lower_content = content.lower()
    for signal in blocked_signals:
        if signal.lower() in lower_content:
            return f"命中反爬特征: {signal}"

    return None


def _extract_titles_from_html(html: str, selectors: list[str], min_len: int, max_items: int) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    news = []
    seen = set()

    for selector in selectors:
        for item in soup.select(selector):
            text = item.get_text(strip=True)
            if len(text) <= min_len:
                continue
            if text in seen:
                continue
            seen.add(text)
            news.append(text)
            if len(news) >= max_items:
                return news

    return news


def _fetch_with_requests(source: NewsSource) -> list[str]:
    res = requests.get(source["url"], headers=COMMON_HEADERS, timeout=15)
    res.encoding = "utf-8"

    if source["key"] == "cls":
        block_reason = _get_cls_block_reason(res.status_code, res.text)
        if block_reason:
            raise RuntimeError(f"CLS 被拦截或响应异常，{block_reason}")
    elif res.status_code != 200:
        raise RuntimeError(f"HTTP状态码异常: {res.status_code}")

    news = _extract_titles_from_html(
        res.text,
        selectors=source["selectors"],
        min_len=source["min_len"],
        max_items=source["max_items"],
    )
    if not news:
        raise RuntimeError("requests 解析为空")
    return news


def _fetch_with_selenium(source: NewsSource) -> list[str]:
    driver = webdriver.Chrome(options=_build_chrome_options())
    try:
        driver.get(source["url"])
        time.sleep(source["wait_seconds"])

        css_query = ", ".join(source["selectors"])
        elements = driver.find_elements(By.CSS_SELECTOR, css_query)

        news = []
        seen = set()
        for element in elements:
            text = element.text.strip()
            if len(text) <= source["min_len"]:
                continue
            if text in seen:
                continue
            seen.add(text)
            news.append(text)
            if len(news) >= source["max_items"]:
                return news

        if news:
            return news

        html = driver.page_source
        return _extract_titles_from_html(
            html,
            selectors=source["selectors"],
            min_len=source["min_len"],
            max_items=source["max_items"],
        )
    finally:
        driver.quit()


NEWS_SOURCES: dict[str, NewsSource] = {
    "cls": {
        "key": "cls",
        "name": "财联社",
        "url": "https://www.cls.cn/",
        "mode": "hybrid",
        "selectors": ["a"],
        "min_len": 15,
        "max_items": 20,
        "wait_seconds": 3,
    },
    "wallstreet": {
        "key": "wallstreet",
        "name": "华尔街见闻",
        "url": "https://wallstreetcn.com/news/global",
        "mode": "selenium",
        "selectors": ["a.article-title", ".title", "h3 a", ".article-entry .title"],
        "min_len": 5,
        "max_items": 20,
        "wait_seconds": 3,
    },
    "csrc": {
        "key": "csrc",
        "name": "中国证监会",
        "url": "https://www.csrc.gov.cn/",
        "mode": "requests",
        "selectors": ["a"],
        "min_len": 12,
        "max_items": 5,
        "wait_seconds": 2,
    },
    "nfra": {
        "key": "nfra",
        "name": "国家金融监督管理总局",
        "url": "https://www.nfra.gov.cn/cn/view/pages/index/index.html",
        "mode": "selenium",
        "selectors": ["a"],
        "min_len": 8,
        "max_items": 5,
        "wait_seconds": 4,
    },
}


def _get_enabled_source_keys() -> list[str]:
    """
    可通过环境变量控制启用站点，示例：NEWS_SOURCES=cls,wallstreet
    """
    raw = os.getenv("NEWS_SOURCES", "").strip()
    if not raw:
        return list(NEWS_SOURCES.keys())

    keys = [item.strip() for item in raw.split(",") if item.strip()]
    enabled = [key for key in keys if key in NEWS_SOURCES]
    return enabled if enabled else list(NEWS_SOURCES.keys())


def fetch_news_by_source(source_key: str) -> list[str]:
    source = NEWS_SOURCES.get(source_key)
    if not source:
        raise ValueError(f"未知站点: {source_key}")

    mode = source["mode"]
    try:
        if mode == "requests":
            return _fetch_with_requests(source)
        if mode == "selenium":
            return _fetch_with_selenium(source)

        # hybrid: 先 requests，失败后 Selenium
        try:
            return _fetch_with_requests(source)
        except Exception as exc:
            logger.warning("%s requests 抓取失败，切换 Selenium 兜底: %s", source["name"], exc)
            return _fetch_with_selenium(source)
    except Exception as exc:
        logger.error("%s 抓取失败: %s", source["name"], exc)
        return []


def list_sources() -> list[str]:
    return list(NEWS_SOURCES.keys())


def get_enabled_source_keys() -> list[str]:
    return _get_enabled_source_keys()


# ===== 财联社抓取 =====
def fetch_cls_news():
    return fetch_news_by_source("cls")


# ===== 华尔街见闻抓取 =====

def fetch_wallstreet_news():
    return fetch_news_by_source("wallstreet")


# ===== 汇总 =====
def fetch_all_news():
    """
    财联社和华尔街见闻各取最多10条，其他站点各取最多5条
    """
    all_news = []
    for source_key in _get_enabled_source_keys():
        source_news = fetch_news_by_source(source_key)
        limit = 10 if source_key in {"cls", "wallstreet"} else 5
        all_news.extend(source_news[:limit])

    return all_news