from typing import Dict, List, Type
from fastapi import HTTPException
from app.dto.dto import FetchUrlsResult
from app.models.newsEntity import NewsEntity
from scrapers.news import News
from app.schemas.news import NewsResponse
import constant
import concurrent
from app.service import error_service

import asyncio
from concurrent.futures import ThreadPoolExecutor

# Fetch urls and return list of news articles
async def scrape_news(parser_class: type[News], db):
    scraper = parser_class()

    # These are blocking, but let's assume this one is fast enough to run in the main thread
    scrape_urls_result: FetchUrlsResult = scraper.get_article_urls_with_errors()

    if scrape_urls_result.errors:
        await error_service.log_error(db, scrape_urls_result.errors)

    article_urls = scrape_urls_result.urls

    # Scrape data from websites using urls
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=scraper.max_workers)

    async def scrape_article(url):
        # Run parser_class(url) in a thread
        article = await loop.run_in_executor(executor, parser_class, url)

        # Run article.parse_article_with_errors in a thread
        parseArticleResult = await loop.run_in_executor(executor, article.parse_article_with_errors)

        if parseArticleResult.errors:
            await error_service.log_error(db, parseArticleResult.errors)

        return NewsEntity(
            url=article.url,
            media_name=article.media_name,
            title=article.title,
            content=article.content,
            published_at=article.published_at,
            authors=article.authors,
            images=article.images,
            origin=article.origin
        )

    # Launch all fetch_article calls concurrently
    tasks = [scrape_article(url) for url in article_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    list_of_news = []
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ Error fetching article: {result}")
        else:
            list_of_news.append(result)

    return list_of_news
