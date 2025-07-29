from app.db.database import AsyncSessionLocal
from scrapers.news import News
from app.service import error_service, news_service
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Fetch urls and return list of news articles
# pen a short-lived DB session where needed
async def scrape_unique_news(parser_class: type[News],db_factory):
    # Fetch urls
    scraper = parser_class()
    scrape_urls_result = scraper.get_article_urls_with_errors()
    article_urls = scrape_urls_result.urls
    ("✅ Ready to remove duplicate urls!")
    # Remove duplicate urls
    try:
        print("Trying to filter out duplicate urls!!!!!")
        async with db_factory() as db:
                unique_urls = await news_service.filter_existing_articles(article_urls, db)
    except Exception as e:
        print("error:",e)
        raise e
    

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

    if all_errors:
        async with db_factory() as db:
            await error_service.log_error(db, all_errors)

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

