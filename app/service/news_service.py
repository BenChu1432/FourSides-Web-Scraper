import asyncio
from typing import List, Type
from fastapi import HTTPException
from app.aws_lambda.send_logs_to_db import send_log_to_lambda
from app.db.database import AsyncSessionLocal
from app.enums.enums import ErrorTypeEnum

from app.llm.meta_llama_question_generation import generate_question_for_article
from app.llm.llama_8B_translation import translate_article
from app.service import scrape_service
from app.service.classify_service import classify_article
from scrapers.news import News
from app.modals.newsEntity import NewsEntity
from app.dto.dto import NewsResponse
import constant
from scrapers.scrape_news import scrape_news_urls, scrape_specified_news, scrape_unique_news
from app.repositories import news_repository
from app.dto.dto import NewsFilter
from sqlalchemy.ext.asyncio import AsyncSession

from util.awsUtil import get_instance_id
from util.questionUtil import generate_misleading_technique_question

async def filter_existing_articles(urls:List[str],db:AsyncSession):
    return await news_repository.filter_existing_articles(urls,db)


async def scrape_generate_question_and_classify_and_store_news_for_one_news_outlet(parser_class: Type[News]):
    # Get machine ID
    try:
        machine_id = await get_instance_id()
        print("machine_id:",machine_id)
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
        print(f"✅ Limited to {len(articles)} URLs")
    except Exception as e:
        print("error:",e)
        # Raise HTTPException to notify the client
        return []
    print(f"✅ {len(articles)} articles collected.")
    if news_instance.media_name!="FactcheckLab" and news_instance.media_name!="TFCNews" and news_instance.media_name!="MyGoPenNews":
        for i, article in enumerate(articles):
            print(f"[{i}] URL: {getattr(article, 'url', 'no-url')}")

        # Generate one question for each article
        print("🧠 Generating true-false-not-given questions...")
        question_results = await asyncio.gather(
            *[generate_question_for_article(article) for article in articles],
            return_exceptions=True
        )

        for i, result in enumerate(question_results):
            if isinstance(result, Exception):
                print(f"❌ Question generation failed for article[{i}]: {result}")
                articles[i].true_false_not_given_questions_data = []
            else:
                articles[i].true_false_not_given_questions_data = result
        print("✅ Finished generating questions...")

    # Tagging
    if news_instance.media_name!="FactcheckLab" and news_instance.media_name!="TFCNews" and news_instance.media_name!="MyGoPenNews":
        print("🧠 Starting classification...")
        results = await asyncio.gather(*[classify_article(a) for a in articles], return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                print(f"❌ Classification crashed for article[{i}]: {r!r}")
                await send_log_to_lambda(jobId, failure_type=ErrorTypeEnum.LLM_ERROR,
                                        detail=f"classify crashed[{i}]: {r!r}",
                                        media_name=str(media_name),
                                        urls=[articles[i].url])
            elif not (isinstance(r, dict) and r.get("ok", False)):
                err = (r or {}).get("error") if isinstance(r, dict) else "unknown"
                print(f"❌ Classification failed for article[{i}]: {err}")
                await send_log_to_lambda(jobId, failure_type=ErrorTypeEnum.LLM_ERROR,
                                        detail=f"classify failed[{i}]: {err}",
                                        media_name=str(media_name),
                                        urls=[articles[i].url])
        print("✅ Classification complete.")
        # --- NEW CODE: Generate Misleading Technique Questions ---
        print("🧠 Generating misleading technique questions...")
        for article in articles:
            # ✅ 防止 None 出現
            if not hasattr(article, 'misleading_techniques_questions_data') or article.misleading_techniques_questions_data is None:
                article.misleading_techniques_questions_data = []

            try:
                misleading_question_data = generate_misleading_technique_question(article)
                print("misleading_question_data:", misleading_question_data)

                if isinstance(misleading_question_data, list):
                    article.misleading_techniques_questions_data.extend(misleading_question_data)
                else:
                    print("⚠️ misleading_question_data is not a list:", type(misleading_question_data))

                print("article.misleading_techniques_questions_data:", article.misleading_techniques_questions_data)
            except Exception as e:
                print(f"❌ Failed to generate misleading technique question for article: {e}")
                article.misleading_techniques_questions_data = []
        print("✅ Finished generating misleading technique questions...")
    # Store
     # ******************************************DB Connection******************************************
    print("🥳 Starting to store...")
    try:
        async with AsyncSessionLocal() as db:
            articles=await news_repository.store_all_articles(articles, db)
        print("🥳 Finished storing...")
    except Exception as e:
        print("❌ Failed to store articles:", e)
        urls=[article.url for article in articles]
        await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f"❌ Failed to store articles:, {e}",media_name=media_name,urls=[urls])
        return []  # or handle however makes sense for your use case
     # ******************************************DB Connection******************************************
    try:
        async with AsyncSessionLocal() as db:
            await scrape_service.log_scrape_job_end(db,jobId)
            return articles
    except Exception as e:
        print("❌ Cannot log finished scrape job:", e)
        urls=[article.url for article in articles]
        await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f"❌ Failed to log the finished scrape job:, {e}",media_name=media_name,urls=[urls])
        return []  # or handle however makes sense for your use case
    return []
    
async def scrape_and_translate_news(parser_class: Type[News]):
    # Scrape
    articles:List[NewsEntity] = await scrape_unique_news(parser_class)
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    # await asyncio.gather(*[translate_article(article) for article in articles])
    # Store
    return articles

async def parse_news_urls(parser_class: Type[News]):
    news_instance = parser_class()
    print("news_instance.media_name:",news_instance.media_name)
    # Scrape
    try:
        article_urls: List[str] = await scrape_news_urls(parser_class)
        print(f"✅ Limited to {len(article_urls)} URLs")
        return article_urls
    except Exception as e:
        print("error:",e)
        # Raise HTTPException to notify the client
        return []

async def retry_scraping_existent_news_by_media(media_name,parser_class):
    async with AsyncSessionLocal() as db:
        urls=await news_repository.get_scraping_existent_news_urls_by_media(media_name,db)
        print("urls:",urls)
    # Scraping
    flattened_urls=[]
    for u in urls:
        if isinstance(u, list) and u:
            flattened_urls.append(u[0])
        elif isinstance(u, str):
            flattened_urls.append(u)
    try:
        articles:List[NewsEntity] = await scrape_specified_news(parser_class,flattened_urls)
    except Exception as e:
        print("error:",e)
        raise e
    print("articles:",articles)
    print("len(articles)",len(articles))
    # Translate
    # await asyncio.gather(*[translate_article(article) for article in articles])
    # Update
    async with AsyncSessionLocal() as db:
        await news_repository.update_all_articles(articles, db)
    return flattened_urls

    
async def get_urls_by_news_media_where_xxx_is_null_or_the_news_is_native(media_name,filter):
    async with AsyncSessionLocal() as db:
        return await news_repository.get_urls_by_news_media_where_xxx_is_null_or_the_news_is_native(media_name,filter,db)
        
    
async def retry_urls_where_XXX_is_null_or_the_news_is_native(media_name,filter,parser_class):
    urls=[]
    # Search for urls
    try:
        urls=await get_urls_by_news_media_where_xxx_is_null_or_the_news_is_native(media_name,filter)
    except Exception as e:
        print("❌ cannot fetch urls:",e)
        return []
    # Scrape
    try:
        articles:List[NewsEntity]=await scrape_specified_news(parser_class,urls)
    except Exception as e:
        print("❌ cannot scrape specified news:",e)
        return []
    # # Store
    try:
        async with AsyncSessionLocal() as db:
            articles=await news_repository.update_all_articles(articles, db)
    except Exception as e:
        print("❌ Failed to store articles:", e)
        urls=[article.url for article in articles]
        return []  # or handle however makes sense for your use case
    print("urls:",urls)
    return urls

    