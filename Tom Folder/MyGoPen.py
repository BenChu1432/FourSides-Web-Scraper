# import feedparser
# from bs4 import BeautifulSoup

# def clean_html(html):
#     soup = BeautifulSoup(html, "html.parser")
#     return soup.get_text(strip=True)

# # 使用 RSS 格式
# rss_url = "https://www.mygopen.com/feeds/posts/default?alt=rss"

# feed = feedparser.parse(rss_url)

# # 檢查是否有錯誤
# if feed.bozo:
#     print("❌ RSS 有錯誤：", feed.bozo_exception)
# else:
#     print(f"✅ 共抓到 {len(feed.entries)} 篇文章")

# # 印出前幾篇
# for i, entry in enumerate(feed.entries[:5]):
#     print(f"\n📰 第 {i+1} 篇")
#     print("📌 標題:", entry.title)
#     print("🔗 連結:", entry.link)
#     print("📅 發佈時間:", entry.published if 'published' in entry else "（無）")
#     print("📄 摘要:", clean_html(entry.summary)[:100] + "..." if 'summary' in entry else "（無）")
#     if "media_thumbnail" in entry:
#         print("🖼️ 圖片:", entry.media_thumbnail[0]['url'])
#     else:
#         print("🖼️ 圖片: （無）")


import feedparser
from bs4 import BeautifulSoup
import requests
import time


class MyGoPenNews:
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name = "MyGoPen"
        self.feed_url = "https://www.mygopen.com/feeds/posts/default?alt=rss"
        self.max_articles = 10
        self.origin = "MyGoPen"

    def _get_article_urls(self):
        print(f"🌐 解析 RSS：{self.feed_url}")
        feed = feedparser.parse(self.feed_url)

        if feed.bozo:
            print("❌ RSS 有錯誤：", feed.bozo_exception)
            return []

        print(f"✅ 共抓到 {len(feed.entries)} 篇文章")
        urls = []

        for entry in feed.entries[:self.max_articles]:
            if "link" in entry:
                urls.append(entry.link)

        print(f"🎯 總共擷取 {len(urls)} 筆文章連結")
        return urls

    def parse_article(self, soup):
        # 標題
        self.title = soup.title.string.strip() if soup.title else "Missing Title"

        # 摘要
        meta_desc = soup.find("meta", attrs={"name": "description"})
        self.summary = meta_desc["content"].strip() if meta_desc and meta_desc.has_attr("content") else "Missing Summary"

        # 發布日期
        pub_date_tag = soup.find("abbr", class_="published")
        self.published_at = pub_date_tag.get("title") if pub_date_tag else None

        # 查核記者（MyGoPen 通常沒有）
        self.authors = []

        # 內容
        content_div = soup.find("div", class_="post-body")
        if content_div:
            self.content = "\n".join(p.get_text(strip=True) for p in content_div.find_all("p"))
        else:
            self.content = "Missing Content"

        # 圖片
        self.images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.endswith(".jpg"):
                self.images.append(src)


if __name__ == "__main__":
    checker = MyGoPenNews()
    checker.run()