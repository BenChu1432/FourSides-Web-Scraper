from enum import Enum
from typing import List
from pydantic import BaseModel, HttpUrl
from typing import Optional

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
    title:  Optional[str]
    origin: Optional[str]
    content:  Optional[str]
    published_at: Optional[int] 
    authors: List[str] = []
    images: List[str] = []
    # correctly convert a SQLAlchemy ORM object into a JSON response.
    class Config:
        from_attributes = True