from typing import Type
from fastapi import HTTPException
from app.models.newsEntity import NewsEntity
from scrapers.news import News
from app.schemas.news import NewsResponse
import constant
import concurrent

async def scrape_news(parser_class: type[News]):
    print("Hi!")
    scraper = parser_class()
    article_urls = scraper.get_article_urls()

    def fetch_article(url):
        try:
            article = parser_class(url)
            return NewsEntity(
                url=article.url,
                media_name=article.media_name,
                title=article.title,
                content=article.content,
                published_at=article.published_at,
                authors=article.authors,
                images=article.images,
                origin=article.origin
            )
        except Exception as e:
            print(f"❌ Failed to parse article {url}: {e}")
            return None
    
    try:
        parser_instance = parser_class()
        print("parser_instance:",parser_instance)
        article_urls = parser_instance.get_article_urls()
        max_workers=parser_instance.max_workers
        print("max_workers:",max_workers)
        print("article_urls:",article_urls)
        list_of_news=[]
        # (Recommended for blocking I/O like APIs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
            future_to_url = {executor.submit(fetch_article, url): url for url in article_urls}
            # As they complete, gather results
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    article:News = future.result()
                    print("article:", article)
                    list_of_news.append(article)
                except Exception as e:
                    print(f"Error fetching article from {future_to_url[future]}: {e}")
        return list_of_news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing article: {str(e)}")