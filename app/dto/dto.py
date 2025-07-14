from typing import List, Dict, Optional
from app.models.errorEntity import ErrorTypeEnum

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
