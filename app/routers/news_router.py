from typing import List
import concurrent
from fastapi import APIRouter, HTTPException
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

@router.post("/retry-parsing-by-media/{media_name}", response_model=List[NewsResponse])
async def retry_parsing_by_media(media_name: str):
    return await news_controller.retry_parsing_by_media(media_name)