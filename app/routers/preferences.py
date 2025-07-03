from fastapi import APIRouter, HTTPException
from app.schemas.models import NewsRequest, NewsResponse, Preferences, Region, Topic

router = APIRouter()

# in-memory store for MVP
_store: Preferences | None = None

@router.get("/", response_model=Preferences)
def get_preferences():
    # default prefs if none set
    return _store or Preferences(region=Region.GLOBAL, topics=[])

@router.post("/", response_model=Preferences)
def set_preferences(prefs: Preferences):
    global _store
    _store = prefs
    return _store
