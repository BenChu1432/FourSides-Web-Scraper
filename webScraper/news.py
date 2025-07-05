import re
from typing import Optional
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import undetected_chromedriver 
# from translation import translate_text
from util.timeUtil import HKEJDateToTimestamp, IntiumChineseDateToTimestamp, NowTVDateToTimestamp, RTHKChineseDateToTimestamp, SCMPDateToTimestamp, SingTaoDailyChineseDateToTimestamp, TheCourtNewsDateToTimestamp, standardChineseDatetoTimestamp, standardDateToTimestamp
from webScraper.simplifiedChineseToTraditionalChinese import simplifiedChineseToTraditionalChinese

# Constants
WAITING_TIME_FOR_JS_TO_FETCH_DATA=0


class News(ABC):
    title: Optional[str]
    subtitle: Optional[str]
    content: Optional[str]
    published_at: Optional[int]
    authors: List[str]
    images: List[str]

    def __init__(self, url):
        self.url = url
        self.title = None
        self.subtitle = None
        self.content = None
        self.published_at=None
        self.authors=[]
        self.images=[]
        self._fetch_and_parse()

    def _fetch_and_parse(self):
        try:
            headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://google.com/',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
}
            response = requests.get(self.url, headers=headers)
            response.encoding = 'utf-8'
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            self._parse_article(soup)
        except Exception as e:
            print(f"Error fetching article: {e}")

    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract images
        self.images = []
        image_div = soup.find("div", id="zoomedimg")
        if image_div:
            image_links = image_div.find_all("a",class_="fancybox")
            for a in image_links:
                img = a.find("img")
                if img and img.has_attr("src"):
                    self.images.append(img["src"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("div", itemprop="datePublished", class_="date")
        if date_div:
            self.published_at = standardChineseDatetoTimestamp(date_div.get_text(strip=True))
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors (no authors)
        # self.authors = []
        # login_div = soup.find("div", class_="articlelogin")
        # if login_div:
        #     h2 = login_div.find("h2")
        #     if h2:
        #         authors_text = h2.get_text(strip=True)
        #         if authors_text:
        #             for author in authors_text.split(" "):
        #                 if author and author != "明報記者":
        #                     self.authors.append(author.strip())
        # print("self.authors:", self.authors)

        # Extract content
        content_div = soup.find("article")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            promo=content_div.find_all("strong")
            for p in promo:
                p.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

# HK News Media
class HongKongFreePress(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div", class_="entry-content")
        if content_div:
            paragraphs = content_div.find_all("p", recursive=False)
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        print("self.content:", self.content)
        self.images.append(soup.find("div", class_="entry-content").find("img")["src"])
        print("self.images:", self.images)

        self.authors.append(soup.find("div", class_="entry-subhead").find("span",class_="author vcard").get_text(strip=True))
        print("self.authors:", self.authors)
        published_at=soup.find("span", class_="posted-on").find("time").get_text(strip=True)
        self.published_at=standardDateToTimestamp(published_at)
        print("self.published_at:", self.published_at)


class MingPaoNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract images
        self.images = []
        image_div = soup.find("div", id="zoomedimg")
        print("image_div:",image_div)
        if image_div:
            image_links = image_div.find_all("a",class_="fancybox")
            print("image_links:", image_links)
            for a in image_links:
                if a and a.has_attr("href"):
                    self.images.append(a["href"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("div", itemprop="datePublished", class_="date")
        if date_div:
            self.published_at = standardDateToTimestamp(date_div.get_text(strip=True))
        else:
            self.published_at = None
        
        # Extract authors
        authors=soup.find("div",class_="articlelogin").find("h2").get_text(strip=True) if soup.find("div",class_="articlelogin") else "No author found"
        if len(authors)>0:
            for author in authors.split(" "):
                print("author:",author)
                if author!="明報記者":
                    self.authors.append(author.strip())
            print("self.authors:",self.authors)
        # Extract content
        upper_content = ""
        lower_content = ""

        upper_div = soup.find("div", id="upper")
        if upper_div:
            upper_paragraphs = upper_div.find_all("p")
            upper_content = "\n".join(p.get_text(strip=True) for p in upper_paragraphs)

        lower_div = soup.find("div", id="lower")
        if lower_div:
            autor_news_div = lower_div.find("div", id="pnsautornews")
            if autor_news_div:
                autor_news_div.decompose()
            lower_paragraphs = lower_div.find_all("p")
            lower_content = "\n".join(p.get_text(strip=True) for p in lower_paragraphs)

        self.content = upper_content + "\n" + lower_content

class SingTaoDaily(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract images
        self.images = []
        image_div = soup.find("figure").find_all("img")
        for img in image_div:
            if img and img.has_attr("src"):
                self.images.append(img["src"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("div", class_="time").find("span").get_text(strip=True) if soup.find("div", class_="time") else None
        if date_div:
            print("date_div:", date_div)
            self.published_at = SingTaoDailyChineseDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        self.authors = []
        login_div = soup.find("div", class_="articlelogin")
        if login_div:
            h2 = login_div.find("h2")
            if h2:
                authors_text = h2.get_text(strip=True)
                if authors_text:
                    for author in authors_text.split(" "):
                        if author and author != "明報記者":
                            self.authors.append(author.strip())
        print("self.authors:", self.authors)

        # Extract content
        content_div = soup.find("article")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            promo=content_div.find_all("strong")
            for p in promo:
                p.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class SCMP(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract images
        self.images = []
        image_div = soup.find("div", class_="css-tfsthe ea45u6l30")
        if image_div:
            image_links = image_div.find_all("img")
            print("image_links:", image_links)
            for a in image_links:
                img = a.find("img")
                if img and img.has_attr("data-original"):
                    self.images.append(img["data-original"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("time").get_text(strip=True)
        if date_div:
            print("date_div:", date_div)
            self.published_at = SCMPDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        self.authors = []
        author = soup.find("a", target="_self",class_="e163ld431 css-uvyeg2 ecgc78b0").get_text(strip=True)
        self.authors.append(author)

        # Extract content
        content_div = soup.find("article")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            promo=content_div.find_all("strong")
            for p in promo:
                p.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class ChineseNewYorkTimes (News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("div",class_="article-header").find("h1").get_text()
            self.content = soup.find("section",class_="article-body")
            print("self.content:",self.content)

            if self.content:
                self.content = "\n".join(p.get_text(strip=True) for p in  self.content)
                print("📄 Content Preview:\n",  self.content, "...")
            else:
                print("⚠️ 找不到文章內容")
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class DeutscheWelle (News):
    def _parse_article(self, soup):
        # Extract title
        title = soup.find("h1").get_text()
        self.title=simplifiedChineseToTraditionalChinese(title)

        # Extract content
        content_div = soup.find("div", class_="c17j8gzx rc0m0op r1ebneao s198y7xq rich-text li5mn0y r1r94ulj wngcpkw blt0baw")
        if content_div:
            paragraphs=content_div.find_all("p")
            self.content = simplifiedChineseToTraditionalChinese("\n".join(p.get_text(strip=True) for p in paragraphs))
        else:
            self.content = "No content found"

class HKFreePress(News):
    # Extract title
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"
        # Extract content
        content_div = soup.find("div",class_="entry-content")
        print("content_div:",content_div)
        if content_div:
            paragraphs = content_div.find_all("p",recursive=False)
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class WenWeiPo(News):
    def _parse_article(self, soup):
    # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",class_="post-content")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        # Extract images
        self.images = []
        image_div = soup.find("figure",class_="image align-center").find_all("img")
        for img in image_div:
            if img and img.has_attr("src"):
                self.images.append(img["src"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("time", class_="publish-date").get_text(strip=True)
        if date_div:
            print("date_div:", date_div)
            self.published_at = standardDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        self.authors = []
        login_div = soup.find("div", class_="articlelogin")
        if login_div:
            h2 = login_div.find("h2")
            if h2:
                authors_text = h2.get_text(strip=True)
                if authors_text:
                    for author in authors_text.split(" "):
                        if author and author != "明報記者":
                            self.authors.append(author.strip())
        print("self.authors:", self.authors)

class OrientalDailyNews(News):
    """Overrides parsing logic for a different HTML structure."""
    def _parse_article(self, soup):
        # Extract images
        self.images = []
        image_div = soup.find("div", class_="photo")
        if image_div:
            a = image_div.find("a")
            images = a.find_all('img') 
            # Get the first image
            self.images.append("https://orientaldaily.on.cc"+images[0]["src"]) if images else None
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("div", class_="site").get_text(strip=True) 
        if date_div:
            print("date_div:", date_div)
            self.published_at = standardChineseDatetoTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        self.authors = []
        login_div = soup.find("div", class_="articlelogin")
        if login_div:
            h2 = login_div.find("h2")
            if h2:
                authors_text = h2.get_text(strip=True)
                if authors_text:
                    for author in authors_text.split(" "):
                        if author and author != "明報記者":
                            self.authors.append(author.strip())
        print("self.authors:", self.authors)

        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("main")

        if content_div:
            paragraphs = content_div.find_all("div",class_="content")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class TaKungPao(News):
    """Overrides parsing logic for a different HTML structure."""
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("h1", class_="tkp_con_title")
        self.title = title_tag.get_text(strip=True) if title_tag else "No title"

        # Extract content
        content_div = soup.find("div",class_="tkp_content")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class HK01(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(str(self.url))
            print("Hello!")
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入
            # Scroll to the bottom repeatedly to load lazy content
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                # Calculate new scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # No more content
                last_height = new_height
            time.sleep(2)  # 等待 JS 載入
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
            print("self.title:", self.title)

            # Extract images
            print(soup.find("article", id="article-content-section"))
            images = soup.find("article", id="article-content-section").find_all("img")
            print("images:", images)
            for image in images:
                self.images.append(image["src"])

            # Extract published date
            date = soup.find("div", {"data-testid": "article-publish-info"}).find_all("time")[0].get_text(strip=True)
            self.published_at=standardDateToTimestamp(date)

            # Extract authors (no authors)
            self.authors = []
            self.authors.append(soup.find("div", {"data-testid": "article-author"}).find_all("span")[1].get_text(strip=True))

            # Extract content
            content_div = soup.find("article")
            if not content_div:
                content_div = soup.find("article", class_="news-text")

            if content_div:
                promo=content_div.find_all("strong")
                for p in promo:
                    p.decompose()
                paragraphs = content_div.find_all("p")
                self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
            else:
                self.content = "No content found"
            print("self.content:",self.content)

            if self.content:
                self.content = "\n".join(p.get_text(strip=True) for p in  self.content)
                print("📄 Content Preview:\n",  self.content, "...")
            else:
                print("⚠️ 找不到文章內容")
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class InitiumMedia(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",class_="entry-content")
        
        print("content_div:", content_div)
        if content_div:
            promo=content_div.find_all("div",class_="gutenberg-block block-explanation-note")
            for p in promo:
                p.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        
        # Extract images
        self.images = []
        image_div = soup.find("div",class_="w-full aspect-3/2 overflow-hidden")
        self.images.append(image_div.find("img")["src"])

        # Extract published date
        date_div = soup.find("div",class_="entry-author").find("time").get_text(strip=True)
        if date_div:
            self.published_at = IntiumChineseDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        self.authors = []
        intro = soup.find("div", class_="entry-author")
        self.authors.append(intro.find("p").get_text(strip=True).replace("端傳媒記者", "").strip())
        print("self.authors:", self.authors)


class YahooNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract images
        self.images = []
        image_div = soup.find("figure").find_all("img")
        for img in image_div:
            if img and img.has_attr("src"):
                self.images.append(img["src"])
        print("self.images:", self.images)

        # Extract published date
        date_div = soup.find("div", class_="caas-attr-time-style").find("time").get_text(strip=True) 
        print("date_div:", date_div)
        if date_div:
            print("date_div:", date_div)
            self.published_at = standardChineseDatetoTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        # self.authors = []
        # login_div = soup.find("div", class_="articlelogin")
        # if login_div:
        #     h2 = login_div.find("h2")
        #     if h2:
        #         authors_text = h2.get_text(strip=True)
        #         if authors_text:
        #             for author in authors_text.split(" "):
        #                 if author and author != "明報記者":
        #                     self.authors.append(author.strip())
        # print("self.authors:", self.authors)

        # Extract content
        content_div = soup.find("article")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            promo=content_div.find_all("strong")
            for p in promo:
                p.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class HKCD(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h2").get_text()

        # Extract content
        content_div = soup.find("div",class_="newsDetail")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

        #Extract published date
        print(soup.find("div",class_="newsDetailBox").find("div", class_="msg"))
        date=soup.find("div",class_="newsDetailBox").find("div", class_="msg").find_all("span")[1].get_text(strip=True)
        if date:
            print("date:", date)
            self.published_at = standardDateToTimestamp(date)
        print("self.published_at:", self.published_at)

        # Extract authors
        author=soup.find("div",class_="newsDetailBox").find("div", class_="msg").find_all("span")[0].find("font").get_text(strip=True)
        self.authors.append(author)

        # Extract images
        frontImage="https://www.hkcd.com.hk/"+soup.find("div", class_="poster").find("img")["src"]
        self.images.append(frontImage)
        print("self.images:", self.images)

        otherImages=soup.find("div", class_="newsDetail").find_all("img")
        print("otherImages:", otherImages)
        for image in otherImages:
            if image and image.has_attr("src"):
                self.images.append(image["src"])

class TheEpochTimes(News):
    def _parse_article(self, soup):
        # Extract title
        title = soup.find("div", class_="arttop arttop2") if soup.find("div", class_="arttop arttop2") else None
        print("title:", title)
        if title is None:
            title = soup.find("div", class_="titles")
        self.title=title.find("h1").get_text()

        # Extract content
        content_div = soup.find("div",class_="post_content") if soup.find("div",class_="post_content") else None

        if content_div is None:
            content_div = soup.find("div", id="artbody")

        if content_div:
            paragraph_p = content_div.find_all("p")
            paragraphs=[]
            for p in paragraph_p:
                if "責任編輯：" in p.get_text(strip=True):
                    continue
                paragraphs.append(p.get_text(strip=True))
            
            self.content = "\n".join(p for p in paragraphs)
        else:
            self.content = "No content found"
        print("self.content:", self.content)
        # Extract published date
        date_div = soup.find("div",class_="main_content")
        if date_div:
            date=date_div.find("div",class_="info").find("time").get_text(strip=True).replace("更新","").strip()
        if date_div is None:
            print("date_div:", date_div)
            date=soup.find("div",id="artbody").find("time").get_text(strip=True).replace("更新:","").strip()
        print("date:", date)
        self.published_at = standardDateToTimestamp(date)
        print("self.published_at:", self.published_at)

        # Extract authors
        content_div=content_div=soup.find("div",id="artbody").find_all("p")
        print("content_div:", content_div)
        if content_div:
            for p in content_div:
                print(p.get_text(strip=True))
                if "責任編輯：" in p.get_text(strip=True):
                    author_text = p.get_text(strip=True).replace("責任編輯：", "").strip()
                    if author_text:
                        self.authors.append(author_text)
            
        
        # Extract images
        print("Hello!")
        image = soup.find("div", class_="featured_image")
        print("image:", image)
        image  = image.find("img")["data-src"] if image and image.find("img") else None
        print("image:", image)

        if image is None:
            print("hello")
            image=soup.find("div", class_="arttop arttop2").find("img")["src"]

        if image:
            self.images.append(image)


class NowTV(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        content_div = soup.find("div",class_="newsLeading")
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

        # Extract images
        self.images = []
        image_div = soup.find("div",class_="colLeft entry-content")
        image_a=image_div.find_all("a",rel="galleryCollection")
        for img in image_a:
            if img and img.has_attr("href"):
                self.images.append(img["href"])

        # Extract published date
        date_div = soup.find("div",class_="newsTime").find("time", class_="published").get_text(strip=True)
        if date_div:
            print("NowTVDateToTimestamp(date_div):", NowTVDateToTimestamp(date_div))
            self.published_at = NowTVDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        # self.authors = []
        # login_div = soup.find("div", class_="articlelogin")
        # if login_div:
        #     h2 = login_div.find("h2")
        #     if h2:
        #         authors_text = h2.get_text(strip=True)
        #         if authors_text:
        #             for author in authors_text.split(" "):
        #                 if author and author != "明報記者":
        #                     self.authors.append(author.strip())
        # print("self.authors:", self.authors)

class ChineseBBC(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        content_div = soup.find("main")
        if content_div:
            paragraphs=content_div.find_all("p",dir="ltr")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class VOC(News):
    def _parse_article(self, soup):
        # Extract title
        title = soup.find("h1").get_text()
        self.title=simplifiedChineseToTraditionalChinese(title)

        # Extract content
        content_div = soup.find("div", id="article-content")
        if content_div:
            paragraphs=content_div.find_all("p")
            self.content = simplifiedChineseToTraditionalChinese("\n".join(p.get_text(strip=True) for p in paragraphs))
        else:
            self.content = "No content found"

class HKCourtNews(News):
    def _parse_article(self, soup):
        # Extract title
        print(soup.find("h1"))
        self.title = soup.find("h1").get_text()

        # Extract content
        content_div = soup.find("div",class_="elementor-element elementor-element-cd4b5e9 elementor-widget elementor-widget-theme-post-content")
        print("content_div:",content_div)
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

        # Extract images
        self.images = []
        image = soup.find("figure",class_="wp-block-image size-large").find("img")
        self.images.append(image["src"])

        # Extract published date
        print(soup.find_all("time"))
        date_time=soup.find_all("time")
        print("date_time:", date_time)
        time_array=[]
        for published_time in date_time:
            time_array.append(published_time.get_text(strip=True))
        time_format= " ".join(time_array)
        print("time_format:", time_format)
        print("TheCourtNewsDateToTimestamp(time_format):", TheCourtNewsDateToTimestamp(time_format))
        self.published_at = TheCourtNewsDateToTimestamp(time_format)

class ICable(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("article")

        if content_div:
            paragraphs = content_div.find_all("p",recursive=False)
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

        # Extract images
        image_div=soup.find("div", class_="post-image")
        if image_div:
             self.images.append(image_div.find("img")["data-src"])

        # Extract published date
        print(soup.find("div", class_="post-meta single-post-meta"))
        date = soup.find("div", class_="post-meta single-post-meta").find_all("li")[1].get_text(strip=True)
        print("date:", date)
        self.published_at = standardDateToTimestamp(date)

class HKGovernmentNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("h1",class_="news-title")
        print("title_tag:", title_tag)
        self.title = title_tag.get_text(strip=True) if title_tag else "No title"

        # Extract content
        content_div = soup.find("div",class_="newsdetail-content")
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        
        # Extract date
        date=soup.find("span", class_="news-date").get_text(strip=True)
        self.published_at=standardDateToTimestamp(date)

        # Extract image
        print(soup.find("div", class_="news-block news-block-3by2"))
        self.images.append("https://www.news.gov.hk/"+soup.find("div", class_="news-block news-block-3by2").find("img")["src"])
        print("self.images:", self.images)


# It uses Vue to fetch data with JavaScript
class OrangeNews(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(str(self.url))
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("h1").getText()
            self.content = soup.find("article").find_all("p")

            print("📰 Title:", self.title if self.title else "無標題")
            print("self.content:",self.content)

            if self.content:
                self.content = "\n".join(p.get_text(strip=True) for p in  self.content)
                print("📄 Content Preview:\n",  self.content, "...")
            else:
                print("⚠️ 找不到文章內容")

            # extract published date
            date=soup.find("div", class_="info").find("span", class_="time fr").get_text(strip=True)
            self.published_at=standardDateToTimestamp(date)
            print("self.published_at:",self.published_at)

            # extract authors
            span_elements=soup.find("div", class_="info").find_all("span")
            print("span_elements:", span_elements)
            for span in span_elements:
                classes = span.get("class", [])
                if "time" in classes and "fr" in classes:
                    continue
                text=span.get_text(strip=True)
                text = text.replace("責編：", "").replace("編輯：", "")
                self.authors.append(text)
            
            # extract images
            self.images.append(soup.find("div", class_="details").find("img")["src"])
            print("self.images:", self.images)


        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class TheStandard(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(str(self.url))
            print("Hello!")
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入
            # Scroll to the bottom repeatedly to load lazy content
            last_height = driver.execute_script("return document.body.scrollHeight")

            while True:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                # Calculate new scroll height
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # No more content
                last_height = new_height
            time.sleep(2)  # 等待 JS 載入
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
            print("self.title:", self.title)

            # Extract images
            images = soup.find("div", class_="article-detail__text-section").find_all("img")
            for image in images:
                self.images.append(image["src"])
            print("self.images:", self.images)

            # Extract published date
            date = soup.find("div", class_="list-item__date-time common").get_text(strip=True)
            self.published_at=SCMPDateToTimestamp(date)
            print("self.published_at:", self.published_at)

            # Extract authors (no authors)
            # self.authors = []
            # self.authors.append(soup.find("div", {"data-testid": "article-author"}).find_all("span")[1].get_text(strip=True))

            # Extract content
            text = soup.find("div",class_="article-detail__text-section")
            text.find("div",class_="article-detail__footer").decompose()  # 移除標題部分
            content_div= text.find_all("p")
            print("content_div:",content_div)

            if content_div:
                self.content = "\n".join(p.get_text(strip=True) for p in content_div)
                print("📄 Content Preview:\n",  self.content, "...")
            else:
                print("⚠️ 找不到文章內容")
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class HKEJ(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("h1", id="article-title")
        self.title = title_tag.get_text() if title_tag else "No title found"

        # Extract published date
        if soup.find("p", class_="info").find("span",class_="date"):
            date = soup.find("p", class_="info").find("span",class_="date").get_text(strip=True)
        elif soup.find("div",id="article-detail-wrapper").find("p"):
            date = soup.find("div",id="article-detail-wrapper").find("p").get_text(strip=True)
        print("date:", date)
        self.published_at = HKEJDateToTimestamp(date)
        print("self.published_at:", self.published_at)

        # Extract authors (no authors)
        author=soup.find("p", class_="info").find("span",class_="author")
        print("author:", author)
        if author:
            self.authors = [author.get_text(strip=True)]


        # Extract content
        if soup.find("div",id="article-content"):
            content_div = soup.find("div", id="article-content")
        elif soup.find("div", id="article-detail-wrapper"):
            # If the content is in a different div
            content_div = soup.find("div", id="article-detail-wrapper")
        print("content_div:", content_div)
        if content_div:
            paragraphs = content_div.find_all("p")
            print("paragraphs:",paragraphs)
            filtered_paragraphs = [
                p for p in paragraphs
                if p.get("id") != "date" and p.get("class") != ["info"]
            ]
            self.content = "\n".join(p.get_text(strip=True) for p in filtered_paragraphs if p.get_text(strip=True)
)
        else:
            self.content = "No content found"
        print("self.content:", self.content)

class HKET(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",class_="article-detail-content-container")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class RTHK(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",class_="itemFullText")

        if content_div:
            # Replace <br> with newline so text is readable
            for br in content_div.find_all("br"):
                br.replace_with("\n")
            self.content = content_div.get_text(strip=True, separator="\n")
        else:
            self.content = "No content found"
        
        # Extract images
        self.images = []
        image_div = soup.find("div",class_="itemSlideShow")
        images=image_div.find_all("img")
        self.images.append(images[1]["src"])

        # Extract published date
        date_div = soup.find("div",class_="createddate").get_text(strip=True)
        if date_div:
            self.published_at = RTHKChineseDateToTimestamp(date_div)
        else:
            self.published_at = None
        print("self.published_at:", self.published_at)

        # Extract authors
        # self.authors = []
        # login_div = soup.find("div", class_="articlelogin")
        # if login_div:
        #     h2 = login_div.find("h2")
        #     if h2:
        #         authors_text = h2.get_text(strip=True)
        #         if authors_text:
        #             for author in authors_text.split(" "):
        #                 if author and author != "明報記者":
        #                     self.authors.append(author.strip())
        # print("self.authors:", self.authors)

class TheWitness(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            # Anti-detection script
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                    });
                """
            })
            
            print("🔗 嘗試連線至：", self.url)
            driver.get(str(self.url))
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Ensure string fields are never None
            title_meta = soup.find("meta", property="og:title")
            self.title = title_meta["content"] if title_meta and title_meta.get("content") else "No title found"

            content_div = soup.find_all("p")
            self.content = "\n".join([p.get_text(strip=True) for p in content_div]) or "No content found"

            print("📰 Title:", self.title)
            print("📝 Subtitle:", self.subtitle)
            print("self.content:", self.content)

            # Handle images safely
            img_div = soup.find("div", class_="elementor-element elementor-element-63ce06d5 elementor-widget elementor-widget-theme-post-featured-image elementor-widget-image")
            if img_div:
                img = img_div.find("img")
                if img and img.get("data-src"):
                    self.images.append(img["data-src"])
            print("self.images:", self.images)

            # Handle date safely
            date_ul = soup.find("ul", class_="elementor-inline-items elementor-icon-list-items elementor-post-info")
            if date_ul:
                lists = date_ul.find_all("li")
                if len(lists) >= 2:
                    date = lists[0].get_text(strip=True) + " " + lists[1].get_text(strip=True)
                    print("date:", date)
                    self.published_at = standardDateToTimestamp(date)
                    print("self.published_at:", self.published_at)

        except Exception as e:
            print("❌ 錯誤：", e)
            # Ensure critical fields have defaults even if parsing fails
            self.title = self.title if hasattr(self, 'title') else "無標題"
            self.subtitle = self.subtitle if hasattr(self, 'subtitle') else "無副標題"
            self.content = self.content if hasattr(self, 'content') else "無內容"
            
        finally:
            driver.quit()

# They use anti-bot mechanism to prevent web scraping
class InMediaHK(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = undetected_chromedriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("meta", property="og:title")
            self.subtitle = soup.find("meta", property="og:description")
            self.article = soup.find("article")

            print("📰 Title:", self.title["content"] if self.title else "無標題")
            print("📝 Subtitle:", self.subtitle["content"] if self.subtitle else "無副標題")

            if self.article:
                paragraphs = self.article.find_all("p")
                text = "\n".join(p.get_text(strip=True) for p in paragraphs)
                print("📄 Content Preview:\n", text, "...")
            else:
                print("⚠️ 找不到文章內容")
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

# China News Media
class PeopleDaily(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("div",class_="col col-1 fl").find("h1").get_text()

        # Extract content
        content_div = soup.find("div",class_="rm_txt_con cf")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"


class XinhuaNewsAgency(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        content_div = soup.find("span",id="detailContent")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class GlobalTimes(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("div",class_="article_title").get_text()

        # Extract content
        self.content = soup.find("div",class_="article_right").get_text()

        # if content_div:
        #     paragraphs = content_div.find_all("p")
        #     self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        # else:
        #     self.content = "No content found"

class CCTV(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("div",class_="article_title").get_text()

        # Extract content
        self.content = soup.find("div",class_="article_right").get_text()


# Taiwanese News
class UnitedDailyNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract content
        content_div = soup.find("article")
        if content_div is None:
            content_div = soup.find("div", class_="article-content__paragraph")

        if content_div:
            figCaptions=content_div.find_all("figcaption")
            for caption in figCaptions:
                caption.decompose()
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        print("self.content:",self.content)

        # Extract authors (no authors)
        author_selectors = [
            {"selector": "div.article-section__info span.article-section__author"},
            {"selector": "div.article-content__subinfo--authors.story_bady_info_author span:nth-of-type(2)"},
            {"selector": "div.article-content__subinfo--authors.story_bady_info_author span.article-content__author"},
            {"selector": "section.authors span.article-content__author"},
            # New selector for 文／ pattern
            {
                "selector": "*:-soup-contains('文／')",  # Targets any element containing "文／"
                "process": lambda el: (
                    el.get_text(strip=True)                # Get full text
                    .split("文／")[-1]                     # Take text after "文／"
                    .split()[0]                           # Take first word (removes trailing junk)
                    .strip()
                ),
                "fallback": True  # Only use if other selectors fail
            }
        ]
    
        for selector in author_selectors:
            element = soup.select_one(selector["selector"])
            if element:
                author_text = element.get_text(strip=True)
                print("author_text:",author_text)
                print("author_text:",author_text)
                if author_text and author_text!="":
                    # Clean up the author text
                    author_text = author_text.replace("綜合外電","").replace("編譯","").replace("聯合報", "").replace("經濟日報","").replace("聯合新聞網","").replace("台北","").replace("台中","").replace("記者","").replace("即時報導","").replace("udn STYLE", "").replace("撰文","").replace("／", "").strip()
                    print("author_text:", author_text)
                    self.authors.append(author_text)
        print("self.authors:", self.authors)

        # Extract published date
        date_selectors=[
            {"selector": "div.article-section__info time", "attribute": "datetime"},  # Preferred - time tag with datetime attribute
            {"selector": "span.article-content__subinfo--time", "text": True},
            {"selector": "time.article-content__time", "text": True},
            {"selector":"div.story_bady_info_author","process": lambda el: next(
            (text.strip() for text in el.stripped_strings if "/" in text), 
            None
        )}
        ]
        for selector in date_selectors:
            element = soup.select_one(selector["selector"])
            if element:
                if "process" in selector:
                    date = selector["process"](element)
                    self.published_at = standardDateToTimestamp(date)
                else: 
                    date=element.get_text(strip=True)
                    self.published_at = standardDateToTimestamp(date)

        print("self.published_at:", self.published_at)

        # Extract images
        self.images = []
        image_div = soup.find_all("figure")
        if image_div:
            for pictures in image_div:
                img = pictures.find("img")
                if img and img.has_attr("src"):
                    self.images.append(img["src"])
                if img and img.has_attr("data-src"):
                    self.images.append(img["data-src"])
        print("self.images:", self.images)


class LibertyTimesNet(News):
     def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="text boxTitle boxText").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class ChinaTimes(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("h1", class_="article-title").get_text()
            self.content = soup.find_all("p")
            self.content="\n".join(p.get_text(strip=True) for p in  self.content)

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class CNA(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        paragraphs = soup.find("div",class_="paragraph").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class TaiwanEconomicTimes(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        paragraphs = soup.find("section",class_="article-body__editor").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class PTSNews(News):
    pass

class CTEE(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("h1").get_text()
            self.content = soup.find("article").find_all("p")
            self.content="\n".join(p.get_text(strip=True) for p in  self.content)

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class MyPeopleVol(News):
    pass

class TaiwanTimes(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag else "No title found"
            content_div = soup.find("div", class_="detail-text logo-size main-text-color margin-bottom")
            if content_div:
                # Get text with line breaks preserved
                texts = [line.strip() for line in content_div.stripped_strings]
                self.content = "\n".join(texts)
            else:
                self.content = "No content found"

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class ChinaDailyNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="elementor-element elementor-element-b93c196 elementor-widget elementor-widget-theme-post-content")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class SETN(News):
    pass

class NextAppleNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="post-content").find_all("p", recursive=False)
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class MirrorMedia(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("section", class_="article-content__Wrapper-sc-a27b9208-0 hWzglx").find_all("span")
        seen = set()
        unique_paragraphs = []
        for span in paragraphs:
            text = span.get_text(strip=True)
            if text not in seen:
                seen.add(text)
                unique_paragraphs.append(text)
        self.content = "\n".join(unique_paragraphs)

class NowNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div", id="articleContent")
        if content_div:
            outer_texts = [
                str(item).strip()
                for item in content_div.contents
                if isinstance(item, str)
            ]
            self.content = "\n".join(t for t in outer_texts if t)
        else:
            self.content = "No content found"

class StormMedia(News):
    pass

class TVBS(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

         # Extract content
        content_div = soup.find("div", class_="article_content")
        if content_div:
            # Remove decorative spans/links
            for span in content_div.find_all("strong"):
                span.decompose()

            # Remove centered divs used for styling
            for div in content_div.find_all("div", align=True):
                div.unwrap()

            # Remove the unwanted promotional block
            promo_div = content_div.find("div", class_="widely_declared")
            print("promo_div:",promo_div)
            if promo_div:
                promo_div.decompose()

            self.content = content_div.get_text(separator="\n", strip=True)
        else:
            self.content = "No content found"

class EBCNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div", class_="article_content")
        # Get rid of ads
        for promo in content_div.find_all("div",class_="inline_box"):
            promo.decompose()
        for promo in content_div.find_all("a"):
            promo.decompose()
        paragraphs=content_div.find_all("p")
        self.content = "\n".join(
            p.get_text(strip=True)
            for p in paragraphs
            if p.get_text(strip=True)  # 過濾空段落
        )

class ETtoday(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1", class_="title").get_text()
        print("self.title:", self.title)

        # Extract content
        content_selectors=[
             {"selector": "article", "text": True}, 
             {"selector":"div.story","text": True}
        ]
        for selector in content_selectors:
            element = soup.select_one(selector["selector"])
            promo=element.find("div",class_="et_social_2")
            if promo:
                promo.decompose()
            paragraphs = element.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract authors (no authors)
        authors_selectors=[
             {"selector": "div.subject_article", "text": True}, 
             {"selector":"div.story","text": True}
        ]
        for selector in authors_selectors:
            element = soup.select_one(selector["selector"])
            isOutLoopReadyToBreak=False
            print("element:",element)
            if element:
                for p in element.find_all('p'):
                    text = p.get_text()
                    # Match pattern: "記者" followed by name, then "／"
                    match = re.search(r'^記者(.+?)／', text)
                    if match:
                        journalist_name = match.group(1).strip()  # .strip() removes extra whitespace
                        self.authors.append(journalist_name)  # Output: 廖翊慈
                        isOutLoopReadyToBreak=True
                        break
            if isOutLoopReadyToBreak==True:
                break

        # Extract published date
        date_selectors=[
            {"selector": "time.date", "text": True}, 
        ]
        for selector in date_selectors:
            element = soup.select_one(selector["selector"])
            if element:
                    date=element.get_text(strip=True)
                    self.published_at = standardDateToTimestamp(date)

        print("self.published_at:", self.published_at)

        # Extract images
        self.images = []
        image_div = soup.find("div",class_="story").find("img")
        print("image_div:",image_div)
        if image_div:
            self.images.append(image_div["src"])
        print("self.images:", self.images)

class NewTalk(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="articleBody clearfix").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

class FTV(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def _parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=options)

        # 加上防偵測腳本
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
                });
            """
        })
        driver.execute_script("""
            let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
            modals.forEach(el => el.remove());
        """)

        # 建議測試短網址，避免過長導致連線問題
        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(self.url)
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag else "No title found"

            content_div = soup.find("div", id="newscontent")
            print("content_div:",content_div)
            for promo in content_div.find_all("strong"):
                promo.decompose()
            if content_div:
                # Get text with line breaks preserved
                texts = [line.strip() for line in content_div.stripped_strings]
                self.content = "\n".join(texts)
            else:
                self.content = "No content found"

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()