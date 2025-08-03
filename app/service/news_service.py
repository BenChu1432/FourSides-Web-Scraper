import asyncio
from typing import List, Type
from fastapi import HTTPException
from app.aws_lambda.send_logs_to_db import send_log_to_lambda
from app.db.database import AsyncSessionLocal
from app.enums.enums import ErrorTypeEnum
from app.llm.llama_8B_translation import translate_article
from app.service import scrape_service
from scrapers.news import News
from app.modals.newsEntity import NewsEntity
from app.dto.dto import NewsResponse
import constant
from scrapers.scrape_news import scrape_specified_news, scrape_unique_news
from app.repositories import news_repository
from app.dto.dto import NewsFilter
from sqlalchemy.ext.asyncio import AsyncSession

from util.awsUtil import get_instance_id

async def filter_existing_articles(urls:List[str],db:AsyncSession):
    return await news_repository.filter_existing_articles(urls,db)


async def scrape_translate_and_store_news_for_one_news_outlet(parser_class: Type[News]):
    # Get machine ID
    try:
        machine_id = await get_instance_id()
        if not machine_id:
            machine_id = 'unknown machine'
    except Exception as e:
        print(f"Failed to get machine_id: {e}")
        machine_id = 'unknown machine'
    news_instance = parser_class()
    media_name=news_instance.media_name
    print("news_instance.media_name:",news_instance.media_name)
    # Log scrape job
    try:
        async with AsyncSessionLocal() as db:
            jobId=await scrape_service.log_scrape_job(db, media_name,machine_id)
    except Exception as e:
        print("❌ Cannot log a scrape job:",e)
        # Fallback to Lambda??????????????????????????????????????????????????????????????????????????????????????????????????????????????
    # Scrape
    try:
        articles:List[NewsEntity] = await scrape_unique_news(parser_class,jobId,AsyncSessionLocal)
    except Exception as e:
        print("error:",e)
        # Raise HTTPException to notify the client
        return []
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    # await asyncio.gather(*[translate_article(article) for article in articles])
    # Store
     # ******************************************DB Connection******************************************
    try:
        async with AsyncSessionLocal() as db:
            await news_repository.store_all_articles(articles, db)
    except Exception as e:
        print("❌ Failed to store articles:", e)
        urls=[article.url for article in articles]
        await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f"❌ Failed to store articles:, {e}",media_name=media_name,urls=[urls])
        return []  # or handle however makes sense for your use case
     # ******************************************DB Connection******************************************
    try:
        async with AsyncSessionLocal() as db:
            await scrape_service.log_scrape_job_end(db,jobId)
    except Exception as e:
        print("❌ Cannot log finished scrape job:", e)
        urls=[article.url for article in articles]
        await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f"❌ Failed to store articles:, {e}",media_name=media_name,urls=[urls])
        return []  # or handle however makes sense for your use case
    
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


async def retry_parsing_by_media(media_name,parser_class):
    async with AsyncSessionLocal() as db:
        urls=await news_repository.get_news_urls_that_need_retrying(media_name,db)
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

    
