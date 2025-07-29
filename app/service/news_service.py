import asyncio
from typing import List, Type
from fastapi import HTTPException
from app.db.database import AsyncSessionLocal
from app.llm.llama_8B_translation import translate_article
from scrapers.news import News
from app.modals.newsEntity import NewsEntity
from app.dto.dto import NewsResponse
import constant
from scrapers.scrape_news import scrape_specified_news, scrape_unique_news
from app.repositories import news_repository
from app.dto.dto import NewsFilter
from sqlalchemy.ext.asyncio import AsyncSession

async def filter_existing_articles(urls:List[str],db:AsyncSession):
    return await news_repository.filter_existing_articles(urls,db)


async def scrape_translate_and_store_news_for_one_news_outlet(parser_class: Type[News]):
    # Scrape
    try:
        articles:List[NewsEntity] = await scrape_unique_news(parser_class,AsyncSessionLocal)
    except Exception as e:
        print("error:",e)
        raise e
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    # await asyncio.gather(*[translate_article(article) for article in articles])
    # Store
    async with AsyncSessionLocal() as db:
        return await news_repository.store_all_articles(articles, db)
    
async def scrape_and_translate_news(parser_class: Type[News]):
    # Scrape
    articles:List[NewsEntity] = await scrape_unique_news(parser_class)
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    # await asyncio.gather(*[translate_article(article) for article in articles])
    # Store
    return articles

async def scrape_and_store_all_taiwanese_news():
    # Several concerns:
    # 1.lack of memory with so many articles
    # 2.DB disconnections
    # 3.Stale DB connections
    for parser_class in constant.TAIWAN_MEDIA:
        print("parser_class:",parser_class)
        print(f"🔍 Scraping from: {parser_class.__name__}")
        await scrape_translate_and_store_news_for_one_news_outlet(parser_class)


async def get_filtered_news(filter:NewsFilter, db):
    news_entities=await news_repository.get_filtered_news(filter,db)
    # newsEntities into newsResponse
    news_responses = [NewsResponse.model_validate(entity) for entity in news_entities]
    return news_responses


async def retry_parsing_by_media(news_media,parser_class):
    async with AsyncSessionLocal() as db:
        urls=await news_repository.get_news_urls_that_need_retrying(news_media,db)
        print("urls:",urls)
    # Scraping
    try:
        articles:List[NewsEntity] = await scrape_specified_news(parser_class,urls)
    except Exception as e:
        print("error:",e)
        raise e
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    await asyncio.gather(*[translate_article(article) for article in articles])
    # Update
    async with AsyncSessionLocal() as db:
        return await news_repository.update_all_articles(articles, db)

    
