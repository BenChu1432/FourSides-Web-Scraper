import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.factchecklab.org"


def get_all_article_urls():
    """Scrape all article URLs from homepage"""
    homepage = BASE_URL
    res = requests.get(homepage)
    soup = BeautifulSoup(res.text, "html.parser")

    article_urls = []

    for a_tag in soup.select("a.post-card-image-link"):
        href = a_tag.get("href")
        if href:
            full_url = urljoin(BASE_URL, href)
            article_urls.append(full_url)

    print(f"✅ Found {len(article_urls)} article URLs")
    return article_urls


def scrape_factchecklab_article(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    # --- Title ---
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else "Missing Title"

    # --- Publish Time ---
    time_tag = soup.find("time", class_="byline-meta-date")
    published_time = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else "Missing Date"

    # --- First Image ---
    first_img = None
    first_figure = soup.find("figure")
    if first_figure:
        img_tag = first_figure.find("img")
        if img_tag and img_tag.has_attr("src"):
            first_img = urljoin(url, img_tag["src"])
        else:
            first_img = "No image found"

    # --- Article Content ---
    content_div = soup.find("article")
    content = ""
    if content_div:
        paragraphs = content_div.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return {
        "url": url,
        "title": title,
        "published_at": published_time,
        "image": first_img,
        "content": content
    }


# ✅ Main Runner
if __name__ == "__main__":
    urls = get_all_article_urls()

    for i, url in enumerate(urls, 1):
        print(f"\n🔎 Scraping article {i}/{len(urls)}: {url}")
        try:
            data = scrape_factchecklab_article(url)
            print("📰 Title:", data["title"])
            print("📅 Published At:", data["published_at"])
            print("🖼️ First Image:", data["image"])
            print("📄 Content Preview:", data["content"][:200], "...\n")
        except Exception as e:
            print(f"❌ Failed to scrape {url} → {e}")