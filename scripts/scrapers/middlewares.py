"""
Scrapy downloader middlewares for nutree_scrapers.

EncodingFixMiddleware handles non-standard HTTP headers from viendinhduong.vn
which causes "Invalid header value char" errors in Scrapy.
"""

import re
import logging
from scrapy import signals
from scrapy.http import Response

logger = logging.getLogger(__name__)


class EncodingFixMiddleware:
    """Fix non-standard HTTP headers returned by viendinhduong.vn.

    The site sends headers containing invalid characters (e.g. Vietnamese
    diacritics or control chars) which Scrapy rejects. This middleware strips
    those chars and forces UTF-8 decoding on the response body.
    """

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def spider_opened(self, spider):
        logger.info("EncodingFixMiddleware active for spider: %s", spider.name)

    def process_response(self, request, response: Response, spider):
        """Strip invalid chars from response headers and force UTF-8."""
        try:
            # Build cleaned headers dict — strip non-ASCII / control chars
            clean_headers = {}
            for key, value in response.headers.items():
                clean_key = self._strip_invalid(key)
                clean_value = self._strip_invalid(value)
                if clean_key:
                    clean_headers[clean_key] = clean_value

            # Replace response with UTF-8 forced body
            body = response.body
            try:
                # Try declared encoding first, fall back to utf-8 with replace
                body.decode("utf-8")
            except UnicodeDecodeError:
                logger.debug(
                    "Non-UTF-8 body on %s — decoding with 'replace'", request.url
                )
                body = response.body.decode("utf-8", errors="replace").encode("utf-8")

            return response.replace(body=body, headers=clean_headers)

        except Exception as exc:  # noqa: BLE001
            logger.warning("EncodingFixMiddleware error on %s: %s", request.url, exc)
            return response

    @staticmethod
    def _strip_invalid(value) -> str:
        """Remove non-printable / non-ASCII chars from a header key or value."""
        if isinstance(value, (bytes, bytearray)):
            try:
                value = value.decode("latin-1", errors="replace")
            except Exception:
                return ""
        text = str(value)
        # Keep only printable ASCII (0x20–0x7E) and common safe chars
        return re.sub(r"[^\x20-\x7e]", "", text).strip()
