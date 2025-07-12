from typing import List, Type
from fastapi import HTTPException
from scrapers.news import News
from app.models.newsEntity import NewsEntity
from app.schemas.news import NewsResponse
import constant
from scrapers.scrape_news import scrape_news
from app.repositories import news_repository
from app.schemas.news import NewsFilter



async def scrape_and_store_news(parser_instance: Type[News], db):
    # Scrape
    articles:List[NewsEntity] = await scrape_news(parser_instance)
    print("articles:",articles)
    # Store
    return await news_repository.store_all_articles(articles,db)

async def get_filtered_news(filter:NewsFilter, db):
    return await news_repository.get_filtered_news(filter,db)
