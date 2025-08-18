# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import requests
# from bs4 import BeautifulSoup
# import time

# # ✅ 用 Selenium 抓文章網址
# def get_tfc_article_urls(max_pages=1):
#     options = Options()
#     options.add_argument("--headless")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--lang=zh-TW")

#     driver = webdriver.Chrome(options=options)
#     article_urls = []

#     # for page in range(1, max_pages + 1):
#     #     if page == 1:
#     #         url = "https://tfc-taiwan.org.tw/fact-check-reports-all/"
#     #     else:
#     #         url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"

#     #     print(f"🔗 開啟第 {page} 頁: {url}")
#     #     driver.get(url)



#     for page in range(1):
#         if page == 1:
#             url = "https://tfc-taiwan.org.tw/fact-check-reports-all/"
#         else:
#             url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"

#         print(f"🔗 開啟第 {page} 頁: {url}")
#         driver.get(url)
#         try:
#             WebDriverWait(driver, 10).until(
#                 EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
#             )

#             articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
#             print(f"✅ 找到 {len(articles)} 篇文章")

#             for article in articles:
#                 try:
#                     a_tag = article.find_element(By.TAG_NAME, "a")
#                     href = a_tag.get_attribute("href")
#                     if href and href not in article_urls:
#                         article_urls.append(href)
#                 except Exception as e:
#                     print("⚠️ 找 <a> 錯誤：", e)

#         except Exception as e:
#             print(f"❌ 頁面載入失敗: {e}")

#         time.sleep(1.2)

#     driver.quit()
#     print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
#     return article_urls

# # ✅ 用 BeautifulSoup 抓查核記者（作者）
# def get_author_from_article(url):
#     try:
#         res = requests.get(url)
#         res.encoding = "utf-8"
#         soup = BeautifulSoup(res.text, "html.parser")

#         for p in soup.find_all("p"):
#             strong = p.find("strong")
#             if strong and "查核記者" in strong.get_text():
#                 author_text = p.get_text().replace("查核記者：", "").strip()
#                 return author_text
#         return None
#     except Exception as e:
#         print(f"❌ 讀取文章失敗: {url}，錯誤：{e}")
#         return None

# # 🔄 串接流程：抓網址 → 一篇篇抓作者
# urls = get_tfc_article_urls(max_pages=3)

# def get_title_and_summary(url):
#     try:
#         res = requests.get(url)
#         res.encoding = "utf-8"
#         soup = BeautifulSoup(res.text, "html.parser")

#         # 直接抓所有 <strong> 標籤
#         strong_tags = soup.find_all("strong")

#         # 不使用任何文字條件判斷，直接取前兩個
#         title = strong_tags[0].get_text(strip=True) if len(strong_tags) > 0 else None
#         summary = strong_tags[1].get_text(strip=True) if len(strong_tags) > 1 else None

#         return title, summary

#     except Exception as e:
#         print(f"❌ 抓取失敗：{url}，錯誤：{e}")
#         return None, None

# def get_article_content(url):
#     try:
#         res = requests.get(url)
#         res.encoding = "utf-8"
#         soup = BeautifulSoup(res.text, "html.parser")

#         # 抓所有段落
#         all_paragraphs = soup.find_all("p")

#         # 過濾掉空的、非內文段落（可進一步加條件）
#         content_paragraphs = [
#             p.get_text(strip=True)
#             for p in all_paragraphs
#             if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20
#         ]

#         content = "\n".join(content_paragraphs)
#         return content if content else None

#     except Exception as e:
#         print(f"❌ 抓文章內容失敗：{url}，錯誤：{e}")
#         return None


# # def get_publish_time(soup):
# #     try:
# #         # 找出所有 <p> 標籤
# #         p_tags = soup.find_all("p")

# #         for p in p_tags:
# #             strong = p.find("strong")
# #             if strong and "發布" in strong.get_text():
# #                 # 回傳 strong 後面的純文字（也就是日期）
# # #                 return p.get_text(strip=True).replace(strong.get_text(strip=True), "").strip()

# # #         return None
# # #     except Exception as e:
# # #         print(f"❌ 發布時間擷取失敗：{e}")
# # #         return None

# # print("\n📖 每篇文章摘要：")
# # for url in urls:
# #     res = requests.get(url)
# #     res.encoding = "utf-8"
# #     soup = BeautifulSoup(res.text, "html.parser")

# #     title, summary = get_title_and_summary(soup)
# #     article = get_article_content(soup)
# #     publish_date = get_publish_time(soup)
# #     author = get_author_from_article(soup)

# #     print(f"\n📰 {url}")
# #     print(f"📌 標題：{title if title else '（未找到）'}")
# #     print(f"📌 結論：{summary if summary else '（未找到）'}")
# #     print(f"📅 發布日期：{publish_date if publish_date else '（未找到）'}")
# #     print(f"📝 查核記者：{author if author else '（未找到）'}")

# #     if article:
# #         print(f"📄 正文內容：\n{article}")
# #     else:
# #         print("📄 正文內容：（未找到）")

# # # res = requests.get(urls)
# # # res.encoding = "utf-8"
# # # soup = BeautifulSoup(res.text, "html.parser")

# # # author = get_author_from_article(soup)
# # # title, summary = get_title_and_summary(soup)
# # # article = get_article_content(soup)
# # # publish_date = get_publish_time(soup)

# # # print(f"\n📰 {urls}")
# # # print(f"📌 標題：{title}")
# # # print(f"📌 結論：{summary}")
# # # print(f"📅 發布日期：{publish_date if publish_date else '（未找到）'}")
# # # print(f"📝 查核記者：{author}")
# # # print(f"📄 正文內容：\n{article if article else '（未找到）'}")


# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# import requests
# import time
# import re

# # ✅ Selenium 抓 TFC 查核文章網址
# def get_tfc_article_urls(max_pages=1):
#     options = Options()
#     options.add_argument("--headless")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--lang=zh-TW")
    
#     driver = webdriver.Chrome(options=options)
#     article_urls = []

#     for page in range(1, max_pages + 1):
#         url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"
#         print(f"🔗 開啟第 {page} 頁: {url}")
#         driver.get(url)

#         try:
#             WebDriverWait(driver, 10).until(
#                 EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
#             )
#             articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
#             print(f"✅ 找到 {len(articles)} 篇文章")

#             for article in articles:
#                 try:
#                     a_tag = article.find_element(By.TAG_NAME, "a")
#                     href = a_tag.get_attribute("href")
#                     if href and href not in article_urls:
#                         article_urls.append(href)
#                 except Exception as e:
#                     print("⚠️ 找 <a> 錯誤：", e)

#         except Exception as e:
#             print(f"❌ 頁面載入失敗: {e}")

#         time.sleep(1.2)

#     driver.quit()
#     print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
#     return article_urls

# # ✅ 擷取標題與結論
# def get_title_and_summary(soup):
#     try:
#         title_tag = soup.find("h1")
#         title = title_tag.get_text(strip=True) if title_tag else None

#         conclusion = None
#         for tag in soup.find_all(["p", "div", "span"]):
#             text = tag.get_text(strip=True)
#             if text in ["錯誤", "部分錯誤", "事實釐清", "正確"]:
#                 conclusion = text
#                 break

#         return title, conclusion
#     except Exception as e:
#         print(f"❌ 標題與結論擷取錯誤：{e}")
#         return None, None

# # ✅ 擷取發佈日期
# def get_publish_time(soup):
#     try:
#         for p in soup.find_all("p"):
#             strong = p.find("strong")
#             if strong and "發佈" in strong.text:
#                 contents = p.contents
#                 for part in contents:
#                     if isinstance(part, str) and part.strip():
#                         return part.strip()
#         return None
#     except Exception as e:
#         print(f"❌ 發布時間擷取失敗：{e}")
#         return None

# # ✅ 擷取查核記者
# def get_author_from_article(soup):
#     try:
#         text = soup.get_text()
#         match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text)
#         if match:
#             return match.group(1)
#         return None
#     except Exception as e:
#         print(f"❌ 記者擷取失敗：{e}")
#         return None

# # ✅ 擷取文章內容
# def get_article_content(soup):
#     try:
#         content = ""
#         article_div = soup.find("div", class_=lambda c: c and ("entry-content" in c or "wp-block" in c))
#         if article_div:
#             paragraphs = article_div.find_all(["p", "li"])
#             content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
#         return content if content else None
#     except Exception as e:
#         print(f"❌ 正文內容擷取錯誤：{e}")
#         return None

# # ✅ 主程式：印出每篇文章資訊
# def main():
#     urls = get_tfc_article_urls(max_pages=2)

#     print("\n📖 每篇文章摘要：")
#     for url in urls:
#         try:
#             res = requests.get(url)
#             res.encoding = "utf-8"
#             soup = BeautifulSoup(res.text, "html.parser")

#             title, summary = get_title_and_summary(soup)
#             article = get_article_content(soup)
#             publish_date = get_publish_time(soup)
#             author = get_author_from_article(soup)

#             print(f"\n📰 {url}")
#             print(f"📌 標題：{title if title else '（未找到）'}")
#             print(f"📌 結論：{summary if summary else '（未找到）'}")
#             print(f"📅 發布日期：{publish_date if publish_date else '（未找到）'}")
#             print(f"📝 查核記者：{author if author else '（未找到）'}")

#             if article:
#                 print(f"📄 正文內容：\n{article[:500]}...")  # 可調整顯示長度
#             else:
#                 print("📄 正文內容：（未找到）")

#         except Exception as e:
#             print(f"❌ 讀取失敗：{url}，錯誤：{e}")

# if __name__ == "__main__":
#     main()



# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# import requests
# import time
# import re

# class TFCNews:
#     def __init__(self, url=None):
#         self.url = url
#         self.media_name = "TFC"
#         self.max_pages = 2
#         self.title = None
#         self.summary = None
#         self.published_at = None
#         self.authors = []
#         self.content = None
#         self.images = []
#         self.origin = "台灣事實查核中心"

#     def get_chrome_driver(self):
#         options = Options()
#         options.add_argument("--headless")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--lang=zh-TW")
#         return webdriver.Chrome(options=options)

#     def _get_article_urls(self):
#         driver = self.get_chrome_driver()
#         article_urls = []

#         for page in range(1, self.max_pages + 1):
#             url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"
#             print(f"🔗 開啟第 {page} 頁: {url}")
#             driver.get(url)

#             try:
#                 WebDriverWait(driver, 10).until(
#                     EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
#                 )
#                 articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
#                 print(f"✅ 找到 {len(articles)} 篇文章")

#                 for article in articles:
#                     try:
#                         a_tag = article.find_element(By.TAG_NAME, "a")
#                         href = a_tag.get_attribute("href")
#                         if href and href not in article_urls:
#                             article_urls.append(href)
#                     except Exception as e:
#                         print("⚠️ 找 <a> 錯誤：", e)

#             except Exception as e:
#                 print(f"❌ 頁面載入失敗: {e}")

#             time.sleep(1.2)

#         driver.quit()
#         print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
#         return article_urls

#     def parse_article(self, soup):
#         # 標題
#         title_tag = soup.find("h1")
#         self.title = title_tag.get_text(strip=True) if title_tag else "Missing Title"

#         # 結論（summary）
#         self.summary = None
#         for tag in soup.find_all(["p", "div", "span"]):
#             text = tag.get_text(strip=True)
#             if text in ["錯誤", "部分錯誤", "事實釐清", "正確"]:
#                 self.summary = text
#                 break
#         if not self.summary:
#             self.summary = "Missing Summary"

#         # 發布日期
#         self.published_at = None
#         for p in soup.find_all("p"):
#             strong = p.find("strong")
#             if strong and "發佈" in strong.text:
#                 contents = p.contents
#                 for part in contents:
#                     if isinstance(part, str) and part.strip():
#                         self.published_at = part.strip()
#                         break
#             if self.published_at:
#                 break
#         if not self.published_at:
#             self.published_at = "Missing Date"

#         # 查核記者
#         self.authors = []
#         text = soup.get_text()
#         match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text)
#         if match:
#             self.authors.append(match.group(1))
#         else:
#             self.authors.append("Missing Author")

#         # 正文內容
#         content_div = soup.find("div", class_=lambda c: c and ("entry-content" in c or "wp-block" in c))
#         if content_div:
#             paragraphs = content_div.find_all(["p", "li"])
#             self.content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
#         else:
#             self.content = "Missing Content"

#         # 圖片（可擴充）
#         self.images = []
#         for img in soup.find_all("img"):
#             image_url = None

#             if img.has_attr("src"):
#                 image_url = img["src"]
#             elif img.has_attr("srcset"):
#                 # 取 srcset 中解析度最大的那個
#                 srcset = img["srcset"]
#                 candidates = [s.strip().split(" ")[0] for s in srcset.split(",")]
#                 if candidates:
#                     image_url = candidates[0]

#             if image_url:
#                 # 若是相對路徑，補上來源網址
#                 if self.url and image_url.startswith("/"):
#                     image_url = urljoin(self.url, image_url)
#                 self.images.append(image_url)

#     def run(self):
#         urls = self._get_article_urls()

#         print("\n📖 每篇文章摘要：")
#         for url in urls:
#             try:
#                 res = requests.get(url)
#                 res.encoding = "utf-8"
#                 soup = BeautifulSoup(res.text, "html.parser")

#                 self.parse_article(soup)

#                 print(f"\n📰 {url}")
#                 print(f"📌 標題：{self.title}")
#                 print(f"📌 結論：{self.summary}")
#                 print(f"📅 發布日期：{self.published_at}")
#                 print(f"📝 查核記者：{', '.join(self.authors)}")
#                 print(f"🖼️ 圖片數量：{len(self.images)}")
#                 print(f"📄 正文內容：\n{self.content[:500]}...")

#             except Exception as e:
#                 print(f"❌ 讀取失敗：{url}，錯誤：{e}")


# import time
# import re
# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# from urllib.parse import urljoin
# from selenium.webdriver.chrome.options import Options
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options


# class TFCNews:
#     def __init__(self, url=None):
#         self.url = url
#         self.media_name = "TFC"
#         self.max_pages = 2
#         self.title = None
#         self.summary = None
#         self.published_at = None
#         self.authors = []
#         self.content = None
#         self.images = []
#         self.origin = "台灣事實查核中心"

#     def get_chrome_driver(self):
#         options = Options()
#         options.add_argument("--headless")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--lang=zh-TW")
#         return webdriver.Chrome(options=options)

#     def _get_article_urls(self):
#         driver = self.get_chrome_driver()
#         article_urls = []

#         for page in range(1, self.max_pages + 1):
#             url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"
#             print(f"🔗 開啟第 {page} 頁: {url}")
#             driver.get(url)

#             try:
#                 WebDriverWait(driver, 10).until(
#                     EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
#                 )
#                 articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
#                 print(f"✅ 找到 {len(articles)} 篇文章")

#                 for article in articles:
#                     try:
#                         a_tag = article.find_element(By.TAG_NAME, "a")
#                         href = a_tag.get_attribute("href")
#                         if href and href not in article_urls:
#                             article_urls.append(href)
#                     except Exception as e:
#                         print("⚠️ 找 <a> 錯誤：", e)

#             except Exception as e:
#                 print(f"❌ 頁面載入失敗: {e}")

#             time.sleep(1.2)

#         driver.quit()
#         print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
#         return article_urls

#     def parse_article(self, soup):
#         # 標題
#         title_tag = soup.find("h1")
#         self.title = title_tag.get_text(strip=True) if title_tag else "Missing Title"

#         # 結論（summary）
#         self.summary = None
#         for tag in soup.find_all(["p", "div", "span"]):
#             text = tag.get_text(strip=True)
#             if text in ["錯誤", "部分錯誤", "事實釐清", "正確"]:
#                 self.summary = text
#                 break
#         if not self.summary:
#             self.summary = "Missing Summary"

#         # 發布日期
#         self.published_at = None
#         for p in soup.find_all("p"):
#             strong = p.find("strong")
#             if strong and "發佈" in strong.text:
#                 contents = p.contents
#                 for part in contents:
#                     if isinstance(part, str) and part.strip():
#                         self.published_at = part.strip()
#                         break
#             if self.published_at:
#                 break
#         if not self.published_at:
#             self.published_at = "Missing Date"

#         # 查核記者
#         self.authors = []
#         text = soup.get_text()
#         match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text)
#         if match:
#             self.authors.append(match.group(1))
#         else:
#             self.authors.append("Missing Author")

#         # 正文內容
#         content_div = soup.find("div", class_=lambda c: c and ("entry-content" in c or "wp-block" in c))
#         if content_div:
#             paragraphs = content_div.find_all(["p", "li"])
#             self.content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
#         else:
#             self.content = "Missing Content"


#         # 圖片擷取（強化版）
#         # ✅ 圖片擷取（強化版）
#         self.images = []
#         images = []

#         for img in soup.find_all("img"):
#             image_url = img.get("src")
            
#             if not image_url and img.get("srcset"):
#                 # 從 srcset 選最大解析度
#                 candidates = [s.strip().split(" ")[0] for s in img["srcset"].split(",")]
#                 if candidates:
#                     image_url = candidates[-1]

#             if image_url:
#                 full_url = urljoin(url, image_url)
#                 images.append(full_url)

#         def run(self):
#             urls = self._get_article_urls()
#             driver = self.get_chrome_driver()

#         print("\n📖 每篇文章摘要：")
#         for url in urls:
#             try:
#                 driver.get(url)
#                 WebDriverWait(driver, 10).until(
#                     EC.presence_of_element_located((By.TAG_NAME, "article"))
#                 )
#                 soup = BeautifulSoup(driver.page_source, "html.parser")
#                 self.url = url  # 要記得設 self.url 才能做 urljoin

#                 self.parse_article(soup)

#                 print(f"\n📰 {url}")
#                 print(f"📌 標題：{self.title}")
#                 print(f"📌 結論：{self.summary}")
#                 print(f"📅 發布日期：{self.published_at}")
#                 print(f"📝 查核記者：{', '.join(self.authors)}")
#                 print(f"🖼️ 圖片數量：{len(self.images)}")
#                 for i, img_url in enumerate(self.images[:3]):
#                     print(f"   📷 圖片{i+1}: {img_url}")
#                 print(f"📄 正文內容：\n{self.content[:300]}...")

#             except Exception as e:
#                 print(f"❌ 讀取失敗：{url}，錯誤：{e}")

#         driver.quit()


#     if __name__ == "__main__":
#         checker = TFCNews()
#         checker.run()



# import time
# import re
# from urllib.parse import urljoin
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# class TFCNews:
#     def __init__(self, url=None):
#         self.url = url
#         self.media_name = "TFC"
#         self.max_pages = 2
#         self.title = None
#         self.summary = None
#         self.published_at = None
#         self.authors = []
#         self.content = None
#         self.images = []
#         self.origin = "台灣事實查核中心"

#     def get_chrome_driver(self):
#         options = Options()
#         options.add_argument("--headless")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--lang=zh-TW")
#         return webdriver.Chrome(options=options)

#     def _get_article_urls(self):
#         driver = self.get_chrome_driver()
#         article_urls = []

#         for page in range(1, self.max_pages + 1):
#             url = f"https://tfc-taiwan.org.tw/fact-check-reports-all/?pg={page}"
#             print(f"🔗 開啟第 {page} 頁: {url}")
#             driver.get(url)

#             try:
#                 WebDriverWait(driver, 10).until(
#                     EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.kb-query-item"))
#                 )
#                 articles = driver.find_elements(By.CSS_SELECTOR, "li.kb-query-item")
#                 print(f"✅ 找到 {len(articles)} 篇文章")

#                 for article in articles:
#                     try:
#                         a_tag = article.find_element(By.TAG_NAME, "a")
#                         href = a_tag.get_attribute("href")
#                         if href and href not in article_urls:
#                             article_urls.append(href)
#                     except Exception as e:
#                         print("⚠️ 找 <a> 錯誤：", e)

#             except Exception as e:
#                 print(f"❌ 頁面載入失敗: {e}")

#             time.sleep(1.2)

#         driver.quit()
#         print(f"\n📦 共蒐集 {len(article_urls)} 筆文章網址")
#         return article_urls

#     def parse_article(self, soup):
#         # 標題
#         title_tag = soup.find("h1")
#         self.title = title_tag.get_text(strip=True) if title_tag else "Missing Title"

#         # 結論（summary）
#         self.summary = None
#         for tag in soup.find_all(["p", "div", "span"]):
#             text = tag.get_text(strip=True)
#             if text in ["錯誤", "部分錯誤", "事實釐清", "正確"]:
#                 self.summary = text
#                 break
#         if not self.summary:
#             self.summary = "Missing Summary"

#         # 發布日期
#         self.published_at = None
#         for p in soup.find_all("p"):
#             strong = p.find("strong")
#             if strong and "發佈" in strong.text:
#                 contents = p.contents
#                 for part in contents:
#                     if isinstance(part, str) and part.strip():
#                         self.published_at = part.strip()
#                         break
#             if self.published_at:
#                 break
#         if not self.published_at:
#             self.published_at = "Missing Date"

#         # 查核記者
#         self.authors = []
#         text = soup.get_text()
#         match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text)
#         if match:
#             self.authors.append(match.group(1))
#         else:
#             self.authors.append("Missing Author")

#         # 正文內容
#         content_div = soup.find("div", class_=lambda c: c and ("entry-content" in c or "wp-block" in c))
#         if content_div:
#             paragraphs = content_div.find_all(["p", "li"])
#             self.content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
#         else:
#             self.content = "Missing Content"

#         # 圖片擷取
#         self.images = []
#         for img in soup.find_all("img"):
#             image_url = img.get("src")
#             if not image_url and img.get("srcset"):
#                 candidates = [s.strip().split(" ")[0] for s in img["srcset"].split(",")]
#                 if candidates:
#                     image_url = candidates[-1]
#             if image_url:
#                 full_url = urljoin(self.url, image_url)
#                 self.images.append(full_url)

#     def run(self):
#         urls = self._get_article_urls()
#         driver = self.get_chrome_driver()

#         print("\n📖 每篇文章摘要：")
#         for url in urls:
#             try:
#                 driver.get(url)
#                 WebDriverWait(driver, 10).until(
#                     EC.presence_of_element_located((By.TAG_NAME, "article"))
#                 )
#                 soup = BeautifulSoup(driver.page_source, "html.parser")
#                 self.url = url  # 記得設定 self.url 給圖片用

#                 self.parse_article(soup)

#                 print(f"\n📰 {url}")
#                 print(f"📌 標題：{self.title}")
#                 print(f"📌 結論：{self.summary}")
#                 print(f"📅 發布日期：{self.published_at}")
#                 print(f"📝 查核記者：{', '.join(self.authors)}")
#                 print(f"🖼️ 圖片數量：{len(self.images)}")
#                 for i, img_url in enumerate(self.images[:3]):
#                     print(f"   📷 圖片{i+1}: {img_url}")
#                 print(f"📄 正文內容：\n{self.content[:300]}...")

#             except Exception as e:
#                 print(f"❌ 讀取失敗：{url}，錯誤：{e}")

#         driver.quit()

# # ✅ 主程式執行
# if __name__ == "__main__":
#     checker = TFCNews()
#     checker.run()


# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin

# import requests




# # TFC article URL
# url = "https://tfc-taiwan.org.tw/fact-check-reports/fake-one-page-ad-dr-chiang-kun-chun-insomnia-medicine/"

# # Get HTML
# res = requests.get(url)
# soup = BeautifulSoup(res.text, "html.parser")

# # Find all .jpg images
# jpg_images = []
# for img in soup.find_all("img"):
#     src = img.get("src")
#     if src and src.endswith(".jpg"):
#         full_url = urljoin(url, src)
#         jpg_images.append(full_url)

# # Print result
# print(f"🖼️ Found {len(jpg_images)} JPG image(s):")
# for i, img_url in enumerate(jpg_images, 1):
#     print(f"📷 Image {i}: {img_url}")
# # ✅ 文章網址
# url = "https://tfc-taiwan.org.tw/fact-check-reports/fake-one-page-ad-dr-chiang-kun-chun-insomnia-medicine/"

# # ✅ 建立 Headless Chrome
# options = Options()
# #options.add_argument("--headless")
# options.add_argument("--disable-gpu")
# options.add_argument("--lang=zh-TW")
# driver = webdriver.Chrome(options=options)

# # ✅ 開啟網頁並等待文章載入
# driver.get(url)
# WebDriverWait(driver, 20).until(
#     EC.presence_of_element_located((By.CSS_SELECTOR, "div.entry-content"))
# )

# # ✅ 使用 BeautifulSoup 解析渲染後的 HTML
# soup = BeautifulSoup(driver.page_source, "html.parser")
# driver.quit()

# # ✅ 擷取圖片
# image_urls = []
# for img in soup.find_all("img"):
#     image_url = img.get("src")

#     # 若 src 為空，試著從 srcset 抓最大解析度
#     if not image_url and img.get("srcset"):
#         candidates = [s.strip().split(" ")[0] for s in img["srcset"].split(",")]
#         if candidates:
#             image_url = candidates[-1]

#     if image_url:
#         full_url = urljoin(url, image_url)
#         image_urls.append(full_url)

# # ✅ 顯示圖片結果
# print(driver.page_source[:500])  # 印出前 500 字元的 HTML，看看是不是空白頁
# print(f"🖼️ 找到 {len(image_urls)} 張圖片：")
# for i, img_url in enumerate(image_urls, 1):
#     print(f"📷 圖片{i}: {img_url}")


import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TFCNews:
    def __init__(self, url=None):
        self.url = url
        self.media_name = "TFC"
        self.max_pages = 2
        self.title = None
        self.summary = None
        self.published_at = None
        self.authors = []
        self.content = None
        self.images = []
        self.origin = "台灣事實查核中心"

    def get_chrome_driver(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=zh-TW")
        return webdriver.Chrome(options=options)

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
        # 標題（先找 <h1>，找不到再 fallback 到 <strong>）
        title_tag = soup.find("h1")
        if title_tag and title_tag.get_text(strip=True):
            self.title = title_tag.get_text(strip=True)
        else:
            # fallback: 找第一個 <strong> 標題樣式
            strong_tags = soup.find_all("strong")
            for tag in strong_tags:
                text = tag.get_text(strip=True)
                if text and len(text) > 10:
                    self.title = text
                    break
            else:
                self.title = "Missing Title"

        # 結論（summary）
        self.summary = None
        for tag in soup.find_all(["p", "div", "span"]):
            text = tag.get_text(strip=True)
            if text in ["錯誤", "部分錯誤", "事實釐清", "正確"]:
                self.summary = text
                break
        if not self.summary:
            self.summary = "Missing Summary"

        # 發布日期
        self.published_at = None
        for p in soup.find_all("p"):
            strong = p.find("strong")
            if strong and "發佈" in strong.text:
                contents = p.contents
                for part in contents:
                    if isinstance(part, str) and part.strip():
                        self.published_at = part.strip()
                        break
            if self.published_at:
                break
        if not self.published_at:
            self.published_at = "Missing Date"

        # 查核記者
        self.authors = []
        text = soup.get_text()
        match = re.search(r"查核記者[:：]?\s*([^\s，、\n]+)", text)
        if match:
            self.authors.append(match.group(1))
        else:
            self.authors.append("Missing Author")

        # 正文內容
        content_div = soup.find("div", class_=lambda c: c and ("entry-content" in c or "wp-block" in c))
        if content_div:
            paragraphs = content_div.find_all(["p", "li"])
            self.content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        else:
            self.content = "Missing Content"

        # 圖片擷取（.jpg）
        self.images = []
        for img in soup.find_all("img"):
            image_url = img.get("src")
            if not image_url and img.get("srcset"):
                candidates = [s.strip().split(" ")[0] for s in img["srcset"].split(",")]
                if candidates:
                    image_url = candidates[-1]
            if image_url and ".jpg" in image_url:
                full_url = urljoin(self.url, image_url)
                self.images.append(full_url)

    def run(self):
        urls = self._get_article_urls()
        driver = self.get_chrome_driver()

        print("\n📖 每篇文章摘要：")
        for url in urls:
            try:
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
                soup = BeautifulSoup(driver.page_source, "html.parser")
                self.url = url  # 給圖片用

                self.parse_article(soup)

                # 合併圖片欄位
                images_combined = " | ".join(self.images) if self.images else "No Images"

                print(f"\n📰 {url}")
                print(f"📌 標題：{self.title}")
                print(f"📌 結論：{self.summary}")
                print(f"📅 發布日期：{self.published_at}")
                print(f"📝 查核記者：{', '.join(self.authors)}")
                print(f"🖼️ 圖片欄位：{images_combined}")
                print(f"📄 正文內容：\n{self.content[:300]}...")

            except Exception as e:
                print(f"❌ 讀取失敗：{url}，錯誤：{e}")

        driver.quit()


# ✅ 主程式執行
if __name__ == "__main__":
    checker = TFCNews()
    checker.run()