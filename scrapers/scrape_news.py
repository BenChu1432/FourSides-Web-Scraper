from app.db.database import AsyncSessionLocal
from app.aws_lambda.send_logs_to_db import send_log_to_lambda
from app.enums.enums import ErrorTypeEnum
from scrapers.news import News
from app.service import news_service, scrape_service
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Fetch urls and return list of news articles
async def scrape_unique_news(parser_class: type[News],jobId,db_factory):
    # Fetch urls
    scraper = parser_class()
    scrape_urls_result = scraper.get_article_urls_with_errors()
    article_urls = scrape_urls_result.urls
    ("✅ Ready to remove duplicate urls!")
    # Remove duplicate urls
    # ******************************************DB Connection******************************************
    try:
        print("Trying to filter out duplicate urls!!!!!")
        async with db_factory() as db:
                unique_urls = await news_service.filter_existing_articles(article_urls, db)
    except Exception as e:
        print("❌ Failed to filter existing articles:", e)
        await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f'"❌ Failed to filter existing articles:", {e}',media_name=scraper.media_name,urls=[scraper.url])
        return []
    # ******************************************DB Connection******************************************
    

    # Scrape content from urls
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=scraper.max_workers)

    async def scrape_article(url):
        article = await loop.run_in_executor(executor, parser_class, url)
        parse_result = await loop.run_in_executor(executor, article.parse_article_with_errors)
        return article, parse_result.errors

    tasks = [scrape_article(url) for url in unique_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    list_of_news = []
    all_errors = []

    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Error fetching article: {result}")
        else:
            article, errors = result
            list_of_news.append(article)
            if errors:
                all_errors.extend(errors)
     # ******************************************DB Connection******************************************
    if all_errors:
        try:
            async with db_factory() as db:
                await scrape_service.log_scrape_error(db, all_errors)
        except Exception as e:
            print("❌ Failed to log errors to DB:", e)
            await send_log_to_lambda(jobId,failure_type=ErrorTypeEnum.DATABASE_TIMEOUT,detail=f"❌ Failed to log errors to DB:, {e}",media_name=scraper.media_name,urls=[scraper.url])
            # Fallback to Lambda

     # ******************************************DB Connection******************************************
    print("list_of_news:",list_of_news)
    return list_of_news


async def scrape_specified_news(parser_class: type[News],urls):
    # Fetch urls
    scraper = parser_class()
    
    # Scrape content from urls
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=scraper.max_workers)

    async def scrape_article(url):
        article = await loop.run_in_executor(executor, parser_class, url)
        parse_result = await loop.run_in_executor(executor, article.parse_article_with_errors)
        return article, parse_result.errors

    tasks = [scrape_article(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    list_of_news = []
    all_errors = []

    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Error fetching article: {result}")
        else:
            article, errors = result
            list_of_news.append(article)
            if errors:
                all_errors.extend(errors)

    return list_of_news

