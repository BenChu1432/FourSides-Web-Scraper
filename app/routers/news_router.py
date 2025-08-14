from typing import List, Optional
import concurrent
from fastapi import APIRouter, HTTPException, Query
from app.controller import news_controller
from app.db.database import get_db
from scrapers.news import News
from app.dto.dto import NewsRequest, NewsResponse
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.dto.dto import NewsFilter


# For local development 
router = APIRouter()

@router.get("/debug-files")
def debug_chrome_files():
    return news_controller.debug_chrome_files()


@router.post("/parse-news", response_model=NewsResponse)
async def parse_news(news: NewsRequest, db: AsyncSession = Depends(get_db)):
    return await news_controller.parse_news_article(news, db)


@router.post("/scrape-news/{media_name}", response_model=List[NewsResponse])
async def fetch_news(media_name: str):
    return await news_controller.scrape_translate_and_store_news_for_one_news_outlet(media_name)


@router.post("/scrape-all-taiwanese-news", response_model=List[NewsResponse])
async def fetch_all_news():
    return await news_controller.scrape_and_store_all_taiwanese_news()


@router.post("/get-news", response_model=List[NewsResponse])
async def get_news_with_filter(filter: NewsFilter, db: AsyncSession = Depends(get_db)):
    return await news_controller.get_news_with_filter(filter, db)

@router.post("/retry-scraping-existent-news-by-media/{media_name}", response_model=List[str])
async def retry_scraping_existent_news_by_media(media_name: str):
    return await news_controller.retry_scraping_existent_news_by_media(media_name)

@router.post("/retry-news-urls-where-xxx-is-null-or-the-news-is-native/{media_name}", response_model=List[str])
async def retry_urls_where_XXX_is_null_or_the_news_is_native(media_name: str,filter: Optional[str] = Query(None)):
    return await news_controller.retry_urls_where_XXX_is_null_or_the_news_is_native(media_name,filter)