import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from fetcher import NEWS_SOURCES, fetch_news_by_source, get_enabled_source_keys
from analyzer import analyze
from logger_utils import get_logger

load_dotenv()

# ====================== 配置区（全部从环境变量读取，见 .env.example） ======================
# NapCat HTTP 服务地址（HTTP API 端口，通常是 3000）
NAPCAT_HTTP = os.getenv("NAPCAT_HTTP", "http://127.0.0.1:3000").strip()

# NapCat Access Token（在 WebUI 中设置，未设置则留空）
NAPCAT_TOKEN = os.getenv("NAPCAT_TOKEN", "").strip()

# 目标 QQ 群号
GROUP_ID = int(os.getenv("QQ_GROUP_ID", "0"))

# 单条消息最大长度
MAX_MESSAGE_LENGTH = 4500
# ====================================================


logger = get_logger(__name__)


def _source_limit(source_key: str) -> int:
    return 10 if source_key in {"cls", "wallstreet"} else 5


def _build_news_bundle() -> tuple[list[str], dict[str, int]]:
    all_news = []
    source_counts: dict[str, int] = {}

    for source_key in get_enabled_source_keys():
        source_news = fetch_news_by_source(source_key)
        limit = _source_limit(source_key)
        limited_news = source_news[:limit]

        source_counts[source_key] = len(limited_news)
        all_news.extend(limited_news)

    return all_news, source_counts


def send_single_message(message: str, group_id: int) -> bool:
    """发送单条消息"""
    url = f"{NAPCAT_HTTP}/send_group_msg"
    
    payload = {
        "group_id": group_id,
        "message": message,
        "auto_escape": False
    }
    
    headers = {}
    if NAPCAT_TOKEN.strip():
        headers["Authorization"] = f"Bearer {NAPCAT_TOKEN}"
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") in ["ok", "success"] or data.get("retcode") in [0, 1]:
                logger.info("消息发送成功，group_id=%s", group_id)
                return True
            else:
                logger.error("消息发送失败，响应=%s", data)
                return False
        else:
            logger.error("消息发送 HTTP 状态码异常: %s | %s", resp.status_code, resp.text[:300])
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("连接失败，请检查 NapCat 是否运行，HTTP 地址=%s", NAPCAT_HTTP)
        return False
    except Exception as e:
        logger.exception("消息发送请求异常: %s", e)
        return False


def send_to_qq_group(message: str, group_id: int = GROUP_ID) -> bool:
    """支持长消息分段发送"""
    if not message or not message.strip():
        logger.warning("消息内容为空，跳过发送")
        return False

    if len(message) > MAX_MESSAGE_LENGTH:
        logger.info("消息过长(%s字符)，开始分段发送", len(message))
        segments = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
        success_count = 0
        for i, seg in enumerate(segments, 1):
            logger.info("正在发送第 %s/%s 段", i, len(segments))
            if send_single_message(seg, group_id):
                success_count += 1
        return success_count == len(segments)
    else:
        return send_single_message(message, group_id)


def send_news_to_qq_group():
    """核心发送逻辑：抓取新闻 → 分析 → 发送"""
    logger.info("开始抓取并发送新闻: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    try:
        news, source_counts = _build_news_bundle()
        if not news:
            logger.warning("本次抓取结果为空，跳过发送")
            return

        result = analyze(news)
        
        now = datetime.now()
        time_day = "今日早盘最新消息" if now.hour < 12 else "今日晚盘最新消息"
        date_str = now.strftime("%m月%d日 %H:%M")
        total_count = len(news)

        source_lines = []
        for source_key in get_enabled_source_keys():
            source_name = NEWS_SOURCES[source_key]["name"]
            source_count = source_counts.get(source_key, 0)
            source_lines.append(f"{source_name}条数: {source_count} 条")
        source_summary = "\n".join(source_lines)
        
        title = f"""📰 {time_day}（{date_str}）
━━━━━━━━━━━━━━
{source_summary}
共抓取到 {total_count} 条新闻
━━━━━━━━━━━━━━

"""
        
        news_list = "\n".join([f"{idx}. {n}" for idx, n in enumerate(news, 1)])
        full_message = title + news_list + "\n\n" + result
        
        logger.info("共生成消息长度: %s 字符", len(full_message))
        
        success = send_to_qq_group(full_message)
        
        if success:
            logger.info("新闻已成功发送到 QQ 群")
        else:
            logger.warning("发送过程中出现问题，请检查本地日志")
            
    except Exception as e:
        logger.exception("执行过程中发生错误: %s", e)

    logger.info("========== 本次发送流程结束 ==========")


# ====================== 定时任务设置 ======================
def setup_scheduler():
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")  # 使用北京时间
    
    # 每天早上 8:00 发送
    scheduler.add_job(
        send_news_to_qq_group,
        trigger=CronTrigger(hour=8, minute=30),
        id='morning_news',
        name='早盘新闻'
    )
    
    # 每天晚上 21:00 发送
    scheduler.add_job(
        send_news_to_qq_group,
        trigger=CronTrigger(hour=20, minute=30),
        id='evening_news',
        name='晚盘新闻'
    )
    
    scheduler.start()
    logger.info("定时任务已启动: 每天 08:30 发送早盘新闻, 20:30 发送晚盘新闻")
    return scheduler


# ====================== 主程序 ======================
if __name__ == "__main__":
    logger.info("=== QQ 财经机器人启动 ===")
    logger.info("当前时间: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # 启动定时任务
    scheduler = setup_scheduler()
    
    # 可选：启动时立即发送一次（方便测试）
    #send_news_to_qq_group()   # ← 需要测试时把这行前面的 # 去掉
    
    try:
        # 保持脚本运行
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("程序已退出")