import asyncio
from typing import List, Type
from fastapi import HTTPException
from app.llm.llama_8B_translation import translate_article
from scrapers.news import News
from app.models.newsEntity import NewsEntity
from app.schemas.news import NewsResponse
import constant
from scrapers.scrape_news import scrape_unique_news
from app.repositories import news_repository
from app.schemas.news import NewsFilter
from sqlalchemy.ext.asyncio import AsyncSession

async def filter_existing_articles(urls:List[str],db:AsyncSession):
    return await news_repository.filter_existing_articles(urls,db)


async def scrape_translate_and_store_news(parser_instance: Type[News], db:AsyncSession):
    # Scrape
    articles:List[NewsEntity] = await scrape_unique_news(parser_instance,db)
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    await asyncio.gather(*[translate_article(article) for article in articles])
    # Store
    return await news_repository.store_all_articles(articles,db)

async def scrape_and_store_all_taiwanese_news(_:any, db:AsyncSession):
    all_articles: List[News] = []

    for parser_class in constant.TAIWAN_MEDIA:
        print("parser_class:",parser_class)
        print(f"🔍 Scraping from: {parser_class.__name__}")
        new_articles = await scrape_translate_and_store_news(parser_class, db)
        all_articles.extend(new_articles)
        print(f"✅ {len(new_articles)} articles scraped from {parser_class.__name__}")

    print(f"\n🎉 Total articles scraped: {len(all_articles)}")
    return all_articles


async def get_filtered_news(filter:NewsFilter, db):
    news_entities=await news_repository.get_filtered_news(filter,db)
    # newsEntities into newsResponse
    news_responses = [NewsResponse.from_orm(entity) for entity in news_entities]
    return news_responses
    
