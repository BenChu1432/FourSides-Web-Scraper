import os
import re
from typing import Dict, Literal, Optional, TypedDict
from urllib.parse import urljoin, urlparse
import concurrent
import feedparser
import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from typing import List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
import datetime
# from translation import translate_text
from app.dto.dto import FetchUrlsResult, ParseArticleResult
from app.enums.enums import ErrorTypeEnum
from app.errors.NewsParsingError import UnmappedMediaNameError
from util import chineseMediaTranslationUtil
from util.timeUtil import HKEJDateToTimestamp, IntiumChineseDateToTimestamp, NowTVDateToTimestamp, RTHKChineseDateToTimestamp, SCMPDateToTimestamp, SingTaoDailyChineseDateToTimestamp, TheCourtNewsDateToTimestamp, standardChineseDatetoTimestamp, standardTaipeiDateToTimestamp,YahooNewsToTimestamp
import concurrent.futures
import time
import platform
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin


# Constants
WAITING_TIME_FOR_JS_TO_FETCH_DATA=2

Degree = Literal["low", "moderate", "high"]

class AssessmentItem(TypedDict):
    description: str
    degree: Degree

class News(ABC):
    media_name: Optional[str]
    title: Optional[str]
    content: Optional[str]
    published_at: Optional[int]
    authors: List[str]
    images: List[str]
    origin: Optional[str]
    refined_title: Optional[str]
    reporting_style: List[str]
    reporting_intention: List[str]
    journalistic_demerits: Dict[str, AssessmentItem]
    journalistic_merits: Dict[str, AssessmentItem]
    max_workers: int
    max_pages: int

    def __init__(self, url=None):
        self.media_name=''
        self.url = url
        self.max_workers=5
        self.max_pages=1
        self.title = None
        self.content = None
        self.published_at=None
        self.origin="native"
        self.authors=[]
        self.images=[]

    def get_chrome_options(self):
        """Return (chromedriver_path, chrome_options) for Selenium based on runtime platform."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        return options

    def get_chrome_driver(self):
        """Return (chromedriver_path, chrome_options) for Selenium based on runtime platform."""
        options=self.get_chrome_options()

        driver = webdriver.Chrome(options=options)
        return driver
    
    # def get_chrom_driver_with_error(self):
    #     try:
    #         self.get_chrome_driver()
    #     except Exception as e:
            


    @abstractmethod
    def _get_article_urls(self):
        """
        Child classes MUST implement this to extract content from BeautifulSoup soup.
        """
        pass
    
    #  Wrapper pattern
    #  Centralizing error handling across polymorphic child classes while keeping the code DRY and clean.
    def get_article_urls_with_errors(self) -> FetchUrlsResult:
        errors = []
        urls = []
        try:
            urls = self._get_article_urls()
            # Limit to 30 urls for web scraping in each run
            urls=urls[:30]
            if not urls:
                errors.append({
                    "failure_type": ErrorTypeEnum.ZERO_URLS_FETCHED,
                    "media_name": self.media_name,
                    "detail": "No URLs found",
                })
        except Exception as e:
            errors.append({
                "failure_type": ErrorTypeEnum.OTHERS,
                "media_name": self.media_name,
                "detail": str(e)
            })
        result=FetchUrlsResult(urls, errors)
        return result
    
    # soup may exist or not
    @abstractmethod
    def parse_article(self, soup):
        """
        Child classes MUST implement this to extract content from BeautifulSoup soup.
        """
        pass

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
            response = requests.get(self.url, headers=headers, timeout=5)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            print("🌐 Requests succeeded, calling parse_article...")
            self.parse_article(soup)

        except Exception as e:
            print(f"⚠️ Falling back to Selenium due to: {e}")
            try:
                driver = self.get_chrome_driver()
                driver.get(str(self.url))
                time.sleep(WAITING_TIME_FOR_JS_TO_FETCH_DATA)

                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")

                print("📦 Calling parse_article() after Selenium fallback")  # MUST SEE THIS
                self.parse_article(soup)  # ✅ Must be here

            except Exception as se:
                print(f"❌ Selenium failed: {se}")
            finally:
                driver.quit()
        print("📌 Title:", self.title)
        print("📌 Author(s):", self.authors)
        print("📌 Published At:", self.published_at)
        print("📌 Content Preview:", self.content[:100], "...")
        print("📌 Image(s):", self.images)

    
    def parse_article_with_errors(self) -> ParseArticleResult:
        errors = []
        try:
            self._fetch_and_parse()
            if self.content is None or self.content=="":
                errors.append({
                    "failure_type": ErrorTypeEnum.PARSING_FAILURE,
                    "url":[self.url],
                    "media_name": self.media_name,
                    "detail": "No content found"
                })
        except UnmappedMediaNameError as e:
            errors.append({
                "failure_type": ErrorTypeEnum.UNMAPPED_MEDIA,
                "url": [self.url],
                "media_name": self.media_name,
                "detail": f"Cannot find {self.media_name} in the map"
            })
        except Exception as e:
            errors.append({
                "failure_type": ErrorTypeEnum.PARSING_ERROR,
                "url":[self.url],
                "media_name": self.media_name,
                "detail": str(e)
            })

        return ParseArticleResult(errors)


        
    

# HK News Media
class HongKongFreePress(News):
    def parse_article(self, soup):
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
        self.published_at=standardTaipeiDateToTimestamp(published_at)
        print("self.published_at:", self.published_at)


class MingPaoNews(News):
    def parse_article(self, soup):
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
            self.published_at = standardTaipeiDateToTimestamp(date_div.get_text(strip=True))
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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="ChineseNewYorkTimes"
        self.max_pages=1
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://m.cn.nytimes.com/zh-hant/"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('ol.article-list li')
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        all_urls.append(full_url)
                        # if href.startswith("/news/detail/"):
                        #     full_url = base_url + href
                        #     print("✅ full_url:", full_url)
                        #     all_urls.append(full_url)

            print("all_urls:",all_urls)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls

    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
        finally:
                driver.quit()

class DeutscheWelle (News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="DeutscheWelle"
    
    def _get_article_urls(self):
        all_urls=[]
        latest_news_url = "https://rss.dw.com/rdf/rss-chi-all"
        headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://google.com/',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                    }
        response=requests.get(latest_news_url,headers=headers)
        xml=response.text
        print("xml:",xml)
        soup=BeautifulSoup(xml, "xml")
        articles=soup.find_all("item")
        for article in articles:
            link=article.find("link")
            print("link:",link)
            if link:
                url=link.get_text()
                print("url:",url)
                all_urls.append(url)
                
        
        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
        # def parse_article(self,soup):
            title = soup.find("h1").get_text()
            self.title=title

            # Extract content
            content_div = soup.find("div", class_="c17j8gzx")
            if content_div:
                paragraphs=content_div.find_all("p")
                self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
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
            author_selectors = [
                {"selector": "a.author"},
                {"selector":"span.author"},
            ]
        
            for selector in author_selectors:
                element = soup.select_one(selector["selector"])
                if element:
                    name=element.get_text()
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

        finally:
                driver.quit()

class HKFreePress(News):
    # Extract title
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
            self.published_at = standardTaipeiDateToTimestamp(date_div)
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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
            self.published_at=standardTaipeiDateToTimestamp(date)

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
        finally:
                driver.quit()

class InitiumMedia(News):
    def parse_article(self, soup):
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

class HKCD(News):
    def parse_article(self, soup):
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
            self.published_at = standardTaipeiDateToTimestamp(date)
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
    def parse_article(self, soup):
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
        self.published_at = standardTaipeiDateToTimestamp(date)
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
    def parse_article(self, soup):
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="ChineseBBC"
        self.max_pages=1
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        all_urls=[]
        latest_news_url = "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml"
        headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://google.com/',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                    }
        response=requests.get(latest_news_url,headers=headers)
        xml=response.text
        print("xml:",xml)
        soup=BeautifulSoup(xml, "xml")
        articles=soup.find_all("item")
        for article in articles:
            link=article.find("link")
            print("link:",link)
            if link:
                url=link.get_text()
                print("url:",url)
                all_urls.append(url)
                
        
        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
            self.published_at=standardTaipeiDateToTimestamp(date)

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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="VOC"
        self.max_pages=1
        
    def _get_article_urls(self):
        latest_news_url = "https://www.voachinese.com/z/1739"
        base_url="https://www.voachinese.com"
        print(f"Loading page: {latest_news_url}")

        all_urls=[]
        headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://google.com/',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                    }
        response=requests.get(latest_news_url,headers=headers)
        html=response.text
        # print("html:",html)
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select('ul.archive-list li')
        # print("articles:",articles)
        for article in articles:
                a_tag = article.select_one("a")
                print("a_tag:",a_tag)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("/a/"):
                        full_url = base_url + href
                        print("✅ full_url:", full_url)
                        all_urls.append(full_url)


        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title = soup.find("h1").get_text()
        self.title=title

        # Additional extraction from <h1 class="title pg-title">
        try:
            h1_title = soup.find("h1", class_="title pg-title")
            print("Found h1_title:", h1_title)

            if h1_title:
                title_text = h1_title.get_text(strip=True)
                print("Extracted title text:", title_text)
                self.title = title_text
        except Exception as e:
            print("Error extracting from <h1 class='title pg-title'>:", e)

        # Extract content
        content_div = soup.find("div", id="article-content")
        if content_div:
            paragraphs=content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"
        
        # Extract date
        publication_date=soup.find("time",{"pubdate":"pubdate"})
        if publication_date:
            date=publication_date.get_text()
            self.published_at=standardTaipeiDateToTimestamp(date)

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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
        self.published_at = standardTaipeiDateToTimestamp(date)

class HKGovernmentNews(News):
    def parse_article(self, soup):
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
        self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract image
        print(soup.find("div", class_="news-block news-block-3by2"))
        self.images.append("https://www.news.gov.hk/"+soup.find("div", class_="news-block news-block-3by2").find("img")["src"])
        print("self.images:", self.images)


# It uses Vue to fetch data with JavaScript
class OrangeNews(News):
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
            self.published_at=standardTaipeiDateToTimestamp(date)
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


        finally:
                driver.quit()

class TheStandard(News):
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
        finally:
                driver.quit()

class HKEJ(News):
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
        self.parse_article()

    def parse_article(self):
        driver = self.get_chrome_driver()

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
                    self.published_at = standardTaipeiDateToTimestamp(date)
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
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        options = Options()
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
        finally:
                driver.quit()

# China News Media
class PeopleDaily(News):
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
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
    def parse_article(self, soup):
        # Extract title
        self.title = soup.find("div",class_="article_title").get_text()

        # Extract content
        self.content = soup.find("div",class_="article_right").get_text()


# Taiwanese News
class UnitedDailyNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="UnitedDailyNews"
        self.max_pages=1

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://money.udn.com/rank/newest/1001/0/1?from=edn_navibar"
        base_url="https://money.udn.com"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("ul.tab-content__list li")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.tab-content__list li")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
        
    def parse_article(self, soup):
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
            {"selector":"div.article-body__info span"},
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
            print("element:",element)
            if element:
                author_text = element.get_text(strip=True)
                print("author_text:",author_text)
                if author_text and author_text!="":
                    # Clean up the author text
                    match = re.search(r'記者([\u4e00-\u9fff]{2,3})', author_text)
                    if match:
                        author_text = match.group(1).strip()

                    if match is None:
                        match = re.search(r'編譯([\u4e00-\u9fff]{2,3})', author_text)
                        if match:
                            author_text = match.group(1).strip()

                    print("author_text:",author_text)
                    # author_text = author_text.replace("綜合外電","").replace("編譯","").replace("聯合報", "").replace("經濟日報","").replace("聯合新聞網","").replace("台北","").replace("台中","").replace("記者","").replace("即時報導","").replace("udn STYLE", "").replace("撰文","").replace("／", "").strip()
                    # print("author_text:", author_text)
                    self.authors.append(author_text)
                    break
        print("self.authors:", self.authors)

        # Extract published date
        date_selectors=[
            {"selector": "div.article-section__info time", "attribute": "datetime"},  # Preferred - time tag with datetime attribute
            {"selector":"time.article-body__time"},
            {"selector":"time.article-content__time"},
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
                    self.published_at = standardTaipeiDateToTimestamp(date)
                else: 
                    date=element.get_text(strip=True)
                    self.published_at = standardTaipeiDateToTimestamp(date)

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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="LibertyTimesNet"
        self.max_pages=1

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://news.ltn.com.tw/list/breakingnews"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("ul.list li")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = "https://news.ltn.com.tw" + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.list li")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = "https://news.ltn.com.tw" + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_selectors=[
             {"selector": "div.article_wrap"},
            {"selector": "div.whitecon.article[data-page='1']"},
            {"selector":"div[data-desc='內文'] div.text"},
            {"selector": "article.article div.text"}, 
            {"selector": "div.text"},  # Preferred - time tag with datetime attribute
        ]
        for selector in content_selectors:
            if selector["selector"] == "div.article_wrap":
                article_wrap = soup.find("div", class_="article_wrap")
                print("article_wrap:",article_wrap)
                if article_wrap:
                    appPromo = article_wrap.find("p", class_="appE1121")
                    subscription=article_wrap.find("a",class_="subs_eDM")
                    captions = article_wrap.find_all("span", class_="ph_d")
                    if appPromo:
                        appPromo.decompose()
                    if subscription:
                        subscription.decompose()
                    if captions:
                        for caption in captions:
                            caption.decompose()
                    content=article_wrap.find_all("p")
                    self.content = "\n".join(p.get_text(strip=True) for p in content)
                    print("self.content:",self.content)
                    break
            if selector["selector"] == "div.text":
                elements = soup.find_all("div", class_="text")
                for element in elements:
                    if element.get("class") == ["text"]:  # exact match
                        break
                else:
                    element = None
            else:
                element = soup.select_one(selector["selector"])

            if element:
                appPromo = element.find("p", class_="appE1121")
                captions = element.find_all("span", class_="ph_d")
                if appPromo:
                    appPromo.decompose()
                if captions:
                    for caption in captions:
                        caption.decompose()
                content_div = element.find_all(["p", "h"])
                self.content = "\n".join(p.get_text(strip=True) for p in content_div)
                break

        # Extract published date
        date_selector=[
            {"selector": "div.whitecon.article[data-page='1'] span.time",},  # Preferred - time tag with datetime attribute
            {"selector": "div[data-desc='內文'] span.time"},
            {"selector": "article.article time.time"}, 
            {"selector": "span.time"}
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                date=element.get_text()
                self.published_at=standardTaipeiDateToTimestamp(date)
                break
        # print("self.published_at:",self.published_at)

        # Extract images
        image_selectors=[
             {"selector": "div.whitecon.article[data-page='1']"}, 
             {"selector":"div[data-desc='內文'] div.text"},
             {"selector": "div.article-wrap div.text","data-desc":"內容頁"}, 
             {"selector": "div.text"}, 
        ]
        for selector in image_selectors:
            element=soup.select_one(selector["selector"])
            print("selector:",selector)
            print("element:",element)
            isReadyToBreak=False
            if element:
                images=element.find_all("img")
                for image in images:
                    print("image:",image)
                    self.images.append(image["data-src"])
                isReadyToBreak=True
            if isReadyToBreak==True:
                break

        # Extract authors (no authors)
        # Extract authors (no authors)
        # Extract authors (no authors)
        # === Extract authors ===
        # ✅ STEP 1: Try direct 文／ pattern first
        print("hello")
        author_tag = soup.select_one("article#article_body p")
        if author_tag:
            text = author_tag.get_text(strip=True)
            match = re.search(r"[【\[]文／([\u4e00-\u9fa5]{2,4})[】\]]", text)
            if match:
                self.authors.append(match.group(1).strip())
                print("✅ Author extracted from 文／ pattern:", match.group(1))
                return  # Stop here if found

        # ✅ STEP 2: Fallback to your original multi-selector loop
        authors_selectors = [
            {"selector": "div.whitecon.article[data-page='1']"},
            {"selector": "div.whitecon.article[itemprop='articleBody'] .text.boxText"},
            {"selector": "div[data-desc='內文'] div.text"}
        ]

        for selector in authors_selectors:
            element = soup.select_one(selector["selector"])
            print("element:", element)
            if not element:
                continue

            for p in element.find_all('p'):
                text = p.get_text()

                # Pattern 1: 記者[Name]／
                match = re.search(r'記者([\u4e00-\u9fa5]{2,4})／', text)
                if match:
                    self.authors.append(match.group(1).strip())
                    print("✅ Author from '記者...／':", match.group(1))
                    return

                # Pattern 2: [Name]／核稿編輯
                match = re.search(r'([\u4e00-\u9fa5]{2,4})／核稿編輯', text)
                if match:
                    self.authors.append(match.group(1).strip())
                    print("✅ Author from '...／核稿編輯':", match.group(1))
                    return

                # (Optional future: Add more patterns here if needed)

            





class ChinaTimes(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="ChinaTimes"
        self.max_workers=5
        self.max_pages=2

    def _fetch_and_parse(self):
        self.parse_article()

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            latest_news_url= "https://www.chinatimes.com/realtimenews/?chdtv"
            base_url = "https://www.chinatimes.com"
            url = f"{base_url}/?page={page}"
            print(f"Loading page: {url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.vertical-list li")

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    a_tag = article.select_one("h3.title a")
                    if a_tag:
                        href = a_tag['href']
                        full_url = base_url + href
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
                    self.published_at = standardTaipeiDateToTimestamp(date)
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
            print("finished")
        finally:
                driver.quit()

class CNA(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="CNA"
        self.max_pages=1
    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.cna.com.tw/list/aall.aspx"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("ul.mainList li")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = "https://www.cna.com.tw" + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                view_more_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "SiteContent_uiViewMoreBtn"))
                )
                view_more_button.click()
                print("Clicked '查看更多內容'")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.mainList li")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = "https://news.ltn.com.tw" + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
                self.published_at=standardTaipeiDateToTimestamp(date)
                break
        # Additional extraction from <p class="article-time"> inside <div class="article-info">
        try:
            article_time_tag = soup.find("p", class_="article-time")
            print("Found article_time_tag:", article_time_tag)

            if article_time_tag:
                datetime_str = article_time_tag.get_text(strip=True)
                print("Extracted datetime from article-time:", datetime_str)
                self.published_at = standardTaipeiDateToTimestamp(datetime_str)
        except Exception as e:
            print("Error extracting from <p class='article-time'>:", e)


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
                    journalist_match = re.search(r'（中央社記者([\u4e00-\u9fff]{2,3})', text)
                    if journalist_match:
                        self.authors.append(journalist_match.group(1))
                    
                    # 2. Fallback: Check for editor names (only if no journalist is found)
                    editor_match = re.search(r'編輯：([\u4e00-\u9fff]{2,3})', text)
                    if editor_match and not self.authors:  # Avoid adding editors if journalist exists
                        self.authors.append(editor_match.group(1))
                break

        # Extract images
        date_selector=[
            {"selector": "figure.center img"},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            elements = soup.select(selector["selector"])
            print("elements:", elements)
            for element in elements:
                if element:
                    src = element.get("src")
                    data_src = element.get("data-src")
                    if src:
                        self.images.append(src)
                    if data_src:
                        self.images.append(data_src)
        print("self.images:",self.images)

class PTSNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="PTSNews"
        self.max_pages=1

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://news.pts.org.tw/dailynews"
        base_url="https://news.pts.org.tw"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("ul.news-list li.d-flex")
            for article in articles:
                    a_tag = article.select_one("a")
                    print("a_tag:",a_tag)
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.news-list li.d-flex")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
                self.published_at=standardTaipeiDateToTimestamp(date)
                break
        print("self.published_at:",self.published_at)

        # Extract authors
        date_selector = [
            {"selector": "div.article_authors div.reporter-container"},
        ]

        for selector in date_selector:
            element = soup.select_one(selector["selector"])
            print("element:", element)
            if element:
                a_elements = element.find_all("a")
                print("a_elements:", a_elements)
                for a_element in a_elements:
                    text = a_element.get_text()
                    self.authors.append(text)
                    print("✅ Extracted author from original method:", text)

        # === ADDITIONAL AUTHOR EXTRACTION (for PTS format) ===
        # Example HTML:
        # <div class="text-muted article-info">
        #     <span class="d-none d-md-inline">劉韋廷</span>
        # </div>
        additional_author_element = soup.select_one("div.article-info span")
        if additional_author_element:
            text = additional_author_element.get_text(strip=True)
            if text and text not in self.authors:
                self.authors.append(text)
                print("✅ Extracted author from PTS format:", text)
                # # 1. First, try to extract the journalist name (primary author)
                # journalist_match = re.search(r'中央社 記者([\u4e00-\u9fff]{2,3})', text)
                # if journalist_match:
                #     self.authors.append(journalist_match.group(1))
                
                # # 1. First, try to extract the journalist name (primary author)
                # journalist_match = re.search(r'經濟日報 編譯([\u4e00-\u9fff]{2,3})', text)
                # if journalist_match:
                #     self.authors.append(journalist_match.group(1))

        #Extract images
        date_selector=[
            {"selector": "figure img"},  # Preferred - time tag with datetime attribute
        ]
        for selector in date_selector:
            element=soup.select_one(selector["selector"])
            if element:
                self.images.append(element["src"])
                break

class CTEE(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="CTEE"
        self.max_pages=1

    def _fetch_and_parse(self):
        self.parse_article()

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.ctee.com.tw/livenews"
        base_url="https://www.ctee.com.tw"
        print(f"Loading page: {latest_news_url}")

        driver = self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("div.newslist.livenews div.newslist__card h3.news-title")
            for article in articles:
                    a_tag = article.select_one("a")
                    print("a_tag:",a_tag)
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                view_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "moreBtn"))
                )

                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", view_more_button)
                time.sleep(1)  # Let any animation finish
                view_more_button.click()
                print("Clicked '查看更多內容'")

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.newslist.livenews div.newslist__card h3.news-title")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver = self.get_chrome_driver()

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
                    self.published_at=standardTaipeiDateToTimestamp(date)
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

        finally:
                driver.quit()

class MyPeopleVol(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="MyPeopleVol"
        self.max_pages=2
    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            base_url = "https://www.mypeoplevol.com"
            url = f"{base_url}/?page={page}"
            print(f"Loading page: {url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.td_block_inner.tdb-block-inner.td-fix-index div")

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    a_tag = article.select_one("a.td-image-wrap")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url not in page_urls:
                            page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # remove promo
        [s.decompose() for s in soup.select('[class*="tdm-descr"]')]

        # Extract title
        self.title = soup.find("h1").get_text()

        # Extract content + authors + images
        content_div = soup.find("div",class_="td-post-content")
        if content_div:
            p_elements=content_div.find_all("p")
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
            journalist_match= re.search(r'〔民眾黨([\u4e00-\u9fff]{2,3})', text)
            if journalist_match and len(self.authors)==0:
                self.authors.append(journalist_match.group(1))
            journalist_match= re.search(r'【民眾網([\u4e00-\u9fff]{2,3})', text)
            if journalist_match and len(self.authors)==0:
                self.authors.append(journalist_match.group(1))
            journalist_match= re.search(r'【民眾新聞網([\u4e00-\u9fff]{2,3})', text)
            if journalist_match and len(self.authors)==0:
                self.authors.append(journalist_match.group(1))
            journalist_match= re.search(r'【民眾新聞([\u4e00-\u9fff]{2,3})', text)
            if journalist_match and len(self.authors)==0:
                self.authors.append(journalist_match.group(1))
            # images 
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
                self.published_at=standardTaipeiDateToTimestamp(date)
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
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name="TaiwanTimes"
        self.max_pages=2
        self.max_workers = 1  # Override field in child class

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_article_url(index, max_pages, start_url, chrome_options):
            driver = webdriver.Chrome(options=chrome_options)
            try:
                driver.get(start_url)
                time.sleep(3)

                for _ in range(max_pages - 1):
                    try:
                        view_more_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '觀看更多')]"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView(true);", view_more_button)
                        time.sleep(1)
                        view_more_button.click()
                        time.sleep(3)
                    except:
                        break

                articles = driver.find_elements(By.CSS_SELECTOR, "div.immediate-item.use-flex")

                if index < len(articles):
                    article = articles[index]
                    driver.execute_script("arguments[0].scrollIntoView(true);", article)
                    time.sleep(1)
                    article.click()
                    time.sleep(2)
                    return driver.current_url
                else:
                    return None
            finally:
                driver.quit()
        latest_news_url = "https://www.taiwantimes.com.tw/app-container/app-content/new/new-category?category=7"

        driver=self.get_chrome_driver()
        options=self.get_chrome_options()

        try:
            driver.get(latest_news_url)
            time.sleep(3)

            for _ in range(max_pages - 1):
                try:
                    view_more_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '觀看更多')]"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", view_more_button)
                    time.sleep(1)
                    view_more_button.click()
                    print("Clicked '觀看更多'")
                    time.sleep(3)
                except Exception as e:
                    print("No more '觀看更多' button or failed to click:", e)
                    break

            articles = driver.find_elements(By.CSS_SELECTOR, "div.immediate-item.use-flex")
            print("articles:",articles)
            total_articles = len(articles)
            print(f"Found {total_articles} articles")

            indices = list(range(total_articles))

        finally:
            driver.quit()

        article_urls = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_article_url, idx, max_pages, latest_news_url, options) for idx in indices]
            for future in concurrent.futures.as_completed(futures):
                url = future.result()
                print("url:",url)
                if url:
                    article_urls.append(url)

        for idx, url in enumerate(article_urls, 1):
            print(f"{idx}. {url}")

        print(f"\nTotal articles found: {len(article_urls)}")
        print("All URLs:", article_urls)
        return article_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver=self.get_chrome_driver()

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
            time.sleep(5)  # 等待 JS 載入

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title_div=soup.find("div",class_="detail-header")
            if title_div:
                self.title = title_div.get_text()
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

            # Extract published date safely
            other_info_elements = soup.find_all("div", class_="otherinfo normal-size main-text-color")
            if len(other_info_elements) > 0:
                date_text = other_info_elements[0].get_text()
                self.published_at = standardTaipeiDateToTimestamp(date_text)
            else:
                print("No date element found")

            # Extract author safely
            if len(other_info_elements) > 1:
                author_text = other_info_elements[1].get_text()
                if author_text:
                    journalist_match = re.search(r'記者([\u4e00-\u9fff]{2,3})', author_text)
                    if journalist_match:
                        self.authors.append(journalist_match.group(1))
            else:
                print("No author element found")

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

        finally:
                driver.quit()

class ChinaDailyNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="ChinaDailyNews"

    def _get_article_urls(self):
        latest_news_url = "https://www.cdns.com.tw/"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            carousel_articles = soup.select('h1.elementor-heading-title.elementor-size-default')
            if carousel_articles:
                for article in carousel_articles:
                    if article:
                        link_a=article.find('a')
                        if link_a:
                            url=link_a['href']
                            all_urls.append(url)

            articles=soup.select("h3.elementor-post__title")
            if articles:
                for article in articles:
                    if article:
                        link_a=article.find('a')
                        if link_a:
                            url=link_a['href']
                            all_urls.append(url)
                    
            print("all_urls:",all_urls)

        except Exception as e:
            print("Error:",e)
            raise e

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls

    def parse_article(self, soup):
        print("parsing article:",self.url)
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find("div", class_="elementor-widget-theme-post-content")
        if paragraphs:
            p_tags = paragraphs.find_all("p")
            passage = "\n".join(p.get_text(strip=True) for p in p_tags if p)
            self.content = passage.strip()

        # Extract date
        date_span=soup.find("span",class_="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-date")
        if date_span:
            date=date_span.get_text()
            if date:
                self.published_at=standardTaipeiDateToTimestamp(date)
        
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
            p_element = p_elements[0]
            if p_element:
                raw_text=p_element.get_text()
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="SETN"
        self.max_pages=1
        self.max_workers=5
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.setn.com/viewall.aspx"
        base_url = "https://www.setn.com"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('div[id="NewsList"] div.newsItems')
            for article in articles:
                    a_tag = article.select_one("h3.view-li-title a")
                    if a_tag:
                        href = a_tag['href']
                        if href.startswith("/News.aspx?"):
                            full_url = base_url + href
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)
                        else:
                            all_urls.append(href)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select('ul[id="realtime"] li')

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("h3.view-li-title a")
                    if a_tag:
                        href = a_tag['href']
                        full_url = base_url + href
                        print("✅ full_url:", full_url)
                        all_urls.append(full_url)
            print("all_urls:",all_urls)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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

        # # Extract date
        # date_selectors=[
        #     {"selector": 'div.page-title-text'}, 
        #     {"selector": 'div.newsTime'}, 
        # ]
        # for selector in date_selectors:
        #     element=soup.select_one(selector["selector"])
        #     if element:
        #         time=element.find("time")
        #         if time:
        #             date=time.get_text()
        #             self.published_at=standardDateToTimestamp(date)

        # Extract date
        date_selectors = [
            {"selector": 'div.page-title-text'},
            {"selector": 'div.newsTime'},
            {"selector": 'time.pageDate'},  # ✅ New selector for your screenshot
            {"selector": 'div#ckuse time'},  # More specific fallback
        ]

        for selector in date_selectors:
            element = soup.select_one(selector["selector"])
            if element:
                # If there is a <time> tag inside, prefer that
                time_tag = element.find("time") if element.name != "time" else element
                if time_tag:
                    date_text = time_tag.get_text(strip=True)
                else:
                    date_text = element.get_text(strip=True)

                if date_text:
                    try:
                        self.published_at = standardTaipeiDateToTimestamp(date_text)
                        break  # ✅ Exit loop once a valid date is found
                    except Exception as e:
                        print(f"⚠️ Failed to parse date from '{date_text}':", e)

        # Extract author
        # Extract author
        div_element = soup.find("article")
        p_elements = div_element.find_all("p")
        if p_elements:
            # Get the full text from the first <p> tag
            raw_text = p_elements[0].get_text()
            # Check which name format is present
            if '記者' in raw_text:
                # Case 1: "記者王超群∕台北報導"
                name = re.split(r'[∕／/]', raw_text.replace('記者', ''))[0]
            elif '報導' in raw_text and ('∕' in raw_text or '／' in raw_text or '/' in raw_text):
                # Case 2: "社會中心／洪正達報導"
                match = re.search(r'[∕／/]\s*([\u4e00-\u9fa5]{2,4})報導', raw_text)
                if match:
                    name = match.group(1)
                else:
                    name = raw_text
            else:
                # Case 3: "王崑義"
                name = raw_text

            print("name:", name)
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="NextAppleNews"
        self.max_pages=2
        self.max_workers=5
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            latest_news_url = f"https://tw.nextapple.com/realtime/latest/{page}"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.stories-container article")
                # filtered_articles=[]
                # for article in articles:
                #     title=article.find("p",class_="date")
                #     print(title)
                #     if title and "PR" not in title:
                #         filtered_articles.append(article)

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    # print("article:",article)
                    a_tag = article.select_one("a")
                    if a_tag:
                        print("a_tag:",a_tag)
                        full_url = a_tag['href']
                        print("full_url:",full_url)
                        if full_url not in page_urls:
                            page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                print("page_urls:",page_urls)
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div", class_="post-content")
        if content_div:
            paragraphs = content_div.find_all("p", recursive=False)
            self.content = "" if content_div is None else "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = ""
            print("⚠️ post-content div not found")

        # Extract published date
        article = soup.find("div", class_="infScroll")
        if article:
            time_tag = article.find("time")
            if time_tag:
                date = time_tag.get_text()
                self.published_at = standardTaipeiDateToTimestamp(date)

        # Extract author
        info_a = soup.find_all("a", style="color: #0275d8;")
        print("info_a:", info_a)
        if len(info_a) > 1:
            author = info_a[1].get_text()
            self.authors.append(author)

        # Extract images
        content_div = soup.find("div", class_="infScroll")
        if content_div:
            figure = content_div.find("figure")
            if figure:
                img = figure.find("img")
                if img and img.get("data-src"):
                    self.images.append(img["data-src"])

        print("self.images:", self.images)

class TTV(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="TTV"
        self.max_pages=1

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://news.ttv.com.tw/realtime"
        base_url="https://news.ttv.com.tw"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("div.news-list ul li")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.news-list ul li")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
            self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract author
        content_div=soup.find("div",id="newscontent")
        print("content_div:",content_div)
        if content_div:
            p=content_div.find_all("p")
            for text in p:
                match = re.search(r'責任編輯／(.*)', text.get_text())  # Capture everything after ／
                if match is None:
                    match = re.search(r'責任編輯/(.*)', text.get_text())  # Capture everything after ／
                if match is None:
                    match = re.search(r'（記者([\u4e00-\u9fff]{2,3})(?:／)?', text.get_text())  # Capture everything after ／
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="MirrorMedia"
        self.max_pages=2
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.mirrormedia.mg"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('div.latest-news__ItemContainer-sc-f95eff3e-1 a.GTM-homepage-latest-list')
            for article in articles:
                    href = article['href']
                    if href:
                        full_url = latest_news_url + href
                        print("✅ full_url:", full_url)
                        all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select('div.latest-news__ItemContainer-sc-f95eff3e-1 a')

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    href = article['href']
                    print("href:",href)
                    if href and href.startswith("https://"):
                        all_urls.append(href)
                    elif href:
                        full_url = latest_news_url + href
                        print("✅ full_url:", full_url)
                        all_urls.append(full_url)
            print("all_urls:",all_urls)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver=self.get_chrome_driver()

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
                origin_div=soup.find("div",class_="external-article-info__ExternalCredit-sc-83f18676-4 ryMAg")
                if origin_div:
                    origin_span=origin_div.find("span")
                    if origin_span:
                        origin=origin_span.get_text()
                        if origin!="MirrorMedia":
                            try:
                                self.origin=chineseMediaTranslationUtil.map_chinese_media_to_enum(origin)
                            except ValueError as e:
                                raise UnmappedMediaNameError(origin) from e
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

            # Additional content extraction from <section class="external-article-content__Wrapper-sc-30e70ae7-0 lhKTuM">
            try:
                extra_container = soup.select_one("section.external-article-content__Wrapper-sc-30e70ae7-0")
                print("extra_container:", extra_container)

                if extra_container:
                    for p in extra_container.find_all("p"):
                        text = p.get_text(strip=True)
                        if text and text not in seen:
                            seen.add(text)
                            all_unique_texts.append(text)

                    self.content = "\n".join(all_unique_texts)
            except Exception as e:
                print("Error extracting extra content from external-article-content__Wrapper-sc-30e70ae7-0:", e)





            # Extract published date
            # Find all divs where class starts with 'article-info__Date'
            date_divs = soup.select('div[class^="article-info__Date"]')

            for div in date_divs:
                text = div.get_text(strip=True)
                if "發布時間" in text:
                    # Split all lines of text and clean them
                    lines = list(div.stripped_strings)
                    print("Raw lines:", lines)

                    # Try to find the second line (actual date)
                    for i, line in enumerate(lines):
                        if "發布時間" in line and i + 1 < len(lines):
                            date = lines[i + 1].strip()
                            print("Extracted publish date:", date)
                            self.published_at = standardTaipeiDateToTimestamp(date)
                            break
                    break
            # Additional extraction from <div class="external-normal-style__Date-sc-e92c822f-5 ...">
            try:
                date_div = soup.find("div", class_="external-normal-style__Date-sc-e92c822f-5")
                print("Found date_div:", date_div)

                if date_div:
                    datetime_str = date_div.get_text(strip=True).split("臺北時間")[0].strip()
                    print("Extracted datetime text from date_div:", datetime_str)
                    self.published_at = standardTaipeiDateToTimestamp(datetime_str)
            except Exception as e:
                print("Error extracting from external-normal-style__Date div:", e)

            # Extract author
            section=soup.find("section",class_="credits__CreditsWrapper-sc-93b3ab5-0 gReTcs normal-credits")
            print("section:",section)
            if section:
                author_ul=section.find("ul")
                if author_ul:
                    self.authors.append(author_ul.get_text().strip())

            # Additional extraction from <p style="text-align: justify;">
            try:
                author_p = soup.find("p", style=lambda value: value and "text-align: justify" in value)
                print("Found author_p:", author_p)

                if author_p:
                    author_text = author_p.get_text(strip=True)
                    print("Extracted author from <p style='text-align: justify;'>:", author_text)
                    self.authors.append(author_text)
            except Exception as e:
                print("Error extracting author from <p style='text-align: justify;'>:", e)

            # Add journalist extraction separately
            journalist_p_tags = soup.find_all("p", style="text-align: justify;")
            for p_tag in journalist_p_tags:
                text = p_tag.get_text().strip()
                if text.startswith("記者"):
                    import re
                    match = re.search(r"記者(\S+)\s*/", text)
                    if match:
                        journalist_name = match.group(1)
                        print("Journalist:", journalist_name)
                        self.authors.append(journalist_name)
                        break  # Stop after finding the first match

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


            # Additional fallback: extract images from <p style="text-align: center;"> with <img> inside
            try:
                centered_paragraphs = soup.find_all("p")
                for p in centered_paragraphs:
                    style = p.get("style", "")
                    if "text-align: center" in style:
                        image_tag = p.find("img")
                        if image_tag and image_tag.get("src"):
                            image_url = image_tag["src"]
                            if image_url not in self.images:
                                print("Found fallback image in centered <p>:", image_url)
                                self.images.append(image_url)
            except Exception as e:
                print("Error in fallback centered image extraction:", e)



            print("content_div:",content_div)
            print("self.title:",self.title)
            print("self.content:",self.content)
            print("self.images:",self.images)
            print("self.authors:",self.authors)
            print("self.published_at:",self.published_at)
            print("self.origin:",self.origin)
            
        finally:
                driver.quit()

class NowNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="NowNews"
        self.max_pages=2
        self.max_workers=5

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            latest_news_url = f"https://www.nownews.com/cat/breaking/page/{page}"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.list-wrap li")
                # filtered_articles=[]
                # for article in articles:
                #     title=article.find("p",class_="date")
                #     print(title)
                #     if title and "PR" not in title:
                #         filtered_articles.append(article)

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    # print("article:",article)
                    a_tag = article.select_one("a")
                    if a_tag:
                        print("a_tag:",a_tag)
                        full_url = a_tag['href']
                        page_urls.append(full_url)
                        print("full_url:",full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                print("page_urls:",page_urls)
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
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
            self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract author
        author_a=soup.find("a",{"data-sec":"reporter"})
        if author_a:
            self.authors.append(author_a.get_text().strip())
        author_div=soup.find("div",class_="info")
        if author_div:
            author_p=author_div.find("p")
            if author_p:
                text=author_p.get_text()
                journalist_match = re.search(r'記者([\u4e00-\u9fff]{2,3})', text)
                if journalist_match and journalist_match.group(1) not in self.authors:
                    self.authors.append(journalist_match.group(1))

        # Extract images
        content_div=soup.find("div",class_="containerBlk mb-1")
        if content_div:
            images=content_div.find_all("figure")
            print("images:",images)
            for image in images:
                self.images.append(image.find("img")["src"])

class StormMedia(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="StormMedia"
        self.max_pages=2
        self.max_workers=5
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            base_url = "https://www.storm.mg"
            latest_news_url = f"https://www.storm.mg/channel/all/0/{page}"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()
            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.ArticleCardWithMeta")
                # filtered_articles=[]
                # for article in articles:
                #     title=article.find("p",class_="date")
                #     print(title)
                #     if title and "PR" not in title:
                #         filtered_articles.append(article)

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    # print("article:",article)
                    a_tag = article.select_one("a")
                    if a_tag:
                        print("a_tag:",a_tag)
                        href = a_tag['href']
                        full_url=base_url+href
                        page_urls.append(full_url)
                        print("full_url:",full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                print("page_urls:",page_urls)
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
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
            self.published_at=standardTaipeiDateToTimestamp(date)

        # Additional extraction from nested <div data-v-xxxx> inside a date container
        try:
            container_div = soup.find("div", class_="my-4 flex gap-x-5 text-smg-typography-body-16-r text-smg-gray-600")
            print("Found container_div:", container_div)

            if container_div:
                inner_div = container_div.find("div")  # First inner <div>
                print("Found inner_div:", inner_div)

                if inner_div:
                    datetime_str = inner_div.get_text(strip=True)
                    print("Extracted datetime from inner_div:", datetime_str)
                    self.published_at = standardTaipeiDateToTimestamp(datetime_str)
        except Exception as e:
            print("Error extracting from nested divs:", e)

        # Extract author
        self.authors.append(soup.find("a",class_="generalLink text-smg-typography-caption-14-r text-smg-red-primary hover:underline").get_text().strip())

        # Extract images
        content_div=soup.find("div",class_="coverImg")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

class TVBS(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="TVBS"
        self.max_pages=1

    def _get_article_urls(self):
        latest_news_url = "https://news.tvbs.com.tw/realtime"
        base_url="https://news.tvbs.com.tw"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("div.news_list div.list ul li")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
                self.published_at=standardTaipeiDateToTimestamp(published_at)
            
            print("self.authors:", self.authors)
            print("Published At:", published_at)
        
        # Extract images
        content_div=soup.find("div",class_="article_new")
        if content_div:
            image_div=content_div.find("div",class_="img_box")
            print("image_div:",image_div)
            if image_div:
                image=image_div.find("img")
                if image:
                    self.images.append(image["src"])
        content_div=soup.find("div",{"itemprop":"articleBody"})
        if content_div:
            image_div=content_div.find_all("div",class_="img")
            print("image_div:",image_div)
            if image_div:
                for img_div in image_div:
                    image=img_div.find("img")
                    if image:
                        self.images.append(image["data-original"])
        print("image:",self.images)


class EBCNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="EBCNews"
        self.max_pages=2
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://news.ebc.net.tw/realtime"
        base_url = "https://news.ebc.net.tw"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Let the initial page load

            scroll_steps = 3*max_pages  # You can adjust this: more steps = more scroll depth

            for i in range(scroll_steps):
                print(f"Scrolling step {i+1}")
                driver.execute_script("window.scrollBy(0, 1000);")  # Scroll down 1000 pixels
                time.sleep(0.2)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('div.tab_content a.item.row_box')
            print(f"Total articles found: {len(articles)}")

            for article in articles:
                href = article.get('href')
                if href:
                    full_url = base_url + href if href.startswith("/") else href
                    if full_url not in all_urls:
                        all_urls.append(full_url)

        finally:
            driver.quit()



        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def parse_article(self, soup):
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
            self.published_at=standardTaipeiDateToTimestamp(date)
        if date_div is None:
            date_div=soup.find("div",class_="article_info_date")
            print("date_div:",date_div)
            if date_div:
                date=" ".join(p.get_text(strip=True) for p in date_div.find_all("div"))
                self.published_at=standardTaipeiDateToTimestamp(date)
            
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="ETtoday"
        self.max_pages=1

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            latest_news_url= "https://www.ettoday.net/news/news-list.htm"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.part_list_2 h3")
                print("articles:",articles)

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_selectors=[
             {"selector": "h1.title", "text": True}, 
             {"selector":"h1.title_article","text": True}
        ]
        for selector in title_selectors:
            element = soup.select_one(selector["selector"])
            if element:
                self.title=element.get_text()

        # Extract content
        content_selectors=[
             {"selector": "article", "text": True}, 
             {"selector":"div.story","text": True}
        ]
        for selector in content_selectors:
            element = soup.select_one(selector["selector"])
            if element:
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
                    print("date:",date)
                    self.published_at = standardTaipeiDateToTimestamp(date)
        # Additional extraction from <time> tag with 'datetime' attribute
        try:
            published_time_tag = soup.find("time", itemprop="datePublished")
            print("Found published_time_tag:", published_time_tag)
            if published_time_tag:
                datetime_str = published_time_tag.get("datetime", "").strip()
                if not datetime_str or len(datetime_str) <= 5:
                    datetime_str = published_time_tag.get_text(strip=True)
                print("Extracted datetime:", datetime_str)
                self.published_at = standardTaipeiDateToTimestamp(datetime_str)
        except Exception as e:
            print("Error extracting from <time itemprop='datePublished'>:", e)

        print("self.published_at:", self.published_at)

        # Extract images
        self.images = []
        story_div = soup.find("div",class_="story")
        if story_div:
            img=story_div.find("img")
            if img:
                print("image_div:",img)
                if img:
                    self.images.append(img["src"])
                print("self.images:", self.images)

class NewTalk(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="NewTalk"
        self.max_pages=2
        self.max_workers=5
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        def fetch_page_articles(page):
            base_url = "https://newtalk.tw"
            latest_news_url = f"{base_url}/news/summary/{today}/{page}"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("ul.category-list li")
                filtered_articles=[]
                for article in articles:
                    title=article.find("p",class_="date")
                    print(title)
                    if title and "PR" not in title:
                        filtered_articles.append(article)

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                page_urls = []
                for article in filtered_articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url not in page_urls:
                            page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        # Running the code
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",class_="articleBody clearfix")
        if content_div:
            news_img=content_div.find_all("div",class_="news_img")
            if news_img:
                print("Hi!")
                for news_div in news_img:
                    news_div.decompose()
        print(content_div)
        paragraphs=content_div.find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract published date
        p_element=soup.find("p",class_="publish")
        print("p_element:",p_element)
        if p_element:
            text=p_element.find("span").get_text()
            print("text:",text)
            date=text.replace("發布","").strip()
            self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract author
        author_a=soup.find("a",class_="author")
        author=''
        if author_a:
            author=author_a.get_text().strip()
            if author!='':
                self.authors.append(author)
        print(author)
        if author=='':
            if paragraphs:
                firstParagraph=paragraphs[0]
                if firstParagraph:
                    firstParagraphText=firstParagraph.get_text()
                    print("firstParagraphText:",firstParagraphText)
                    match = re.search(r'（中央社記者([\u4e00-\u9fff]{2,3})(?:／)?', firstParagraphText)
                    if match:
                        print("match:",match)
                        author=match.group(1).strip()
                        self.authors.append(author)
                    else:
                        print("No match found")
        # Extract images
        content_div=soup.find("div",class_="news_content")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

class CTINews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="CTINews"

    def _get_article_urls(self):
        latest_news_url = "https://ctinews.com/news/topics/KDdek5vgXx"
        base_url="https://ctinews.com"
        print(f"Loading page: {latest_news_url}")

        all_urls=[]
        headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://google.com/',
                        'Connection': 'keep-alive',
                        'DNT': '1',
                        'Upgrade-Insecure-Requests': '1',
                    }
        response=requests.get(latest_news_url,headers=headers)
        html=response.text
        # print("html:",html)
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select('div.feed-wrapper')
        # print("articles:",articles)
        for article in articles:
                a_tag = article.select_one("a")
                print("a_tag:",a_tag)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("/news/items"):
                        full_url = base_url + href
                        print("✅ full_url:", full_url)
                        all_urls.append(full_url)
        articles = soup.select('div.news-hover-section')
        for article in articles:
                a_tag = article.select_one("a")
                print("a_tag:",a_tag)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("/news/items"):
                        full_url = base_url + href
                        if full_url not in all_urls:
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)

        articles = soup.select('div.base-card-sm:not(.with-video)')
        for article in articles:
                a_tag = article.select_one("a")
                print("a_tag:",a_tag)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("/news/items"):
                        full_url = base_url + href
                        if full_url not in all_urls:
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)

        articles = soup.select('div.base-card-md:not(.with-video)')
        for article in articles:
                a_tag = article.select_one("a")
                print("a_tag:",a_tag)
                if a_tag:
                    href = a_tag['href']
                    if href.startswith("/news/items"):
                        full_url = base_url + href
                        if full_url not in all_urls:
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)


        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    def parse_article(self, soup):
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
        # Extract published time (e.g., 2025/08/13 15:49)
        time_span = soup.find("span", class_="text-gray-400")
        # Extract published time (e.g., 發布: 2025/08/13 15:49)
        try:
            time_span = soup.find("span", class_="text-gray-400")
            if time_span:
                time_text = time_span.get_text(strip=True)
                print("published time text:", time_text)
                
                if "發布:" in time_text:
                    datetime_str = time_text.replace("發布:", "").strip()
                    print("published datetime:", datetime_str)
                    # Optionally, convert to timestamp
                    self.published_at = standardTaipeiDateToTimestamp(datetime_str)
        except Exception as e:
            print("Error extracting time:", e)
            self.published_at=standardTaipeiDateToTimestamp(date)
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
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="FTV"
        self.max_pages=1
        

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.ftvnews.com.tw/realtime/"
        base_url = "https://www.ftvnews.com.tw"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('ul[id="realtime"] li')
            for article in articles:
                    a_tag = article.select_one("div.news-block a")
                    if a_tag:
                        href = a_tag['href']
                        if href.startswith("/news/detail/"):
                            full_url = base_url + href
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select('ul[id="realtime"] li')

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("div.news-block a")
                    if a_tag:
                        href = a_tag['href']
                        if href.startswith("/news/detail/"):
                            full_url = base_url + href
                            print("✅ full_url:", full_url)
                            all_urls.append(full_url)
            print("all_urls:",all_urls)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        return all_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver=self.get_chrome_driver()

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
                self.published_at=standardTaipeiDateToTimestamp(date)
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
        finally:
                driver.quit()

class TaiwanNews(News):
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name="TaiwanNews"
        self.max_pages=2
        self.max_workers = 1  # Override field in child class

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            page_urls=[]
            latest_news_url = f"https://newstaiwan.net/category/%e7%84%a6%e9%bb%9e/page/{page}/"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("article.l-post.grid-post.grid-base-post")
                
                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url not in page_urls:
                            page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        driver=self.get_chrome_driver()

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

            # Extract title
            title_tag = soup.find("h1", class_="is-title post-title")
            print("title_tag:",title_tag)
            self.title = title_tag.get_text().strip() if title_tag else "No title found"

            # Extract content
            content_div = soup.find("div",class_="post-content")
            print("content_div:",content_div)
            if content_div:
                paragraphs=content_div.find_all("p")
                if paragraphs:
                    self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

            # Extract published date
            date_time=soup.find("time",class_="post-date")
            if date_time:
                date=date_time.get_text().replace(' ', '').strip()
                print("date:",date)
                self.published_at=standardChineseDatetoTimestamp(date)
                print("date:",date)

            # Extract images
            image_div=soup.find("div",class_="featured")
            if image_div:
                image=image_div.find("img")
                if image:
                    self.images.append(image["src"])

            # Extract author
            author_a=soup.find("a",rel="author")
            print("author_a:",author_a)
            if author_a:
                author=author_a.get_text()
                if author:
                    author=author.replace(" ","")
                    self.authors.append(author)

        finally:
                driver.quit()


class CTWant(News):
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name="CTWant"
        self.max_pages=2
        self.max_workers = 1  # Override field in child class

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            page_urls=[]
            latest_news_url = f"https://www.ctwant.com/category/%E6%9C%80%E6%96%B0?page={page}/"
            base_url="https://www.ctwant.com/"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.p-realtime__list div.p-realtime__item")
                
                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        href = a_tag['href']
                        full_url=base_url+href
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_h1 = soup.find("h1", class_="p-article__title")
        self.title = title_h1.get_text().strip() if title_h1 else "No title found"

        # Extract content
        paragraphs = soup.find("article").find_all("p")
        self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract author
        author_span=soup.find("span",class_="author-name")
        if author_span:
            author=author_span.get_text()
            if author:
                self.authors.append(author)

        # Extract published date
        time=soup.find("time",class_="p-article-info__time")
        print("time:",time)
        if time:
            date=time.get_text()
            if date:
                self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract images
        content_div=soup.find("div",class_="p-article__img-box")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])


class TSSDNews(News):
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name="TSSDNews"
        self.max_pages=2
        self.max_workers = 1  # Override field in child class

    def _get_article_urls(self):
        max_pages=self.max_pages
        max_workers=self.max_workers
        def fetch_page_articles(page):
            page_urls=[]
            latest_news_url = f"https://www.tssdnews.com.tw/index.php?page={page}&FID=63"
            base_url="https://www.tssdnews.com.tw"
            print(f"Loading page: {latest_news_url}")

            # Each thread must create its own driver
            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div[id='story'] a")
                print("articles:",articles)
                
                for article in articles:
                    href = article["href"]
                    if href:
                        full_url=base_url+href
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")
        return all_urls
    
    def _fetch_and_parse(self):
        self.parse_article()

    def parse_article(self):
        # 使用非 headless 模式（可視化）
        base_url="https://www.tssdnews.com.tw"
        driver=self.get_chrome_driver()

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

            # Extract title
            title_div = soup.find("div", id="news_title")
            print("title_div:",title_div)
            self.title = title_div.get_text().strip() if title_div else "No title found"

            # Extract content
            content_div = soup.find("div",id="article")
            print("content_div:",content_div)
            if content_div:
                self.content=content_div.get_text()

            # Extract published date+author
            info=soup.find("div",id="news_author")
            if info:
                text = info.get_text(strip=True)
                print("Full text:", text)

                # Extract author (記者 Name ／ Location 報導)
                author_match = re.search(r'記者([\u4e00-\u9fff]{2,3})', text)
                if author_match:
                    author = author_match.group(1)
                    print("Author:", author)
                    self.authors.append(author)
                else:
                    author = None
                    print("No author found")

                # Extract date (matches YYYY/MM/DD)
                date_match = re.search(r'\d{4}/\d{2}/\d{2}', text)
                if date_match:
                    date_str = date_match.group(0)
                    print("Date:", date_str)
                    self.published_at=standardTaipeiDateToTimestamp(date_str)
                else:
                    date_str = None
                    print("No date found")
            

            # Extract images
            image_div=soup.find("div",id="news_photo")
            if image_div:
                image=image_div.find("img")
                if image:
                    full_url=base_url+image["src"]
                    self.images.append(full_url)

        finally:
                driver.quit()

class CTS(News):
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name="CTS"
        self.max_pages=1
        self.max_workers = 5  # Override field in child class

    def _get_article_urls(self):
        max_pages=self.max_pages
        def fetch_page_articles(page):
            page_urls=[]
            latest_news_url = "https://news.cts.com.tw/real/index.html"
            base_url="https://news.cts.com.tw"
            print(f"Loading page: {latest_news_url}")

            driver = self.get_chrome_driver()

            try:
                driver.get(latest_news_url)
                time.sleep(2)  # wait for JS

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("div.newslist-container a")
                
                for article in articles:
                    full_url = article["href"]
                    page_urls.append(full_url)

                for page in range(max_pages-1):
                    # Scroll to bottom
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # Wait for articles to load after scroll

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    articles = soup.select("div.newslist-container a")
                    
                    for article in articles:
                        full_url = article["href"]
                        if full_url not in page_urls:
                            page_urls.append(full_url)

                    print(f"Page {page+1}: Found {len(articles)} articles")

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            finally:
                driver.quit()
        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        return all_urls
    
    def parse_article(self, soup):
        # Extract title
        title_h1 = soup.find("h1", class_="artical-title")
        self.title = title_h1.get_text().strip() if title_h1 else "No title found"

        # Extract content
        content_div = soup.find("div",class_="artical-content")
        if content_div:
            paragraphs=content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        # Extract author
        author_span=soup.find("span",class_="author-name")
        if author_span:
            author=author_span.get_text()
            if author:
                self.authors.append(author)

        # Extract published date
        time=soup.find("time",{"itemprop":"datePublished"})
        print("time:",time)
        if time:
            date=time.get_text()
            if date:
                self.published_at=standardTaipeiDateToTimestamp(date)

        # Extract images
        content_div=soup.find("div",class_="artical-img")
        if content_div:
            images=content_div.find_all("img")
            for image in images:
                self.images.append(image["src"])

        # Extract news source
        news_src_p=soup.find("p",class_="news-src")
        if news_src_p:
            news_source=news_src_p.get_text()
            if "華視新聞" not in news_source:
                news_source=news_source.replace("新聞來源：","").strip()
                try:
                    self.origin=chineseMediaTranslationUtil.map_chinese_media_to_enum(news_source)
                except ValueError as e:
                    raise UnmappedMediaNameError(news_source) from e

class YahooNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name="YahooNews"
        self.max_pages=2
        

    def _get_article_urls(self):
        def scroll_and_collect(driver, url, base_url):
            driver.get(url)
            scroll_step = 1000
            total_scrolls = 5 * self.max_pages
            for i in range(total_scrolls):
                driver.execute_script(f"window.scrollTo(0, {scroll_step * (i + 1)});")
                time.sleep(0.3)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select('ul#stream-container-scroll-template li.StreamMegaItem')
            print(f"✅ {len(articles)} articles found at: {url}")
            urls = []
            for article in articles:
                a_tag = article.find("a")
                if a_tag and a_tag.get("href"):
                    href = a_tag["href"]
                    full_url = base_url + href if href.startswith("/") else href
                    if full_url not in urls:
                        urls.append(full_url)
            return urls

        # Your two target Yahoo URLs
        archive_urls = [
            "https://tw.news.yahoo.com/tw.realnews.yahoo.com--%E6%89%80%E6%9C%89%E9%A1%9E%E5%88%A5/archive",
            "https://tw.news.yahoo.com/archive"
        ]
        base_url = "https://tw.news.yahoo.com"

        # Get options and driver_path
        driver=self.get_chrome_driver()

        all_urls = []

        try:
            for url in archive_urls:
                new_urls = scroll_and_collect(driver, url, base_url)
                for u in new_urls:
                    if u not in all_urls:
                        all_urls.append(u)
        finally:
            driver.quit()

        print(f"🎯 Total unique articles collected: {len(all_urls)}")
        return all_urls

    
    def parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag and title_tag.has_attr("content") else "No title found"
        print("self.title:", self.title)

        # Extract images
        self.images = []
        figure = soup.find("figure")
        if figure:
            image_div=figure.find_all("img")
            for img in image_div:
                if img and img.has_attr("src"):
                    self.images.append(img["src"])
            print("self.images:", self.images)

        #Extract published date
        date_div = soup.find("div", class_="caas-attr-time-style")
        if date_div:
            date_time=date_div.find("time")
            if date_time:
                date=date_time.get_text(strip=True) 
                if date:
                    print("date:", date)
                    self.published_at = standardChineseDatetoTimestamp(date)
        if self.published_at is None:
            print("self.published_at:", self.published_at)
            



        # Extract origin
        image_div=soup.find("div",class_="mb-2 flex items-center justify-between lg:justify-start")
        if image_div:
            image=image_div.find("img")
            if image:
                alt=image['alt']
                if alt and "Yahoo新聞" in alt:
                    try:
                        self.origin=chineseMediaTranslationUtil.map_chinese_media_to_enum(alt)
                    except ValueError as e:
                        raise UnmappedMediaNameError(alt) from e
        

        # Extract authors
        self.authors = []

        # Find the div that contains the span
        author_div = soup.find("div", class_="mb-0.5")
        if author_div:
            # Find the span with author info
            span = author_div.find("span")
            if span:
                authors_text = span.get_text(strip=True)
                if authors_text:
                    # Split by separator "｜" (full-width vertical bar)
                    for author in authors_text.split("｜"):
                        if author and "記者" not in author:  # Filter out job titles
                            self.authors.append(author.strip())

        print("self.authors:", self.authors)

        # Extract publish datetime
        # self.publish_time = None  # Initialize

        # Try to find ANY <time> tag with a datetime attribute
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            time = time_tag["datetime"].strip()
            self.published_at=YahooNewsToTimestamp(time)
            print("✅ Found datetime:", self.published_at)
        else:
            print("❌ No <time> tag with datetime found")


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

class MyGoPenNews(News):
    def __init__(self, url=None):
        super().__init__(url)
        self.media_name = "MyGoPenNews"
        self.feed_url = "https://www.mygopen.com/feeds/posts/default?alt=rss"
        self.max_articles = 10

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
        for abbr in soup.find_all("abbr"):
            title = abbr.get("title")
            if title and "T" in title and title.startswith("202"):
                # 例如標準格式：2025-09-06T09:53:00+08:00
                self.published_at = standardTaipeiDateToTimestamp(title)
                break  # 找到第一個就跳出

        # 查核記者（MyGoPen 通常沒有）
        self.authors = []

        # 內容
        content_div = soup.find("div", class_="post-body entry-content")
        self.content = ""

        if content_div:
            # 取得所有文字區段（包含 div, h3, p, br 等混合結構）
            parts = []
            for elem in content_div.descendants:
                if elem.name == "br":
                    parts.append("\n")
                elif isinstance(elem, str):
                    text = elem.strip()
                    if text:
                        parts.append(text)

            self.content = "".join(parts).strip()

        # 圖片
        self.images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.endswith(".jpg"):
                self.images.append(src)

class TFCNews(News):  # ✅ 改這裡:
    def __init__(self, url=None):
        super().__init__(url)  # ✅ 呼叫父類別 News 的 constructor
        self.media_name = "TFCNews"
        self.max_pages = 2
        self.origin = "native"

    def _get_article_urls(self):
        driver = self.get_chrome_driver()
        article_urls = []

        for page in range(1, self.max_pages + 1):
            url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"
            print(f"🔗 開啟第 {page} 頁: {url}")
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
                )
                articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
                print(f"✅ 找到 {len(articles)} 篇文章")

                for article in articles:
                    try:
                        a_tag = article.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")
                        if href and href not in article_urls:
                            article_urls.append(href)
                    except Exception as e:
                        print("⚠️ 找 <a> 錯誤：", e)

            except Exception as e:
                print(f"❌ 頁面載入失敗: {e}")

            time.sleep(1.2)

        driver.quit()
        print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
        return article_urls

    def parse_article(self, soup):
        driver = self.get_chrome_driver()

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

        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(str(self.url))
            time.sleep(2)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            entry_content = soup.find("div", class_="entry-content")
            containers = entry_content.find_all("div", class_="kt-inside-inner-col")
            paragraphs = []

            # ✅ Step 1: 嘗試從 kadence advanced heading 擷取標題
            self.title = ""
            heading_tags = soup.select("p.wp-block-kadence-advancedheading")
            for tag in heading_tags:
                text = tag.get_text(strip=True)
                if "？" in text or "?" in text:
                    self.title = text
                    break

            # ✅ Step 2: fallback to <strong> 包含問號
            if not self.title:
                for container in containers:
                    for p in container.find_all("p"):
                        strong = p.find("strong")
                        if strong and ("？" in strong.text or "?" in strong.text):
                            self.title = strong.get_text(strip=True)
                            break
                    if self.title:
                        break

            if not self.title:
                self.title = "（無標題）"

            print("self.title:", self.title)

            # ✅ Step 3: 擷取內文
            for container in containers:
                for p in container.find_all("p"):
                    text = p.get_text(strip=True)
                    if not text or text == self.title:
                        continue
                    if any(keyword in text for keyword in ["發佈", "更新", "責任編輯", "記者", "報告編號"]):
                        continue
                    if len(text) > 30:
                        paragraphs.append(text)

            self.content = "\n\n".join(paragraphs)

            # ✅ 擷取作者
            text_all = soup.get_text()
            match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text_all)
            if match:
                self.authors.append(match.group(1))
            match = re.search(r"責任編輯[:：]?\s*([^\s，、\n]+)", text_all)
            if match:
                self.authors.append(match.group(1))

            # ✅ 發佈時間
            match = re.search(r"發[布佈][:：]?\s*(\d{4}-\d{2}-\d{2})", text_all)
            if match:
                date_str = match.group(1)
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    self.published_at = int(dt.timestamp())
                except Exception as e:
                    print(f"⚠️ 日期格式錯誤：{date_str} - {e}")

            # ✅ 圖片
            self.images = []
            for img in soup.find_all("img"):
                src = img.get("src")
                if src and src.endswith(".jpg"):
                    self.images.append(src)

        finally:
            driver.quit()
                        

class FactcheckLab(News):
    def __init__(self, url=None):
        super().__init__(url)  # Call parent constructor
        self.media_name = "FactcheckLab"
        self.max_pages = 1
        self.max_workers = 5

    def _get_article_urls(self):
        max_pages = self.max_pages

        def fetch_page_articles(page: int):
            # Factcheck Lab 首頁會載入最新文章，無明確分頁參數
            # 若未來有分頁，可在此擴充
            page_urls = []
            base_url = "https://www.factchecklab.org"
            print(f"Loading page: {base_url}")

            # 先嘗試使用 requests（站點為靜態可抓）
            try:
                res = requests.get(base_url, timeout=15)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                articles = soup.select("a.post-card-image-link")

                for a_tag in articles:
                    href = a_tag.get("href")
                    if href:
                        full_url = urljoin(base_url, href)
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            except Exception as e:
                print(f"Requests failed, fallback to Selenium for page {page}: {e}")

                # 若需要 JS 執行再回退到 Selenium
                driver = self.get_chrome_driver()
                try:
                    driver.get(base_url)
                    time.sleep(2)  # wait for basic render

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    articles = soup.select("a.post-card-image-link")

                    for a_tag in articles:
                        href = a_tag.get("href")
                        if href:
                            full_url = urljoin(base_url, href)
                            page_urls.append(full_url)

                    # 若有需要滾動載入，可在此加入滾動邏輯（目前站點不需要）
                    print(f"Found {len(page_urls)} articles on page {page}")
                    return page_urls
                finally:
                    driver.quit()

        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        # 去重
        all_urls = list(dict.fromkeys(all_urls))
        return all_urls

    def parse_article(self, soup: BeautifulSoup):
        base_url = "https://www.factchecklab.org"
        # Title
        h1 = soup.find("h1")
        self.title = h1.get_text(strip=True) if h1 else "No title found"

        # Publish date
        # <time class="byline-meta-date" datetime="...">
        time_tag = soup.find("time", class_="byline-meta-date")
        if time_tag and time_tag.has_attr("datetime"):
            date_str = time_tag["datetime"]
            # 若父類別提供 ISO8601 轉 timestamp 工具
            try:
                self.published_at = standardTaipeiDateToTimestamp(date_str)
            except Exception:
                # 若工具不可用，可退回原字串
                self.published_at = date_str
        
        # Content
        # 文章本體大多在 <article> 中
        content_div = soup.find("article")
        if content_div:
            paragraphs = content_div.find_all("p")
            content_texts = []
            for p in paragraphs:
                txt = p.get_text(strip=True)
                if txt:
                    content_texts.append(txt)
            self.content = "\n".join(content_texts)

        # Author(s) — 網站未必固定顯示作者，若有可擴充選擇器
        # 嘗試幾種常見位置
        author_candidates = []
        # 例：class 可能為 byline 或作者連結
        for sel in ["a.post-card-author", ".byline-author a", ".byline-author", "a.author", ".author"]:
            for tag in soup.select(sel):
                txt = tag.get_text(strip=True)
                if txt:
                    author_candidates.append(txt)

        # 去重後加入
        for author in list(dict.fromkeys(author_candidates)):
            self.authors.append(author)
        
        # First image（封面或首圖）
        content=soup.find('section',class_="post-full-content")
        print("content:",content)
        # Find all <div> tags with a specific style
        target_divs = content.find_all("div", style="border:2px; border-style:solid; border-color:#479393; padding: 1em")
        print("target_divs:",target_divs)
        # Remove them
        for div in target_divs:
            div.decompose()
        print("content:",content)
        if content:
            images=content.find_all("img")
            print("images:",images)
            if images:
                for image in images:
                    image_url=image['src']
                    self.images.append(image_url)
        print("self.images:",self.images)

        # News source / origin
        # Factcheck Lab 多為自家出品，若需要對外媒做 mapping，可在此擴充
        # 例：若文末有「來源」段落，可嘗試解析：
        source_text = None
        for sel in ["p", "li"]:
            for tag in soup.select(sel):
                txt = tag.get_text(strip=True)
                if txt and (txt.startswith("來源：") or txt.startswith("資料來源：")):
                    source_text = txt.replace("來源：", "").replace("資料來源：", "").strip()
                    break
            if source_text:
                break
        if source_text:
            try:
                self.origin = chineseMediaTranslationUtil.map_chinese_media_to_enum(source_text)
            except ValueError as e:
                # 若你的系統需要嚴格映射，則拋出；否則可忽略或記錄
                # raise UnmappedMediaNameError(source_text) from e
                pass

class TaroNews(News):
    def __init__(self, url=None):
        super().__init__(url)  # ✅ 呼叫父類別 News 的 constructor
        self.media_name = "TaroNews"
        self.max_pages = 2
        self.origin = "native"

    def _get_article_urls(self):
        max_pages = self.max_pages

        def fetch_page_articles(page: int):
            page_urls = []
            base_url = "https://taronews.tw"
            latest_news='https://taronews.tw/archives'
            url = f"{latest_news}/page/{page}/"
            print(f"Loading page: {url}")

            try:
                res = requests.get(url, timeout=15)  # ✅ 用正確的分頁 URL
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                articles = soup.select("div.listing-thumbnail article")

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                for article in articles:
                    a_tag = article.select_one("h2.title a")
                    if a_tag:
                        href = a_tag['href']
                        full_url = base_url + href
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            except Exception as e:
                print(f"Requests failed, fallback to Selenium for page {page}: {e}")

                # 若需要 JS 執行再回退到 Selenium
                driver = self.get_chrome_driver()
                try:
                    driver.get(url)  # ✅ 使用分頁 URL
                    time.sleep(2)  # wait for basic render

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    articles = soup.select("div.listing-thumbnail article")

                    if not articles:
                        print(f"No articles found on page {page}.")
                        return []

                    
                    for article in articles:
                        a_tag = article.select_one("h2.title a")
                        if a_tag:
                            href = a_tag['href']
                            full_url = base_url + href
                            page_urls.append(full_url)

                    print(f"Found {len(page_urls)} articles on page {page}")
                    return page_urls
                finally:
                    driver.quit()

        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        # 去重
        all_urls = list(dict.fromkeys(all_urls))
        return all_urls

    def parse_article(self, soup):
        driver = self.get_chrome_driver()

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

        print("🔗 嘗試連線至：", self.url)

        try:
            driver.get(str(self.url))
            time.sleep(2)

            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")

            # title
            title=soup.find("span",class_="post-title")
            if title:
                self.title=title.get_text(strip=True)
            

            print("self.title:", self.title)

            # content
            content_div=soup.find('div',class_="single-post-content")
            if content_div:
                content_p=content_div.find_all('p')
                paragraphs = []
                for p in content_p:
                    paragraphs.append(p.get_text(strip=True))  # ✅ 取得段落純文字
                self.content = "\n".join(paragraphs)

            # ✅ 擷取作者
            span_author_name = soup.find("span",class_="post-author-name")
            if span_author_name:
                author_name = span_author_name.find('b')
                if author_name:
                    self.authors.append(author_name.get_text(strip=True))  # ✅ 轉為 str

            # ✅ 發佈時間
            published_at_time = soup.find("time", class_="post-published")
            if published_at_time:
                publication_date_tag = published_at_time.find('b')
                if publication_date_tag:
                    date_str = publication_date_tag.get_text(strip=True)
                    self.published_at = standardTaipeiDateToTimestamp(date_str)

            # ✅ 圖片
            self.images = []
            header_div = soup.find('div', class_='post-header')
            if header_div and 'style' in header_div.attrs:
                style_attr = header_div['style']
                match = re.search(r'url\("(.+?)"\)', style_attr)
                if match:
                    image_url = match.group(1)
                    self.images.append(image_url)  # ✅ 加入圖片列表
                else:
                    print("No image URL found in style.")
            else:
                print("Header div not found or no style attribute.")

        finally:
            driver.quit()


class GVM(News):
    def __init__(self, url=None):
        super().__init__(url)  # ✅ 呼叫父類別 News 的 constructor
        self.media_name = "GVM"
        self.max_pages = 2
        self.origin = "native"

    def _get_article_urls(self):
        max_pages=self.max_pages
        latest_news_url = "https://www.gvm.com.tw/newest"
        base_url="https://www.gvm.com.tw"
        print(f"Loading page: {latest_news_url}")

        driver=self.get_chrome_driver()

        all_urls = []

        try:
            driver.get(latest_news_url)
            time.sleep(2)  # Wait for initial load

            soup = BeautifulSoup(driver.page_source, "html.parser")
            articles = soup.select("div.item-card_content")
            for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                        if full_url not in all_urls:
                            all_urls.append(full_url)


            for page in range(max_pages-1):
                # Scroll to bottom
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for articles to load after scroll

                soup = BeautifulSoup(driver.page_source, "html.parser")
                articles = soup.select("li.item-list_li")

                print(f"Page {page+1}: Found {len(articles)} articles")

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        full_url = a_tag['href']
                        if full_url.startswith("/"):  # Ensure it's a full URL
                            full_url = base_url + full_url
                            all_urls.append(full_url)
                        if full_url not in all_urls:
                            all_urls.append(full_url)

        finally:
            driver.quit()

        print(f"Total articles found: {len(all_urls)}")
        print("all_urls:",all_urls)
        return all_urls

    def parse_article(self, soup: BeautifulSoup):
        # ✅ 擷取標題（含 fallback）
        self.title = ""
        heading_tags = soup.select("h1.article-head_h1")
        for tag in heading_tags:
            text = tag.get_text(strip=True)
            self.title = text  # fallback 預設
            if "？" in text or "?" in text:
                break

        # ✅ 擷取內文
        self.content = ""
        article = soup.find("div", class_="article-content")
        if article:
            parts = []
            for elem in article.descendants:
                if elem.name == "br":
                    parts.append("\n")
                elif isinstance(elem, str):
                    text = elem.strip()
                    if text:
                        parts.append(text)
            self.content = "".join(parts).strip()

        # ✅ 擷取作者與發佈時間
        self.authors = []
        self.published_at = None
        header_info = soup.find("div", class_="article-head_grid")
        if header_info:
            # 擷取作者
            author_a = header_info.find("a", class_="article-head_author")
            if author_a:
                author = author_a.get_text(strip=True)
                self.authors.append(author)

            # 擷取日期
            div_elements = header_info.find_all("div", class_="article-head_box")
            for div in div_elements:
                # 找出可能是日期的 p 標籤
                p_tags = div.find_all("p", class_="article-head_grey")
                for p in p_tags:
                    text = p.get_text(strip=True)
                    if any(token in text for token in ["202", "201", "-", "/"]):  # 粗略偵測日期格式
                        try:
                            self.published_at = standardTaipeiDateToTimestamp(text)
                            raise StopIteration  # 提早跳出所有迴圈
                        except Exception as e:
                            print(f"⚠️ Unable to parse date: {text}")
                            continue
            else:
                print("⚠️ No valid date found in header info.")

        # ✅ 圖片處理（確保為完整 URL）
        self.images = []
        figure = soup.find("figure", class_="article-img")
        if figure:
            img = figure.find("img")
            if img:
                src = img.get("src")
                if src:
                    full_img_url = urljoin("https://www.gvm.com.tw", src)
                    self.images.append(full_img_url)

class PChome(News):
    def __init__(self, url=None):
        super().__init__(url)  # ✅ 呼叫父類別 News 的 constructor
        self.media_name = "PChome"
        self.max_pages = 2
        self.origin = "native"

    def _get_article_urls(self):
        max_pages = self.max_pages

        def fetch_page_articles(page: int):
            page_urls = []
            base_url = "https://news.pchome.com.tw"
            latest_news='https://news.pchome.com.tw/today'
            url = f"{latest_news}/{page}/"
            print(f"Loading page: {url}")

            try:
                res = requests.get(url, timeout=15)  # ✅ 用正確的分頁 URL
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")
                articles = soup.select("div.channel_newssection")

                if not articles:
                    print(f"No articles found on page {page}.")
                    return []

                for article in articles:
                    a_tag = article.select_one("a")
                    if a_tag:
                        href = a_tag['href']
                        full_url = base_url + href
                        page_urls.append(full_url)

                print(f"Found {len(page_urls)} articles on page {page}")
                return page_urls

            except Exception as e:
                print(f"Requests failed, fallback to Selenium for page {page}: {e}")

                # 若需要 JS 執行再回退到 Selenium
                driver = self.get_chrome_driver()
                try:
                    driver.get(url)  # ✅ 使用分頁 URL
                    time.sleep(2)  # wait for basic render

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    articles = soup.select("div.channel_newssection")

                    if not articles:
                        print(f"No articles found on page {page}.")
                        return []

                    
                    for article in articles:
                        a_tag = article.select_one("a")
                        if a_tag:
                            href = a_tag['href']
                            full_url = base_url + href
                            page_urls.append(full_url)

                    print(f"Found {len(page_urls)} articles on page {page}")
                    return page_urls
                finally:
                    driver.quit()

        all_urls = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(fetch_page_articles, page) for page in range(1, max_pages + 1)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    urls = future.result()
                    all_urls.extend(urls)
                except Exception as e:
                    print(f"Error fetching page: {e}")

        # 去重
        all_urls = list(dict.fromkeys(all_urls))
        return all_urls

    def parse_article(self, soup: BeautifulSoup):
        base_url = "https://news.pchome.com.tw"
        # title
        title=soup.find("h1",class_="article_title")
        if title:
            self.title=title.get_text(strip=True)
        

        print("self.title:", self.title)

        # content
        content_div=soup.find('div',class_="article_text")
        if content_div is None:
            content_div=soup.find('div',calss="article_text")
        print("content_div:",content_div)
        if content_div:
            content_p=content_div.find_all('p')
            paragraphs = []
            for p in content_p:
                paragraphs.append(p.get_text(strip=True).replace("更多新聞推薦",""))  # ✅ 取得段落純文字
            self.content = "\n".join(paragraphs)

        # ✅ 擷取作者
        func_source_li = soup.find("li", class_="func_source")
        if func_source_li:
            author_text = func_source_li.get_text(strip=True)
            if author_text:
                # Remove "記者：" from the beginning
                author_name = author_text.replace("記者：", "").strip()
                self.authors.append(author_name)

        # ✅ 發佈時間
        func_time_li = soup.find("li", class_="func_time")
        if func_time_li:
            time = func_time_li.find('time')
            if time:
                source=time.find('a')
                if source:
                    source.decompose()
                date_str = time.get_text(strip=True)
                if date_str:
                    date = date_str.replace("\u3000新聞來源 :", "").strip()
                    print(f"date:{date}")
                    self.published_at = standardTaipeiDateToTimestamp(date)

        # ✅ 圖片
        self.images = []
        article_text_div = soup.find('div', class_='article_text')
        if article_text_div:
            src=article_text_div['src']
            image_url=base_url+src
            if image_url:
                self.images.append(image_url)

        # ✅ 來源
        func_time_li = soup.find("li", class_="func_time")
        if func_time_li:
            origin_a=func_time_li.find("a")
            if origin_a:
                origin=origin_a.get_text(strip=True)
                if origin:
                    self.origin=origin