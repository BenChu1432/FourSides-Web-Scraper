import re
from typing import Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import undetected_chromedriver 
import datetime
# from translation import translate_text
from util.timeUtil import HKEJDateToTimestamp, IntiumChineseDateToTimestamp, NowTVDateToTimestamp, RTHKChineseDateToTimestamp, SCMPDateToTimestamp, SingTaoDailyChineseDateToTimestamp, TheCourtNewsDateToTimestamp, standardChineseDatetoTimestamp, standardDateToTimestamp
from webScraper.simplifiedChineseToTraditionalChinese import simplifiedChineseToTraditionalChinese

# Constants
WAITING_TIME_FOR_JS_TO_FETCH_DATA=0


class News(ABC):
    title: Optional[str]
    content: Optional[str]
    published_at: Optional[int]
    origin: Optional[int]
    authors: List[str]
    images: List[str]
    origin: Optional[str]

    def __init__(self, url=None):
        self.url = url
        self.title = None
        self.content = None
        self.published_at=None
        self.origin="native"
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
            driver.get(str(self.url))
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

            # Extract publication date and authors
            byline=soup.find("div",class_="byline")
            if byline:
                date_time=byline.find("time")
                authors_address=byline.find("address")
                if date_time:
                    date=date_time.get_text()
                    self.published_at=standardChineseDatetoTimestamp(date)
                if authors_address:
                    authors_text=authors_address.get_text()
                    authors=authors_text.split(",")
                    self.authors=authors

            # Extract images
            figure=soup.find("figure",class_="article-span-photo")
            if figure:
                image=figure.find("img")
                if image:
                    src=image['src']
                    self.images.append(src)
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class DeutscheWelle (News):
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
            time.sleep(0)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
        # def _parse_article(self,soup):
            title = soup.find("h1").get_text()
            self.title=simplifiedChineseToTraditionalChinese(title)

            # Extract content
            content_div = soup.find("div", class_="c17j8gzx")
            if content_div:
                paragraphs=content_div.find_all("p")
                self.content = simplifiedChineseToTraditionalChinese("\n".join(p.get_text(strip=True) for p in paragraphs))
            else:
                self.content = "No content found"

            # Extract publication
            date_span=soup.find("span",class_="publication")
            if date_span:
                date=date_span.find("time")
                date=date.get_text()
                self.published_at=standardChineseDatetoTimestamp(date)

            # Extract author
            a=soup.find('a',class_="author")
            if a:
                name=a.get_text()
                self.authors.append(name)

            # Extract images
            picture=soup.find("picture",class_="s9gezr6")
            print('picture:',picture)
            if picture:
                image=picture.find('img')
                if image:
                    srcset=image["srcset"]
                    # print("srcset:",srcset)
                    sources=srcset.split(",")
                    # print("sources:",sources)
                    source_and_width=sources[len(sources)-1]
                    source_and_width_list=source_and_width.split()
                    source=source_and_width_list[0]
                    self.images.append(source)

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

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
        
        # Extract author
        author_span=soup.find("span",class_="bbc-1orxave")
        if author_span:
            author=author_span.get_text()
            self.authors.append(author)

        # Extract publication date
        date_time=soup.find("time",class_="bbc-xvuncs e1mklfmt0")
        if date_time:
            date=date_time["datetime"]
            self.published_at=standardDateToTimestamp(date)

        # Extract images
        main=soup.find("main",{"role":"main"})
        recommendations_heading=main.find("section",{"data-e2e":"recommendations-heading"})
        if recommendations_heading:
            recommendations_heading.decompose()
        print("main:",main)
        if main:
            images=main.find_all("img")
            print("images:",images)
            for image in images:
                image=image["src"]
                self.images.append(image)

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
        
        # Extract date
        publication_date=soup.find("time",{"pubdate":"pubdate"})
        if publication_date:
            date=publication_date.get_text()
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        author_link=soup.find("a",class_="links__item-link")
        if author_link:
            name=author_link.get_text()
            self.authors.append(name)

        # Extract images
        image_div=soup.find("div",class_="cover-media")
        if image_div:
            image=image_div.find("img")
            if image:
                src=image['src']
                modified_url = re.sub(r'_w\d+', f'_w{1000}', src)
                self.images.append(modified_url)
        print(self.images)

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
    #  def _fetch_and_parse(self):
    #     self._parse_article()

    # def _parse_article(self):
    #     # 使用非 headless 模式（可視化）
    #     options = undetected_chromedriver.ChromeOptions()
    #     options.add_argument("--headless")
    #     options.add_argument("--disable-gpu")
    #     options.add_argument("--no-sandbox")
    #     options.add_argument("--window-size=1280,800")
    #     options.add_argument("--disable-blink-features=AutomationControlled")
    #     options.add_experimental_option("excludeSwitches", ["enable-automation"])
    #     options.add_experimental_option("useAutomationExtension", False)
    #     options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    #     driver = webdriver.Chrome(options=options)

    #     # 加上防偵測腳本
    #     driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #         "source": """
    #             Object.defineProperty(navigator, 'webdriver', {
    #             get: () => undefined
    #             });
    #         """
    #     })
    #     driver.execute_script("""
    #         let modals = document.querySelectorAll('.popup, .modal, .ad, .overlay, .vjs-modal');
    #         modals.forEach(el => el.remove());
    #     """)

    #     # 建議測試短網址，避免過長導致連線問題
    #     print("🔗 嘗試連線至：", self.url)

    #     try:
    #         driver.get(str(self.url))
    #         time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

    #         html = driver.page_source
    #         soup = BeautifulSoup(html, "html.parser")
    #         # Extract title
    #         title_tag = soup.find("meta", property="og:title")
    #         self.title = title_tag["content"].strip() if title_tag else "No title found"

    #         # Extract content
    #         content_selectors=[
    #             {"selector": "div.whitecon.article[data-page='1']"},
    #             {"selector": "div.text",},  # Preferred - time tag with datetime attribute
    #         ]
    #         for selector in content_selectors:
    #             element=soup.select_one(selector["selector"])
    #             if element:
    #                 appPromo=element.find("p",class_="appE1121")
    #                 captions=element.find_all("span",class_="ph_d")
    #                 if appPromo:
    #                     appPromo.decompose()
    #                 if captions:
    #                     for caption in captions:
    #                         caption.decompose()
    #                 content_div=element.find_all(["p","h"])   
    #                 self.content = "\n".join(p.get_text(strip=True) for p in content_div)
    #                 break

    #         # Extract published date
    #         date_selector=[
    #             {"selector": "div.article div.function","text": True},  # Preferred - time tag with datetime attribute
    #             {"selector": "span.time","text": True}
    #         ]
    #         for selector in date_selector:
    #             element=soup.select_one(selector["selector"])
    #             print("element:",element)
    #             date=element.get_text()
    #             self.published_at=standardDateToTimestamp(date)
    #         print("self.published_at:",self.published_at)

    #         # Extract images
    #         images=soup.find("div",class_="text").find_all("img")
    #         for image in images:
    #             self.images.append(image["data-src"])
    
    #     except Exception as e:
    #         print("❌ 錯誤：", e)
        
    #     driver.quit()
     def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_selectors=[
            # {"selector":"div.article"},
            {"selector": "div.whitecon.article[data-page='1']"},
            {"selector": "div.text",},  # Preferred - time tag with datetime attribute
        ]
        for selector in content_selectors:
            element=soup.select_one(selector["selector"])
            print("element:",element)
            # if element and len(element)>1:
            #     element=element[0]
            if element:
                appPromo=element.find("p",class_="appE1121")
                captions=element.find_all("span",class_="ph_d")
                if appPromo:
                    appPromo.decompose()
                if captions:
                    for caption in captions:
                        caption.decompose()
                content_div=element.find_all(["p","h"])   
                self.content = "\n".join(p.get_text(strip=True) for p in content_div)
                break

        # Extract published date
        date_selector=[
            {"selector": "div.whitecon.article[data-page='1'] span.time",},  # Preferred - time tag with datetime attribute
            {"selector": "span.time","text": True}
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                date=element.get_text()
                self.published_at=standardDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract images
        image_selectors=[
             {"selector": "div.whitecon.article[data-page='1']"}, 
             {"selector": "div.article-wrap div.text","data-desc":"內容頁"}, 
             {"selector": "div.text"}, 
        ]
        for selector in image_selectors:
            element=soup.select_one(selector["selector"])
            # print("element:",element)
            isReadyToBreak=False
            if element:
                images=element.find_all("img")
                for image in images:
                    self.images.append(image["data-src"])
                isReadyToBreak=True
            if isReadyToBreak==True:
                break

        # Extract authors (no authors)
        authors_selectors=[
             {"selector": "div.whitecon.article[data-page='1']"}, 
             {"selector": "div.whitecon.article[itemprop='articleBody'] .text.boxText"}
        ]
        for selector in authors_selectors:
            element = soup.select_one(selector["selector"])
            isOutLoopReadyToBreak = False

            if element:
                for p in element.find_all('p'):
                    text = p.get_text()

                    # Pattern 1: 記者[Name]／
                    match = re.search(r'記者(\w{2,4})／', text)
                    if match:
                        self.authors.append(match.group(1).strip())
                        isOutLoopReadyToBreak = True
                        break  # Stop after first match

                    # Pattern 2: [Name]／核稿編輯
                    match = re.search(r'(\w{2,4})／核稿編輯', text)
                    if match:
                        self.authors.append(match.group(1).strip())
                        isOutLoopReadyToBreak = True
                        break  # Stop after first match

            if isOutLoopReadyToBreak:
                break





class ChinaTimes(News):
    def _fetch_and_parse(self):
        self._parse_article()

    def get_article_urls(self, max_pages=5):
        base_url = "https://www.chinatimes.com/realtimenews/?chdtv"

        # Set up headless Chrome
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

        all_urls = []

        try:
            for page in range(1, max_pages + 1):
                url = f"{base_url}/?page={page}"

                print(f"Loading page: {url}")
                driver.get(url)
                time.sleep(2)  # wait for JS to load

                soup = BeautifulSoup(driver.page_source, "html.parser")

                articles = soup.select("ul.vertical-list li")
                if not articles:
                    print("No more articles.")
                    break

                stop = False
                for article in articles:
                    a_tag = article.select_one("h3.title a")
                    if a_tag:
                        href = a_tag['href']
                        url="https://www.chinatimes.com"+href
                        print("full_url:",url)
                        all_urls.append(url)

                if stop:
                    break

        finally:
         driver.quit()

        return all_urls

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

            title_h1=soup.find("h1", class_="article-title")
            if title_h1:
                self.title=title_h1.get_text()
            content_div = soup.find("article")
            if content_div:
                # Safely remove elements if they exist
                comments_section = content_div.find("section", class_="comments")
                if comments_section:
                    comments_section.decompose()

                newsletter_div = content_div.find("div", class_="subscribe-news-letter")
                if newsletter_div:
                    newsletter_div.decompose()

                # Extract paragraphs
                content_p = content_div.find_all("p")
                print("content_p:", content_p)

                # Join all paragraph texts together
                all_text = "\n".join(p.get_text(strip=True) for p in content_p if p)
                self.content = all_text

            # Extract published date
            meta_info = soup.find("div", class_="meta-info")
            if meta_info:
                time_tag = meta_info.find("time")
                if time_tag and time_tag.has_attr('datetime'):
                    date = time_tag['datetime']  # Correct way to access the attribute
                    print("date:", date)
                    self.published_at = standardDateToTimestamp(date)
                else:
                    print("No datetime attribute found in time tag")
            else:
                print("No meta-info div found")
            
            # Extract author
            author_div=soup.find("div",class_="author")
            if author_div:
                author=author_div.get_text(strip=True)
                self.authors.append(author)

            # Extract images
            photoContainer=soup.find("div",class_="photo-container")
            if photoContainer:
                image=photoContainer.find("img")["src"]
                self.images.append(image)

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

        # Extract published date
        date_selector=[
            {"selector": "div.updatetime span:first-child",},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                date=element.get_text()
                self.published_at=standardDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract images
        date_selector=[
            {"selector": "figure.center img","attr": "src"},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                self.images.append(element["src"])
                break
        print("self.published_at:",self.published_at)

        # Extract authors
        date_selector=[
            {"selector": "div.paragraph"},
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            # print("element:",element)
            if element:
                paragraphs=element.find_all('p')
                for paragraph in paragraphs:
                    text=paragraph.get_text()
                    print("text:",text)
                    # 1. First, try to extract the journalist name (primary author)
                    journalist_match = re.search(r'（中央社記者([\u4e00-\u9fff]{2,4})', text)
                    if journalist_match:
                        self.authors.append(journalist_match.group(1))
                    
                    # 2. Fallback: Check for editor names (only if no journalist is found)
                    editor_match = re.search(r'編輯：([\u4e00-\u9fff]{2,4})', text)
                    if editor_match and not self.authors:  # Avoid adding editors if journalist exists
                        self.authors.append(editor_match.group(1))
                break

class TaiwanEconomicTimes(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        paragraphs = soup.find("section",class_="article-body__editor").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        date_selector=[
            {"selector": "time.article-body__time",},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                date=element.get_text()
                self.published_at=standardDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract authors
        date_selector=[
            {"selector": "div.article-body__info span"},
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            print("element:",element)
            if element:
                text=element.get_text()
                print("text:",text)
                # 1. First, try to extract the journalist name (primary author)
                journalist_match = re.search(r'中央社 記者([\u4e00-\u9fff]{2,3})', text)
                if journalist_match:
                    self.authors.append(journalist_match.group(1))
                
                # 1. First, try to extract the journalist name (primary author)
                journalist_match = re.search(r'經濟日報 編譯([\u4e00-\u9fff]{2,3})', text)
                if journalist_match:
                    self.authors.append(journalist_match.group(1))

        # Extract images
        date_selector=[
            {"selector": "figure.article-image img"},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                self.images.append(element["src"])
                break
        print("self.published_at:",self.published_at)

class PTSNews(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content
        paragraphs = soup.find("div",class_="post-article").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        date_selector=[
            {"selector": "span.text-nowrap time",},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            print("element:",element)
            if element:
                date=element.get_text()
                self.published_at=standardDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract authors
        date_selector=[
            {"selector": "div.article_authors div.reporter-container"},
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            print("element:",element)
            if element:
                a_elements=element.find_all("a")
                print("a_elements:",a_elements)
                for a_element in a_elements:
                    text=a_element.get_text()
                    self.authors.append(text)
                # # 1. First, try to extract the journalist name (primary author)
                # journalist_match = re.search(r'中央社 記者([\u4e00-\u9fff]{2,3})', text)
                # if journalist_match:
                #     self.authors.append(journalist_match.group(1))
                
                # # 1. First, try to extract the journalist name (primary author)
                # journalist_match = re.search(r'經濟日報 編譯([\u4e00-\u9fff]{2,3})', text)
                # if journalist_match:
                #     self.authors.append(journalist_match.group(1))

        # Extract images
        date_selector=[
            {"selector": "figure img"},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                self.images.append(element["src"])
                break

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
            driver.get(str(self.url))
            time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            self.title = soup.find("h1").get_text()
            self.content = soup.find("article").find_all("p")
            self.content="\n".join(p.get_text(strip=True) for p in  self.content)

            # Extract published date
            date_selector=[
                {"selector": "ul.news-credit",},  # Preferred - time tag with datetime attribute
            ]
            for selector in date_selector:
                element=soup.select_one(selector["selector"])
                print("element:",element)
                if element:
                    lists=element.find_all("li")
                    date=lists[0].get_text()+lists[1].get_text()
                    self.published_at=standardDateToTimestamp(date)
                    break
            print("self.published_at:",self.published_at)

            # Extract authors
            date_selector=[
                {"selector": "span.name",}, 
            ]
            for selector in date_selector:
                element=soup.select_one(selector["selector"])
                print("element:",element)
                if element:
                    author=element.get_text().strip()
                    print("author:",author)
                    self.authors.append(author)
                    break
                    # # 1. First, try to extract the journalist name (primary author)
                    # journalist_match = re.search(r'中央社 記者([\u4e00-\u9fff]{2,3})', text)
                    # if journalist_match:
                    #     self.authors.append(journalist_match.group(1))
                    
                    # # 1. First, try to extract the journalist name (primary author)
                    # journalist_match = re.search(r'經濟日報 編譯([\u4e00-\u9fff]{2,3})', text)
                    # if journalist_match:
                    #     self.authors.append(journalist_match.group(1))

            # Extract images
            date_selector=[
                {"selector": "figure img"},  # Preferred - time tag with datetime attribute
            ]
            for selector in date_selector:
                element=soup.select_one(selector["selector"])
                if element:
                    self.images.append(element["src"])
                    break

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class MyPeopleVol(News):
    def _parse_article(self, soup):
        # remove promo
        [s.decompose() for s in soup.select('[class*="tdm-descr"]')]

        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content + authors + images
        p_elements = soup.find_all("p")
        # content
        filtered_p = [
            p.get_text(strip=True)
            for p in p_elements
            if 'comment-form-cookies-consent' not in p.get('class', [])
        ]
        self.content = "\n".join(filtered_p)
        text = self.content
        print("self.content:",self.content)
        # author
        journalist_match = re.search(r'【記者([\u4e00-\u9fff]{2,3})', text)
        if journalist_match:
            self.authors.append(journalist_match.group(1))
        journalist_match= re.search(r'【民眾網([\u4e00-\u9fff]{2,3})', text)
        if journalist_match:
            self.authors.append(journalist_match.group(1))
        image_selectors = [
            {"selector": "figure img"},  # Preferred
            {
                "selector": "div.td_block_wrap.tdb_single_content.tdi_50.td-pb-border-top"
                            ".td_block_template_1.td-post-content.tagdiv-type img"
            }
        ]

        for selector in image_selectors:
            elements = soup.select(selector["selector"])  # Use select() to get all matches
            print("elements:", elements)
            if elements:
                self.images.extend([img["src"] for img in elements if img.has_attr("src")])
                break  # Stop after first successful selector

        # Extract published date
        date_selector=[
            {"selector": "time",},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                date=element.get_text()
                self.published_at=standardDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract images
        image_selector=[
            {"selector": "figure.article-image img"},  # Preferred - time tag with datetime attribute
        ]
        for selector in image_selector:
            element=soup.select_one(selector["selector"])
            if element:
                self.images.append(element["src"])
                break

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
            driver.get(str(self.url))
            time.sleep(1)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            self.title = soup.find("div",class_="detail-header").get_text()
            print("self.title:",self.title)

            # Extract content
            content_div = soup.find("div", class_="detail-text logo-size main-text-color margin-bottom")
            if content_div:
                # Get text with line breaks preserved
                texts = [line.strip() for line in content_div.stripped_strings]
                self.content = "\n".join(texts)
            else:
                self.content = "No content found"
            print("self.content:",self.content)

            # Extract published date
            other_info_elements=soup.find_all("div",class_="otherinfo normal-size main-text-color")
            date=other_info_elements[0]
            if date:
                self.published_at=standardDateToTimestamp(date.get_text())

            # Extract author
            author=other_info_elements[1].get_text()
            if author:
                journalist_match = re.search(r'記者([\u4e00-\u9fff]{2,3})', author)
                if journalist_match:
                    self.authors.append(journalist_match.group(1))

            # Extract images
            image_selector=[
                {"selector": 'div[itemprop="articleBody"]'}, 
                {"selector":"div.detail-wrapper"}
            ]
            for selector in image_selector:
                element=soup.select_one(selector["selector"])
                print("element:",element)
                if element:
                    images=element.find_all("img")
                    for image in images:
                        self.images.append(image["src"])
                    break

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
        passage = "\n".join(p.get_text(strip=True) for p in paragraphs)
        self.content=passage.strip()

        # Extract date
        date=soup.find("span",class_="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-date").get_text()
        self.published_at=standardDateToTimestamp(date)
        
        # Extract images
        image_selectors=[
            {"selector": 'figure'}, 
        ]
        for selector in image_selectors:
                element=soup.select_one(selector["selector"])
                print("element:",element)
                if element:
                    images=element.find_all("img")
                    for image in images:
                        self.images.append(image["src"])
                    break
        soup.find("self.images:",self.images)

        # Extract author
        div_element = soup.find("div", class_="elementor-element elementor-element-b93c196 elementor-widget elementor-widget-theme-post-content")
        p_elements = div_element.find_all("p")
        if p_elements:
            # Get the full text from the first <p> tag
            raw_text = p_elements[0].get_text()
            
            # Check which name format is present
            if '記者' in raw_text and ('∕' in raw_text or '/' in raw_text):
                # Case 1: "記者王超群∕台北報導"
                # This removes the "記者" prefix, splits the string at the slash,
                # and takes the first part (the name).
                name = raw_text.replace('記者', '').split('∕')[0]
            else:
                # Case 2: "王崑義"
                # The entire string is the name.
                name = raw_text
            self.authors.append(name.strip())

        # for element in p_elements:
        #     text=element.get_text()
        #     print("text:",text)
        #     journalist_match = re.search(r'記者([\u4e00-\u9fff]{2,3})', text)
        #     if journalist_match:
        #         print("journalist_match.group(1):",journalist_match.group(1))
        #         self.authors.append(journalist_match.group(1))
        


class SETN(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("article").find_all("p")
        passage = "\n".join(
        p.get_text(strip=True) 
        for i, p in enumerate(paragraphs)  # Add index with enumerate
            if i > 0  # Skip first paragraph (index 0)
            and "text-align:center" not in p.get("style", "").replace(" ", "") 
            and "text-align:center;" not in p.get("style", "").replace(" ", "")
        )
        self.content=passage.strip()

        # Extract date
        print(soup.find("div",class_="page-title-text"))
        date=soup.find("time",class_="page_date").get_text()
        self.published_at=standardDateToTimestamp(date)

        # Extract author
        div_element = soup.find("article")
        p_elements = div_element.find_all("p")
        if p_elements:
            # Get the full text from the first <p> tag
            raw_text = p_elements[0].get_text()
            print("raw_text:",raw_text)
            # Check which name format is present
            if '記者' in raw_text:
                # Case 1: "記者王超群∕台北報導"
                # This removes the "記者" prefix, splits the string at the slash,
                # and takes the first part (the name).
                name = re.split(r'[∕／/]', raw_text.replace('記者', ''))[0]
            else:
                # Case 2: "王崑義"
                # The entire string is the name.
                name = raw_text
            print("name:",name)
            self.authors.append(name.strip())
        
        # Extract images
        image_selectors=[
            {"selector": 'article'}, 
        ]
        for selector in image_selectors:
                element=soup.select_one(selector["selector"])
                print("element:",element)
                if element:
                    images=element.find_all("img")
                    for image in images:
                        self.images.append(image["src"])
                    break
        soup.find("self.images:",self.images)

class NextAppleNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="post-content").find_all("p", recursive=False)
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        article=soup.find("div",class_="infScroll")
        if article:
            date=article.find("time").get_text()
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        info_a=soup.find_all("a",style="color: #0275d8;")
        print("info_a:",info_a)
        if info_a and info_a[1]:
            author=info_a[1].get_text()
            self.authors.append(author)
        # print("info:",info)

        # Extract images
        content_div=soup.find("div",class_="infScroll")
        if content_div:
            figure=content_div.find("figure")
            if figure:
                img=figure.find("img")
                if img:
                    self.images.append(img['data-src'])
        print("self.images:",self.images)

class TTV(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",id="newscontent").find_all("p", recursive=False)
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        date_time=soup.find("li",class_="date time")
        if date_time:
            date=date_time.get_text()
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        content_div=soup.find("div",id="newscontent")
        print("content_div:",content_div)
        if content_div:
            p=content_div.find_all("p")
            for text in p:
                match = re.search(r'責任編輯／(.*)', text.get_text())  # Capture everything after ／
                if match is None:
                    match = re.search(r'責任編輯/(.*)', text.get_text())  # Capture everything after ／
                if match:
                    name = match.group(1).strip()  # Get the captured group and remove whitespace
                    self.authors.append(name)
                else:
                    print("No match found")
            
        # print("info:",info)

        # Extract images
        content_div=soup.find("div",class_="article-body")
        if content_div:
            figure=content_div.find("figure",class_="cover img")
            print("figure:",figure)
            if figure:
                img=figure.find("img")
                if img:
                    self.images.append(img['src'])

        content_div=soup.find("div",id="newscontent")
        if content_div:
                images=content_div.find_all("img")
                if images:
                    for image in images:
                        image=image["src"]
                        self.images.append(image)
        print("self.images:",self.images)
                

class MirrorMedia(News):
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
            time.sleep(0)  # Initial load

            # Get page height
            total_height = driver.execute_script("return document.body.scrollHeight")

            # Human-like scrolling (e.g., 300px at a time)
            scroll_step = 300
            current_position = 0

            while current_position < total_height:
                # Scroll down a bit
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                current_position += scroll_step
                time.sleep(0.001)  # Adjust based on network speed

                # Update total height (in case new content loads)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height > total_height:
                    total_height = new_height
            time.sleep(2)  # 等待 JS 載入
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            # Extract title
            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag else "No title found"

            # Extract content
            container=None
            tag=None
            if soup.find("section",class_="article-content__Wrapper-sc-a27b9208-0 hWzglx"):
                container=soup.find("section",class_="article-content__Wrapper-sc-a27b9208-0 hWzglx")
                tag="div"
            if container==None and soup.find("section",class_="external-article-content__Wrapper-sc-8f3f1b36-0 cWifPf"):
                container=soup.find("section",class_="external-article-content__Wrapper-sc-8f3f1b36-0 cWifPf")
                self.origin=soup.find("div",class_="external-article-info__ExternalCredit-sc-83f18676-4 ryMAg").find("span").get_text()
                tag="p"
            print("container:",container)
            all_unique_texts = []
            seen = set()
            if container:
                for element in container.find_all(tag):
                        text = element.get_text(strip=True)
                        if text and text not in seen:  # Check for non-empty and unique
                            seen.add(text)
                            all_unique_texts.append(text)

            self.content = "\n".join(all_unique_texts)

            # Extract published date
            div_element=soup.find("div",class_="normal__Date-sc-3b14d180-5 huFyWo")
            if div_element is None:
                div_element=soup.find("div",class_="external-normal-style__Date-sc-f5353e0a-5 cOlbJt")
            print("p_element:",div_element)
            if div_element:
                date=div_element.get_text().replace("臺北時間","")
                print("date:",date)
                self.published_at=standardDateToTimestamp(date)

            # Extract author
            section=soup.find("section",class_="credits__CreditsWrapper-sc-93b3ab5-0 gReTcs normal-credits")
            print("section:",section)
            if section:
                author_ul=section.find("ul")
                if author_ul:
                    self.authors.append(author_ul.get_text().strip())

            # Extract images
            # native articles
            content_div=soup.find("article")
            if content_div:
                extended_reading=content_div.find("ul",class_="related-article-list__ArticleWrapper-sc-55c1bac2-2 iYrpEr")
                if extended_reading:
                    extended_reading.decompose()
                images=content_div.find_all("img",class_="readr-media-react-image")
                print("images:",images)
                for image in images:
                    print(image["src"])
                    self.images.append(image["src"])
            # non-native articles
            if content_div is None:
                content_div=soup.find_all("p",style="text-align: center;")
                print("content_div:",content_div)
                if content_div:
                    for content in content_div:
                        image=content.find("img")
                        if image:
                            self.images.append(image["src"])
            print("content_div:",content_div)
            print("self.title:",self.title)
            print("self.content:",self.content)
            print("self.images:",self.images)
            print("self.authors:",self.authors)
            print("self.published_at:",self.published_at)
            print("self.origin:",self.origin)
            
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

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

        # Extract published date
        div_element=soup.find("span",{"aria-label": "出版時間"})
        print("p_element:",div_element)
        if div_element:
            date=div_element.get_text()
            print("date:",date)
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        author_a=soup.find("a",{"data-sec":"reporter"})
        if author_a:
            self.authors.append(author_a.get_text().strip())

        # Extract images
        content_div=soup.find("div",class_="containerBlk mb-1")
        if content_div:
            images=content_div.find_all("figure")
            print("images:",images)
            for image in images:
                self.images.append(image.find("img")["src"])

class StormMedia(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("article").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        div_element=soup.find("div",class_="flex shrink-0 items-center text-smg-typography-caption-12-r text-smg-gray-700 smg-desktop:text-smg-typography-body-16-r")
        print("p_element:",div_element)
        if div_element:
            date=div_element.get_text()
            print("date:",date)
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        self.authors.append(soup.find("a",class_="generalLink text-smg-typography-caption-14-r text-smg-red-primary hover:underline").get_text().strip())

        # Extract images
        content_div=soup.find("div",class_="coverImg")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

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

        # Extract published date+authors
        article_info = soup.find("div", class_="author")
        if article_info:
            editor_links = article_info.find_all("a")
            for a in editor_links:
                self.authors.append(a.text)
            
            # Extract published date (the first time after "發佈時間：")
            text_parts = article_info.get_text().split("發佈時間：")
            if len(text_parts) > 1:
                published_date = text_parts[1].split()  # Gets "2025/07/06"
                published_at=published_date[0]+" "+published_date[1]
                self.published_at=standardDateToTimestamp(published_at)
            
            print("self.authors:", self.authors)
            print("Published At:", published_at)
        
        # Extract images
        print("article_new:",soup.find("div",class_="article_new"))
        content_div=soup.find("div",class_="article_new")
        if content_div:
            image_div=content_div.find("div",class_="img_box")
            print("image_div:",image_div)
            if image_div:
                image=image_div.find("img")["src"]
                self.images.append(image)
        print("image:",self.images)


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
            if p.get_text(strip=True) and p.get_text()!="★延伸閱讀★"  # 過濾空段落
        )
        print("self.content:",self.content)

        # Extract date
        date_div=soup.find("div",class_="article_date")
        if date_div:
            date=date_div.get_text()
            self.published_at=standardDateToTimestamp(date)
        if date_div is None:
            date_div=soup.find("div",class_="article_info_date")
            print("date_div:",date_div)
            if date_div:
                date=" ".join(p.get_text(strip=True) for p in date_div.find_all("div"))
                self.published_at=standardDateToTimestamp(date)
            
        # Extract images
        content_div=soup.find("div",class_="article_container")
        if content_div:
            image_div=content_div.find("div",class_="img")
            print("image_div:",image_div)
            if image_div:
                image=image_div.find("img")
                print("image:",image)
                if image:
                    self.images.append(image["src"])
        
        
        # Extract authors
        editor_div=soup.find("a",class_="article_info_editor")
        if editor_div is None:
            editor_div=soup.find("div",class_="article_info_editor")
        print("editor_div:",editor_div)
        if editor_div:
            editor=editor_div.get_text()
            editor=editor.replace("實習編輯","").replace("記者","").replace("責任編輯","").strip()
            self.authors.append(editor)

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

        # Extract published date
        p_element=soup.find("p",class_="publish")
        print("p_element:",p_element)
        if p_element:
            text=p_element.find("span").get_text()
            print("text:",text)
            date=text.replace("發布","").strip()
            self.published_at=standardDateToTimestamp(date)

        # Extract author
        self.authors.append(soup.find("a",class_="author").get_text().strip())

        # Extract images
        content_div=soup.find("div",class_="news_content")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

class CTINews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div",class_="article-content").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date+author
        article_info=soup.find("div",class_="article-info")
        print("article_info:",article_info)
        if article_info:
            info=article_info.find_all("a")
            date=info[0].get_text()
            author=info[1].get_text()
            # date=text.replace("發布","").strip()
            self.published_at=standardDateToTimestamp(date)
            self.authors.append(author)

            author=info[1]
            print("info[0]:",info[0])
            print("info[1]:",info[1])

        # Extract images
        content_div=soup.find("div",class_="article-content")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

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
            driver.get(str(self.url))
            time.sleep(2)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("meta", property="og:title")
            self.title = title_tag["content"].strip() if title_tag else "No title found"

            content_div = soup.find("div", id="newscontent")
            print("content_div:",content_div)
            if content_div:
                for promo in content_div.find_all("strong"):
                    promo.decompose()
                for captions in content_div.find_all("figcaption"):
                    captions.decompose()
                if content_div:
                    # Get text with line breaks preserved
                    texts = [line.strip() for line in content_div.stripped_strings]
                    self.content = "\n".join(texts)
                else:
                    self.content = "No content found"

            # Extract published date
            date_span=soup.find("span",class_="date")
            if date_span:
                date=date_span.get_text().replace("發佈時間：","").strip()
                self.published_at=standardDateToTimestamp(date)
                print("date_span:",date_span)

            # Extract images
            image_div=soup.find("div",class_="fixed_img")
            if image_div:
                image=image_div.find("img")
                if image:
                    self.images.append(image["src"])

            # Extract author
            preface=soup.find("div",id="preface")
            print("preface:",preface)
            if preface:
                p_element=preface.find('p')
                if p_element:
                    author=p_element.get_text()
                    match = re.search(r'／(.*?)報導', author)
                    if match:
                        name = match.group(1)
                        if name!="綜合": 
                            self.authors.append(name)
                        print(name)
                    else:
                        print("No match found")

        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()