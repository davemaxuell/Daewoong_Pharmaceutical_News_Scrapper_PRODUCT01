# News Scrapers Package
# 각 뉴스 소스별 스크래퍼 모듈

from .base_scraper import BaseScraper, NewsArticle

# Individual imports to avoid circular import issues
# Use direct imports in multi_source_scraper.py instead

__all__ = [
    'BaseScraper',
    'NewsArticle',
]
