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
    # Fetch urls
    scraper = parser_class()
    scrape_urls_result = scraper.get_article_urls_with_errors()

    article_urls = scrape_urls_result.urls

    # Scrape content from urls
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=scraper.max_workers)

    async def scrape_article(url):
        article = await loop.run_in_executor(executor, parser_class, url)
        parse_result = await loop.run_in_executor(executor, article.parse_article_with_errors)
        return article, parse_result.errors

    tasks = [scrape_article(url) for url in article_urls]
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
        await error_service.log_error(db, all_errors)

    return list_of_news

