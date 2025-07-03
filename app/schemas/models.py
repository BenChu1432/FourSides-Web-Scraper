from enum import Enum
from typing import List
from pydantic import BaseModel, HttpUrl

class Region(str, Enum):
    GLOBAL = 'Global'
    NORTH_AMERICA = 'North America'
    EUROPE = 'Europe'
    ASIA = 'Asia'
    SOUTH_AMERICA = 'South America'
    AFRICA = 'Africa'
    OCEANIA = 'Oceania'

class Topic(str, Enum):
    POLITICS = 'Politics'
    TECHNOLOGY = 'Technology'
    BUSINESS = 'Business'
    SPORTS = 'Sports'
    HEALTH = 'Health'
    ENTERTAINMENT = 'Entertainment'
    SCIENCE = 'Science'

class Preferences(BaseModel):
    region: Region
    topics: List[Topic]

class Article(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: HttpUrl
    region: Region
    topics: List[Topic]
    bias_score: float

class NewsRequest(BaseModel):
    url: HttpUrl
    media: str

class NewsResponse(BaseModel):
    title: str
    content: str