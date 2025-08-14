# app/controllers/news_controller.py

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.dto.dto import NewsRequest, NewsResponse
from app.dto.dto import NewsFilter
from app.service import news_service, scrape_service
from constant import NEWS_CLASSES
from scrapers.news import News


def debug_chrome_files():
    import os
    return {
        "chromedriver_exists": os.path.exists("/opt/chromedriver"),
        "chromedriver_executable": os.access("/opt/chromedriver", os.X_OK),
        "chrome_exists": os.path.exists("/opt/headless-chromium"),
        "chrome_executable": os.access("/opt/headless-chromium", os.X_OK),
    }


async def parse_news_article(news: NewsRequest, db: AsyncSession) -> NewsResponse:
    parser_class = NEWS_CLASSES.get(news.media)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Media class '{news.media}' not found")

    article: News = parser_class(news.url)
    result = article.parse_article_with_errors()
    if result.errors:
        await scrape_service.log_scrape_error(db, result.errors)

    return NewsResponse(
        url=article.url,
        media_name=article.media_name,
        title=article.title,
        content=article.content,
        published_at=article.published_at,
        authors=article.authors,
        images=article.images,
        origin=article.origin,
    )


async def scrape_translate_and_store_news_for_one_news_outlet(media_name: str) -> List[NewsResponse]:
    parser_class = NEWS_CLASSES.get(media_name)

    try:
        await news_service.scrape_translate_and_store_news_for_one_news_outlet(parser_class)
        return []
    except Exception as e:
        print("Either scrape/translate/store goes wrong!:",e)

async def scrape_and_store_all_taiwanese_news() -> List[NewsResponse]:
    return await news_service.scrape_and_store_all_taiwanese_news()


async def get_news_with_filter(filter: NewsFilter, db: AsyncSession) -> List[NewsResponse]:
    try:
        return await news_service.get_filtered_news(filter, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
async def retry_scraping_existent_news_by_media(media_name:str):
    parser_class = NEWS_CLASSES.get(media_name)
    return await news_service.retry_scraping_existent_news_by_media(media_name,parser_class)

async def retry_urls_where_XXX_is_null_or_the_news_is_native(media_name:str,filter: Optional[str]):
    parser_class = NEWS_CLASSES.get(media_name)
    return await news_service.retry_urls_where_XXX_is_null_or_the_news_is_native(media_name,filter,parser_class)