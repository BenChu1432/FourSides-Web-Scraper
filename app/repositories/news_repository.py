from sqlalchemy.future import select
from app.schemas.news import NewsFilter, NewsResponse
from app.models.newsEntity import NewsEntity
from sqlalchemy import select, and_
from typing import List
from sqlalchemy.dialects.postgresql import insert

async def filter_existing_articles(urls: List[str], db) -> List[NewsEntity]:
    if not urls:
        return []

    # Step 1: Remove duplicates from the input list
    unique_urls = list(set(urls))  # Converts to set to deduplicate, then back to list

    # Step 2: Fetch existing URLs from the DB
    existing_urls_query = select(NewsEntity.url).where(NewsEntity.url.in_(unique_urls))
    result = await db.execute(existing_urls_query)
    existing_urls = set(result.scalars().all())

    # Step 3: Filter out URLs already in the DB
    filtered_articles = [url for url in unique_urls if url not in existing_urls]

    print(f"Filtered out {len(urls) - len(filtered_articles)} existing or duplicate URLs")
    print("unique urls:",filtered_articles)
    return filtered_articles



async def get_filtered_news(filter, db):
    query = select(NewsEntity)

    conditions = []
    print("filter:",filter)

    if filter.start_time is not None:
        conditions.append(NewsEntity.published_at >= filter.start_time)
    if filter.end_time is not None:
        conditions.append(NewsEntity.published_at <= filter.end_time)
    if filter.media_name is not None:
        conditions.append(NewsEntity.media_name == filter.media_name)
    if filter.origin is not None:
        conditions.append(NewsEntity.origin == filter.origin)
    if filter.authors and len(filter.authors)>0:
        # ARRAY contains check (works with PostgreSQL)
        conditions.append(NewsEntity.authors.overlap(filter.authors))

    if conditions:
        query = query.where(and_(*conditions))
    print("query:",query)
    result = await db.execute(query)
    data:List[NewsEntity]=result.scalars().all()
    print("data:",data)
    return data

async def store_all_articles(articles:List[NewsEntity],db):
    print("storing!!!!!!!")
    # Check if content is null
    
    # Prepare list of dictionaries for bulk insert
    values_to_insert = []
    for article in articles:
        values_to_insert.append({
            "media_name": article.media_name,
            "url": article.url,
            "title": article.title,
            "origin": article.origin,
            "content": article.content,
            "content_en": article.content_en,
            "published_at": article.published_at,
            "authors": article.authors,
            "images": article.images,
        })

    # Check if url already exists=>if exists=>skipped
    stmt = insert(NewsEntity).values(values_to_insert).on_conflict_do_nothing(index_elements=['url'])
    await db.execute(stmt)
    await db.commit()
    return articles

async def get_news(db, news_id):
    result = await db.execute(select(NewsEntity).where(NewsEntity.id == news_id))
    return result.scalar_one_or_none()
