import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import undetected_chromedriver 
# from translation import translate_text
from webScraper.simplifiedChineseToTraditionalChinese import simplifiedChineseToTraditionalChinese

# Constants
WAITING_TIME_FOR_JS_TO_FETCH_DATA=0


class News(ABC):
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
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract published date
        self.published_at=soup.find("div",class_="datePublished").get_text(strip=True) if soup.find("div",class_="datePublished") else "No date found"

        # Extract content
        content_div = soup.find("article")
        if not content_div:
            content_div = soup.find("article", class_="news-text")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

# HK News Media
class MingPaoNews(News):
    """Uses the default parser; override only if needed."""
    pass

class SingTaoDaily(News):
    pass

class SCMP(News):
    pass

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

class OrientalDailyNews(News):
    """Overrides parsing logic for a different HTML structure."""
    def _parse_article(self, soup):
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
    pass

class InitiumMedia(News):
    pass

class YahooNews(News):
    pass

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

class TheEpochTimes(News):
    def _parse_article(self, soup):
        # Extract title
        self.title = soup.find("h2").get_text()

        # Extract content
        content_div = soup.find("div",class_="post_content")

        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

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
        self.title = soup.find("h1").get_text()

        # Extract content
        content_div = soup.find("div",class_="elementor-element elementor-element-cd4b5e9 elementor-widget elementor-widget-theme-post-content")
        print("content_div:",content_div)
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

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

class HKGovernmentNews(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("h1", class_="tkp_con_title")
        self.title = title_tag.get_text(strip=True) if title_tag else "No title"

        # Extract content
        content_div = soup.find("div",class_="newsdetail-content")
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"


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
            driver.get(self.url)
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
        except Exception as e:
            print("❌ 錯誤：", e)

        driver.quit()

class TheStandard(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        paragraphs = soup.find_all("p")
        print("paragraphs:",paragraphs)
        if paragraphs:
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

class HKEJ(News):
    def _parse_article(self, soup):
        # Extract title
        title_tag = soup.find("meta", property="og:title")
        self.title = title_tag["content"].strip() if title_tag else "No title found"

        # Extract content
        content_div = soup.find("div",id="article-content")
        if not content_div:
            content_div = soup.find("article", class_="news-text")
        if content_div:
            paragraphs = content_div.find_all("p")
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            self.content = "No content found"

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

class TheWitness(News):
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

            self.title = soup.find("meta", property="og:title")
            self.subtitle = soup.find("meta", property="og:description")
            self.content = soup.find_all("p")

            print("📰 Title:", self.title["content"] if self.title else "無標題")
            print("📝 Subtitle:", self.subtitle["content"] if self.subtitle else "無副標題")
            print("self.content:",self.content)

            if self.content:
                self.content = "\n".join(p.get_text(strip=True) for p in  self.content)
                print("📄 Content Preview:\n",  self.content, "...")
            else:
                print("⚠️ 找不到文章內容")
        except Exception as e:
            print("❌ 錯誤：", e)

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
    pass

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
    pass

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