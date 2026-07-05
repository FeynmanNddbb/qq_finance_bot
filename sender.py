import os

import requests
from datetime import datetime
from dotenv import load_dotenv

from fetcher import fetch_all_news, fetch_cls_news, fetch_wallstreet_news
from analyzer import analyze

load_dotenv()

# ====================== 配置区（全部从环境变量读取，见 .env.example） ======================
# NapCat HTTP 服务地址（HTTP API 端口，通常是 3000）
NAPCAT_HTTP = os.getenv("NAPCAT_HTTP", "http://127.0.0.1:3000").strip()

# NapCat Access Token（在 WebUI 中设置，强烈建议配置；未设置则留空）
NAPCAT_TOKEN = os.getenv("NAPCAT_TOKEN", "").strip()

# 目标 QQ 群号
GROUP_ID = int(os.getenv("QQ_GROUP_ID", "0"))

# 单条消息最大长度（QQ 实际限制约 5000-8000 字符，保守设置）
MAX_MESSAGE_LENGTH = 4500
# ====================================================


def send_to_qq_group(message: str, group_id: int = GROUP_ID) -> bool:
    """通过 NapCat HTTP 接口发送消息到 QQ 群（支持分段发送）"""
    if not message or not message.strip():
        print("⚠️ 消息内容为空，跳过发送")
        return False

    # 如果消息太长，进行分段发送
    if len(message) > MAX_MESSAGE_LENGTH:
        print(f"消息过长 ({len(message)} 字符)，将分段发送...")
        segments = [message[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(message), MAX_MESSAGE_LENGTH)]
        success_count = 0
        for i, seg in enumerate(segments, 1):
            print(f"正在发送第 {i}/{len(segments)} 段...")
            if send_single_message(seg, group_id):
                success_count += 1
        return success_count == len(segments)
    else:
        return send_single_message(message, group_id)


def send_single_message(message: str, group_id: int) -> bool:
    """发送单条消息"""
    url = f"{NAPCAT_HTTP}/send_group_msg"
    
    payload = {
        "group_id": group_id,
        "message": message,
        "auto_escape": False
    }
    
    headers = {}
    if NAPCAT_TOKEN:
        headers["Authorization"] = f"Bearer {NAPCAT_TOKEN}"
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") in ["ok", "success"] or data.get("retcode") in [0, 1]:
                print("✅ 已成功发送到 QQ 群")
                return True
            else:
                print(f"❌ 发送失败: {data}")
                return False
        else:
            print(f"❌ HTTP 状态码异常: {resp.status_code} | {resp.text[:300]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败！请检查 NapCat 是否正在运行，以及 HTTP 服务是否已开启（端口 {NAPCAT_HTTP}）")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False


def send_news_to_qq_group():
    print(f"🚀 开始抓取并发送新闻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        news = fetch_all_news()
        result = analyze(news)
        
        now = datetime.now()
        time_day = "今日早盘最新消息" if now.hour < 12 else "今日晚盘最新消息"
        date_str = now.strftime("%m月%d日 %H:%M")
        
        cls_count = len(fetch_cls_news())
        wall_count = len(fetch_wallstreet_news())
        total_count = len(news)
        
        # 构造标题（更美观）
        title = f"""📰 {time_day}（{date_str}）
━━━━━━━━━━━━━━
财联社条数: {cls_count} 条
华尔街见闻条数: {wall_count} 条
共抓取到 {total_count} 条新闻
━━━━━━━━━━━━━━

"""
        
        # 新闻列表
        news_list = "\n".join([f"{idx}. {n}" for idx, n in enumerate(news, 1)])
        
        # 完整消息
        full_message = title + news_list + "\n\n" + result
        
        print(f"共生成消息长度: {len(full_message)} 字符")
        
        # 发送
        success = send_to_qq_group(full_message)
        
        if success:
            print("🎉 新闻已成功发送到 QQ 群！")
        else:
            print("⚠️ 发送过程中出现问题，请检查日志")
            
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {e}")
    
    print("========== 发送流程结束 ==========")


if __name__ == "__main__":
    send_news_to_qq_group()