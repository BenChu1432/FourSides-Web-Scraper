import asyncio
from typing import List
import concurrent
from fastapi import APIRouter, HTTPException
from app.schemas.models import NewsRequest, NewsResponse, Preferences, Region, Topic
import logging

from constant import NEWS_CLASSES

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/parse-news", response_model=NewsResponse)
def parse_news_article(news: NewsRequest):
    media_name = news.media
    url = news.url

    # Secure parser class lookup
    parser_class = NEWS_CLASSES.get(media_name)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Media class '{media_name}' not found")

    try:
        article = parser_class(url)
        return NewsResponse(url=article.url,title=article.title, content=article.content,published_at=article.published_at, authors=article.authors, images=article.images,origin=article.origin)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing article: {str(e)}")
    
@router.get("/get-news/{media_name}", response_model=List[NewsResponse])
async def get_news(media_name: str):
    print("media_name:",media_name)
    parser_class = NEWS_CLASSES.get(media_name)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Media class '{media_name}' not found")
    print("parser_class:",parser_class)

    try:
        parser_instance = parser_class()
        article_urls = parser_instance.get_article_urls(max_pages=2)
        print("article_urls:",article_urls)
        list_of_news=[]
        def fetch_article(url):
            return parser_class(url)
        # (Recommended for blocking I/O like APIs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all tasks
            future_to_url = {executor.submit(fetch_article, url): url for url in article_urls}

            # As they complete, gather results
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    article = future.result()
                    print("article:", article)
                    list_of_news.append(article)
                except Exception as e:
                    print(f"Error fetching article from {future_to_url[future]}: {e}")
        return list_of_news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing article: {str(e)}")