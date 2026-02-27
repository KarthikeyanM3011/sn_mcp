import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# Browser-like headers so documentation sites don't block the crawler
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _make_session() -> aiohttp.ClientSession:
    """Return a ClientSession with browser headers and SSL verification relaxed."""
    connector = aiohttp.TCPConnector(ssl=False)
    return aiohttp.ClientSession(headers=_HEADERS, connector=connector)


class DocCrawler:
    def __init__(self, base_url: str, max_pages: int = 1000):
        self.base_url = base_url.rstrip("/")
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.visited: set[str] = set()

    async def crawl_url(self, url: str) -> dict | None:
        async with _make_session() as session:
            return await self._fetch_page(session, url)

    async def crawl_multiple(self, urls: list[str]) -> dict[str, dict]:
        async with _make_session() as session:
            tasks = [self._fetch_page(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        pages = {}
        for url, result in zip(urls, results):
            if isinstance(result, dict):
                pages[url] = result
            else:
                logger.warning("Skipped %s — %s", url, result)
        return pages

    async def crawl_domain(self, sitemap_url: str = None) -> dict[str, dict]:
        urls_to_crawl = []
        if sitemap_url:
            urls_to_crawl = await self._parse_sitemap(sitemap_url)
        if not urls_to_crawl:
            urls_to_crawl = [self.base_url]

        queue = deque(urls_to_crawl)
        pages = {}
        seen = set(urls_to_crawl)

        async with _make_session() as session:
            while queue and len(pages) < self.max_pages:
                batch = []
                for _ in range(min(10, len(queue))):
                    if queue:
                        batch.append(queue.popleft())

                tasks = [self._fetch_page(session, url) for url in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch, results):
                    if isinstance(result, dict):
                        pages[url] = result
                        for link in result.get("links", []):
                            if link not in seen:
                                seen.add(link)
                                queue.append(link)
                    else:
                        logger.warning("Skipped %s — %s", url, result)

        return pages

    async def _parse_sitemap(self, sitemap_url: str) -> list[str]:
        try:
            async with _make_session() as session:
                async with session.get(
                    sitemap_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=True,
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Sitemap %s returned HTTP %s", sitemap_url, resp.status)
                        return []
                    text = await resp.text()
            root = ET.fromstring(text)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            urls = [loc.text.strip() for loc in root.findall(".//sm:loc", ns) if loc.text]
            return [u for u in urls if urlparse(u).netloc == self.domain]
        except Exception as e:
            logger.warning("Sitemap parse failed for %s: %s", sitemap_url, e)
            return []

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> dict | None:
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    logger.warning("HTTP %s for %s", resp.status, url)
                    return None
                html = await resp.text()
            logger.debug("Fetched %s (%d chars)", url, len(html))
            return self._parse_page(url, html)
        except Exception as e:
            logger.warning("Fetch error for %s: %s", url, e)
            return None

    def _parse_page(self, url: str, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.select("script, style, iframe"):
            tag.decompose()

        breadcrumb = self._extract_breadcrumb(soup, url)
        title = soup.title.string.strip() if soup.title and soup.title.string else url.split("/")[-1]

        main = (
            soup.select_one("main")
            or soup.select_one("article")
            or soup.select_one(".content")
            or soup.select_one(".docs-content")
            or soup.select_one('[role="main"]')
            or soup.body
        )
        for tag in (main or soup).select("nav, footer, .sidebar, .nav, aside, .toc"):
            tag.decompose()

        content = main.get_text(separator="\n", strip=True) if main else ""

        links = []
        for a in soup.find_all("a", href=True):
            full = urljoin(url, a["href"]).split("#")[0].rstrip("/")
            if urlparse(full).netloc == self.domain and full not in links:
                links.append(full)

        return {
            "url": url,
            "title": title,
            "breadcrumb": breadcrumb,
            "content": content,
            "links": links,
        }

    def _extract_breadcrumb(self, soup: BeautifulSoup, url: str) -> str:
        # Strategy 1: structured breadcrumb element
        breadcrumb_el = soup.select_one(
            'nav[aria-label="breadcrumb"], .breadcrumb, [class*="breadcrumb"]'
        )
        if breadcrumb_el:
            parts = [a.get_text(strip=True) for a in breadcrumb_el.find_all("a")]
            current = breadcrumb_el.find("span", attrs={"aria-current": "page"})
            if current:
                parts.append(current.get_text(strip=True))
            if parts:
                return " > ".join(parts)

        # Strategy 2: active item in sidebar nav — walk DOM upward collecting parent section labels
        sidebar = soup.select_one(
            "nav.sidebar, .sidebar-nav, aside nav, [class*='sidebar'], [class*='nav-tree']"
        )
        if sidebar:
            active = sidebar.select_one(
                "a.active, a[aria-current='page'], li.active a, .selected a, [class*='active'] a"
            )
            if active:
                path_parts = []
                el = active.parent
                while el and el != sidebar:
                    label = el.find_previous_sibling(["h3", "h4", "h5", "strong", "span"])
                    if label:
                        text = label.get_text(strip=True)
                        if text and text not in path_parts:
                            path_parts.insert(0, text)
                    el = el.parent
                path_parts.append(active.get_text(strip=True))
                if len(path_parts) > 1:
                    return " > ".join(path_parts)

        # Strategy 3: derive from URL path segments
        path = urlparse(url).path.strip("/")
        parts = [p.replace("-", " ").replace("_", " ").title() for p in path.split("/") if p]
        return " > ".join(parts) if parts else url
