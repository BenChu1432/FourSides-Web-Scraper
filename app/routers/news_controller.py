import asyncio
from typing import List
import concurrent
from fastapi import APIRouter, HTTPException
from app.db.database import get_db
from scrapers.news import News
from app.schemas.news import NewsRequest, NewsResponse
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from app.service import error_service, news_service
from constant import NEWS_CLASSES
import constant
from app.schemas.news import NewsFilter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/parse-news", response_model=NewsResponse)
async def parse_news_article(news: NewsRequest, db: AsyncSession = Depends(get_db)):
    media_name = news.media
    url = news.url

    # Secure parser class lookup
    parser_class = NEWS_CLASSES.get(media_name)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Media class '{media_name}' not found")

    article:News = parser_class(url)
    parse_article_result=article.parse_article_with_errors()
    print("article:",article)
    if parse_article_result.errors:
        await error_service.log_error(db, parse_article_result.errors)
    return NewsResponse(url=article.url, media_name=article.media_name,title=article.title, content=article.content,published_at=article.published_at, authors=article.authors, images=article.images,origin=article.origin)


@router.post("/fetch-news/{media_name}", response_model=List[NewsResponse])
async def get_news(media_name: str, db: AsyncSession = Depends(get_db)):
    print("media_name:",media_name)
    parser_class = NEWS_CLASSES.get(media_name)
    if not parser_class:
        raise ValueError("Unknown media")
    
    articles = await news_service.scrape_and_store_news(parser_class, db)
    print("articles:",articles)
    return articles
    
@router.post("/get-news", response_model=List[NewsResponse])
async def get_news_with_filter(
    filter: NewsFilter,
    db: AsyncSession = Depends(get_db)
):
    try:
        return await news_service.get_filtered_news(filter,db)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    