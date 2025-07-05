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
        return NewsResponse(title=article.title, content=article.content,published_at=article.published_at, authors=article.authors, images=article.images)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing article: {str(e)}")