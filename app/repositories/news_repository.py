import uuid
from sqlalchemy.future import select
from app.dto.dto import NewsFilter, NewsResponse
from app.modals.authorEntity import AuthorEntity
from app.modals.authorToNewsMediaEntity import AuthorToNewsMediaEntity
from app.modals.newsAuthorEntity import NewsAuthorEntity
from app.modals.newsMediaEntity import NewsMediaEntity
from app.modals.newsQuestionEntity import NewsQuestionEntity, QuestionTypeEnum
from app.modals.scrapeEntity import ScrapeFailure
from app.modals.newsEntity import NewsEntity
from sqlalchemy import ARRAY, TEXT, Integer, cast, column, func, or_, select, and_
from typing import List, Optional
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, literal_column
from sqlalchemy import Table, Column, String, select
from sqlalchemy import values as sa_values
from typing import List,Any
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

# Helpers

def get_enum_value(val: Any) -> str:
    """Return the underlying string for an Enum or the value itself if already a string.
    Returns empty string for None to avoid NOT NULL violations where applicable.
    """
    if val is None:
        return ""
    return getattr(val, "value", val)

def nz(val: Any, default: Any):
    """Coalesce None to a default value."""
    return default if val is None else val

def safe_str(val: Optional[str]) -> str:
    if not isinstance(val, str):
        return ""
    return val.strip()

def safe_list(val) -> list:
    if not isinstance(val, list):
        return []
    return val

# Core operations

async def store_all_articles(articles: List["NewsEntity"], db: AsyncSession):
    print("Storing articles...")

    values_to_insert = []
    news_to_insert = []
    author_links = []
    media_links = []
    question_entities = []

    # In-memory dedupe for link entities (avoid unique constraint races)
    author_link_keys = set()  # (newsId, authorId)
    media_link_keys = set()   # (authorId, newsMediaId)

    for article in articles:
        if not getattr(article, "url", None):
            continue

        # Skip if news already exists
        existing_news = await db.execute(
            select(NewsEntity.id).where(NewsEntity.url == article.url)
        )
        if existing_news.scalars().first():
            continue

        # Normalize enum-like fields
        media_name_str = get_enum_value(getattr(article, "media_name", None))
        origin_str = get_enum_value(getattr(article, "origin", None))

        # Ensure article has an id
        article_id = getattr(article, "id", None) or uuid.uuid4()
        article.id = article_id

        # Insert related questions safely
        
        for q in getattr(article, "true_false_not_given_questions_data", []) or []:
            if not isinstance(q, dict):
                continue
            question_text = safe_str(q.get("question"))
            options = q.get("options") or {}
            answer = safe_str(q.get("answer"))
            explanation = safe_str(q.get("explanation"))
            if not question_text:
                continue
            try:
                question_entities.append(
                    NewsQuestionEntity(
                        id=uuid.uuid4(),
                        question=question_text,
                        options=options,
                        answer=answer,
                        explanation=explanation,
                        newsId=article.id,
                        type=QuestionTypeEnum.TRUE_FALSE_NOT_GIVEN_QUESTION
                    )
                )
            except Exception as e:
                print("❌ Failed to append TFNG question:", e)
        # Iterate over the correct attribute
        print("article.misleading_techniques_questions_data:", getattr(article, "misleading_techniques_questions_data", None))

        # Safely extract the question data
        questions_data = getattr(article, "misleading_techniques_questions_data", [])

        # Ensure it's a list
        if not isinstance(questions_data, list):
            print("⚠️ Expected a list but got:", type(questions_data))
            questions_data = []

        for q in questions_data:
            if not isinstance(q, dict):
                print("⚠️ Skipping non-dict question:", q)
                continue

            # Ensure required fields exist and are strings
            required_keys = ("question", "options", "answer", "explanation")
            if not all(k in q for k in required_keys):
                print("⚠️ Skipping question with missing keys:", q)
                continue

            try:
                question_text = str(q.get("question", "")).strip()
                options = q.get("options") or {}
                answer = str(q.get("answer", "")).strip()
                explanation = str(q.get("explanation", "")).strip()

                # Validate options dict
                if not isinstance(options, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in options.items()):
                    print("⚠️ Skipping question with invalid options format:", options)
                    continue

                if not question_text:
                    print("⚠️ Skipping question with empty text")
                    continue

                question_entities.append(
                    NewsQuestionEntity(
                        id=uuid.uuid4(),
                        question=question_text,
                        options=options,
                        answer=answer,
                        explanation=explanation,
                        newsId=article.id,
                        type=QuestionTypeEnum.MISGUIDING_TECHNIQUES_QUESTION
                    )
                )
            except Exception as e:
                print("❌ Failed to append question entity:", e, "\nData:", q)
        # Prepare News row (coalesce Nones defensively)
        translated_title = nz(
            traditionalChineseUtil.translateIntoTraditionalChinese(getattr(article, "title", None)),
            getattr(article, "title", "") or ""
        )
        translated_content = nz(
            traditionalChineseUtil.translateIntoTraditionalChinese(getattr(article, "content", None)),
            getattr(article, "content", "") or ""
        )

        article_dict = {
            "id": article_id,
            "media_name": media_name_str or "",
            "url": article.url or "",
            "title": nz(traditionalChineseUtil.safeTranslateIntoTraditionalChinese(getattr(article, "title", "")), ""),
            "origin": origin_str or "",
            "content": nz(traditionalChineseUtil.safeTranslateIntoTraditionalChinese(getattr(article, "content", "")), ""),
            "published_at": getattr(article, "published_at", None),

            # All lists or strings — null-safe
            "authors": safe_list(getattr(article, "authors", [])),
            "images": safe_list(getattr(article, "images", [])),
            "refined_title": safe_str(getattr(article, "refined_title", "")),
            "journalistic_merits": safe_list(getattr(article, "journalistic_merits", [])),
            "journalistic_demerits": safe_list(getattr(article, "journalistic_demerits", [])),
            "reporting_intention": safe_str(getattr(article, "reporting_intention", "")),
            "reporting_style": safe_str(getattr(article, "reporting_style", "")),
            "clickbait": getattr(article, "clickbait", None)  # nullable is okay
        }

        values_to_insert.append(article_dict)
        news_to_insert.append(article)

        # Ensure NewsMedia row exists when a media name is present
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

        # Link authors
        for author_names in nz(getattr(article, "authors", None), []):
            # Authors may be joined with '、'
            for author_name in (author_names or "").split("、"):
                author_name = (author_name or "").strip()
                if not author_name:
                    continue

                traditional_chinese_name = (
                    traditionalChineseUtil.translateIntoTraditionalChinese(author_name)
                    or author_name
                )

                # Find or create Author
                result = await db.execute(
                    select(AuthorEntity).where(AuthorEntity.name == traditional_chinese_name)
                )
                author = result.scalars().first()
                if not author:
                    author = AuthorEntity(id=uuid.uuid4(), name=traditional_chinese_name)
                    db.add(author)
                    await db.flush()

                # Link News <-> Author (dedupe)
                key = (article.id, author.id)
                if key not in author_link_keys:
                    author_link_keys.add(key)
                    author_links.append(
                        NewsAuthorEntity(
                            id=uuid.uuid4(),
                            newsId=article.id,
                            authorId=author.id
                        )
                    )

                # Link Author <-> NewsMedia (dedupe)
                if media:
                    mkey = (author.id, media.id)
                    if mkey not in media_link_keys:
                        # Only create link if not existing
                        result = await db.execute(
                            select(AuthorToNewsMediaEntity).where(
                                AuthorToNewsMediaEntity.authorId == author.id,
                                AuthorToNewsMediaEntity.newsMediaId == media.id
                            )
                        )
                        if not result.scalars().first():
                            media_link_keys.add(mkey)
                            media_links.append(
                                AuthorToNewsMediaEntity(
                                    id=uuid.uuid4(),
                                    authorId=author.id,
                                    newsMediaId=media.id
                                )
                            )

    # Bulk insert News with conflict handling by unique url
    if values_to_insert:
        stmt = (
            insert(NewsEntity)
            .values(values_to_insert)
            .on_conflict_do_nothing(index_elements=["url"])
        )
        await db.execute(stmt)

    # Insert question entities
    for q in question_entities:
        db.add(q)

    # Insert NewsAuthorEntity
    for link in author_links:
        db.add(link)

    # Insert AuthorToNewsMediaEntity
    for link in media_links:
        db.add(link)

    await db.commit()
    return news_to_insert