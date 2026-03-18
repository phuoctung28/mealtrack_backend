"""
Scrapy settings for nutree_scrapers project.
"""

BOT_NAME = "nutree_scrapers"

SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# Polite scraping
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
ROBOTSTXT_OBEY = True

# Identify ourselves
USER_AGENT = "NutreeAI/1.0 (contact@nutree.ai)"

# Handle encoding issues from viendinhduong.vn
DOWNLOADER_MIDDLEWARES = {
    "middlewares.EncodingFixMiddleware": 543,
}

# Default encoding
FEED_EXPORT_ENCODING = "utf-8"

# Output feeds: spider name maps to JSON file
FEEDS = {
    "../../data/%(name)s.json": {
        "format": "json",
        "encoding": "utf-8",
        "overwrite": True,
    }
}

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Timeout
DOWNLOAD_TIMEOUT = 30

# Disable cookies (not needed)
COOKIES_ENABLED = False

# Log level
LOG_LEVEL = "INFO"
