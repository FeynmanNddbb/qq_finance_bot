from fetcher import fetch_all_news
from analyzer import analyze
from sender import send_qq
from datetime import datetime
import schedule
import time


# ===== 主任务 =====
def main_job():
    try:
        print(f"开始执行: {datetime.now()}")

        news = fetch_all_news()
        result = analyze(news)

        today = datetime.now().strftime("%m月%d日")
        message = f"📰 新闻早班车（{today}）\n\n{result}"

        send_qq(message)

        print("执行完成\n")

    except Exception as e:
        print("执行失败:", e)


# ===== 定时任务 =====
schedule.every().day.at("08:00").do(main_job)
schedule.every().day.at("22:00").do(main_job)


# ===== 启动 =====
if __name__ == "__main__":
    print("机器人已启动...")

    while True:
        schedule.run_pending()
        time.sleep(30)