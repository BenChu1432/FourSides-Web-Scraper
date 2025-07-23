from typing import List, Dict, Optional

from pydantic import BaseModel, HttpUrl
from app.modals.errorEntity import ErrorTypeEnum

class FetchUrlsResult:
    def __init__(self, urls: Optional[List[str]] = None, errors: Optional[List[Dict]] = None):
        self.urls = urls or []
        self.errors = errors or []

    def add_error(self, failure_type: ErrorTypeEnum, media_name: str, url: Optional[str], reason: str, stage: Optional[str] = None):
        self.errors.append({
            "failure_type": failure_type,
            "media_name": media_name,
            "url": url,
            "reason": reason,
        })

class ParseArticleResult:
    def __init__(self, errors: Optional[List[Dict]] = None):
        self.errors = errors or []

    def add_error(self, failure_type: ErrorTypeEnum, media_name: str, url: Optional[str], reason: str, stage: Optional[str] = None):
        self.errors.append({
            "failure_type": failure_type,
            "media_name": media_name,
            "url": url,
            "reason": reason,
        })


class NewsFilter(BaseModel):
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    media_name: Optional[str] = None
    origin: Optional[str] = None
    authors: Optional[List[str]] = None


class NewsRequest(BaseModel):
    url: HttpUrl
    media: str

class NewsResponse(BaseModel):
    url: Optional[HttpUrl]
    media_name: Optional[str]
    title:  Optional[str]
    origin: Optional[str]
    content:  Optional[str]
    published_at: Optional[int] 
    authors: List[str] = []
    images: List[str] = []
    # correctly convert a SQLAlchemy ORM object into a JSON response.
    class Config:
        from_attributes = True