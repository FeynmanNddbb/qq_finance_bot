"""
测试抓取脚本：输出从财联社和华尔街见闻获取的新闻条目。
"""
from fetcher import fetch_all_news

def test_fetch():
    """测试新闻抓取功能"""
    print("开始测试抓取...")
    try:
        news_list = fetch_all_news()
        print(f"共抓取到 {len(news_list)} 条新闻\n")
        print("财联社条数:", len(fetch_cls_news()))
        print("华尔街见闻条数:", len(fetch_wallstreet_news()))
        for idx, news in enumerate(news_list, 1):
            print(f"{idx}. {news}")
        print("\n测试完成")
    except Exception as e:
        print(f"抓取出错: {e}")
from fetcher import fetch_cls_news, fetch_wallstreet_news



if __name__ == "__main__":
    test_fetch()