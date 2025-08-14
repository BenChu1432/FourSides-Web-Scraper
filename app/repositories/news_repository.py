import uuid
from sqlalchemy.future import select
from app.dto.dto import NewsFilter, NewsResponse
from app.modals.authorEntity import AuthorEntity
from app.modals.authorToNewsMediaEntity import AuthorToNewsMediaEntity
from app.modals.newsAuthorEntity import NewsAuthorEntity
from app.modals.newsMediaEntity import NewsMediaEntity
from app.modals.scrapeEntity import ScrapeFailure
from app.modals.newsEntity import NewsEntity
from sqlalchemy import ARRAY, TEXT, Integer, cast, column, func, or_, select, and_
from typing import List, Optional
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, literal_column
from sqlalchemy import Table, Column, String, select
from sqlalchemy import values as sa_values
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.enums.enums import MediaNameEnum,OriginEnum  # make sure to import the Enum class
from util import traditionalChineseUtil


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

async def store_all_articles(articles: List[NewsEntity], db):
    print("Storing articles...")

    values_to_insert = []
    news_to_insert = []
    author_links = []
    media_links = []

    for article in articles:
        if not article.url:
            continue

        # 🔍 Skip if sews already exists
        existing_news = await db.execute(
            select(NewsEntity.id).where(NewsEntity.url == article.url)
        )
        if existing_news.scalars().first():
            continue

        # ✅ Handle Enum safely
        media_name_str = getattr(article.media_name, "value", article.media_name)
        origin_str = getattr(article.origin, "value", article.origin)

        # ✅ Generate id if missing
        article_id = getattr(article, "id", None) or uuid.uuid4()
        article.id = article_id  # Ensure it's set for relationship use

        # 📦 Prepare dict for bulk insert
        article_dict = {
            "id": article_id,
            "media_name": media_name_str,
            "url": article.url,
            "title": traditionalChineseUtil.translateIntoTraditionalChinese(article.title),
            "origin": origin_str,
            "content": traditionalChineseUtil.translateIntoTraditionalChinese(article.content),
            "content_en": article.content_en,
            "published_at": article.published_at,
            "authors": article.authors,
            "images": article.images,
        }
        values_to_insert.append(article_dict)
        news_to_insert.append(article)

        # 🏷️ Prepare NewsMediaEntity (only once per article)
        media = None
        if media_name_str:
            result = await db.execute(
                select(NewsMediaEntity).where(NewsMediaEntity.name == media_name_str)
            )
            media = result.scalars().first()

            if not media:
                media = NewsMediaEntity(
                    id=uuid.uuid4(),
                    name=media_name_str,
                    imageUrl=""
                )
                db.add(media)
                await db.flush()

        # 👤 Link authors
        if article.authors:
            for author_names in article.authors:
                authors = author_names.split('、')
                for author_name in authors:
                    traditional_chinese_name=traditionalChineseUtil.translateIntoTraditionalChinese(author_name)
                    result = await db.execute(
                        select(AuthorEntity).where(AuthorEntity.name == traditional_chinese_name)
                    )
                    author = result.scalars().first()

                    if not author:
                        author = AuthorEntity(id=uuid.uuid4(), name=traditional_chinese_name)
                        db.add(author)
                        await db.flush()

                    # Link News <-> Author
                    author_links.append(NewsAuthorEntity(
                        id=uuid.uuid4(),
                        newsId=article.id,
                        authorId=author.id
                    ))

                    # Link Author <-> NewsMedia
                    if media:
                        result = await db.execute(
                            select(AuthorToNewsMediaEntity).where(
                                AuthorToNewsMediaEntity.authorId == author.id,
                                AuthorToNewsMediaEntity.newsMediaId == media.id
                            )
                        )
                        if not result.scalars().first():
                            media_links.append(AuthorToNewsMediaEntity(
                                id=uuid.uuid4(),
                                authorId=author.id,
                                newsMediaId=media.id
                            ))

    # 🧾 Bulk insert News
    if values_to_insert:
        stmt = insert(NewsEntity).values(values_to_insert)\
            .on_conflict_do_nothing(index_elements=["url"])
        await db.execute(stmt)

    # 🧾 Insert NewsAuthorEntity
    for link in author_links:
        db.add(link)

    # 🧾 Insert AuthorToNewsMediaEntity
    for link in media_links:
        db.add(link)

    await db.commit()
    return news_to_insert  # ✅ Return list, not None or []


async def update_all_articles(articles: List[NewsEntity], db: AsyncSession):
    for article in articles:
        stmt = (
            update(NewsEntity)
            .where(NewsEntity.url == article.url)
            .values({
                "title": traditionalChineseUtil.safeTranslateIntoTraditionalChinese(article.title),
                "content": traditionalChineseUtil.safeTranslateIntoTraditionalChinese(article.content),
                "content_en": article.content_en,
                "published_at": article.published_at,
                "authors": article.authors,
                "images": article.images,
                "origin": article.origin,
            })
        )
        await db.execute(stmt)
    await db.commit()
    return articles  

async def get_news(db, news_id):
    result = await db.execute(select(NewsEntity).where(NewsEntity.id == news_id))
    return result.scalar_one_or_none()


async def get_news_urls_that_need_retrying(news_media,db):
   result=await db.execute(select(ScrapeFailure.url).where(ScrapeFailure.media_name == news_media))
   urls = result.scalars().all()
   return urls

async def get_urls_by_news_media_where_xxx_is_null_or_the_news_is_native(news_media: str, filter: str, db):
    query = select(NewsEntity.url).where(NewsEntity.media_name == news_media)

    if filter == "author":
        query = query.where(
            func.coalesce(func.array_length(NewsEntity.authors, 1), 0) == 0,
        )
    elif filter == "published_at":
        query = query.where(NewsEntity.published_at == None)
    elif filter == "title":
        query = query.where(NewsEntity.title == None)
    elif filter == "native":
        query = query.where(NewsEntity.origin == "native")

    result = await db.execute(query)
    print("result:",result)
    data = result.scalars().all()
    urls = list(data)  # or just return data directly
    print("urls:",urls)
    return urls