import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from moveworks_mcp.auth.auth_manager import AuthManager
from moveworks_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class QueryMoveworksDocsParams(BaseModel):
    query: str = Field(..., description="The question or topic to search for in Moveworks documentation")
    max_pages: int = Field(default=10, description="Maximum number of relevant documentation pages to fetch (default: 10)")
    use_sitemap: bool = Field(default=True, description="Use sitemap.xml for faster discovery (default: True)")


class DocumentPage:
    def __init__(self, url: str, title: str = "", description: str = "", breadcrumb: str = ""):
        self.url = url
        self.title = title
        self.description = description
        self.breadcrumb = breadcrumb
        self.relevance_score = 0.0
        self.content = ""

    def __repr__(self):
        return f"DocumentPage(url={self.url}, title={self.title}, score={self.relevance_score})"


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return normalized.rstrip('/')


def extract_page_metadata(soup: BeautifulSoup, url: str) -> Tuple[str, str, str]:
    title = ""
    if soup.title:
        title = soup.title.string.strip() if soup.title.string else ""
    if not title:
        h1 = soup.find('h1')
        title = h1.get_text(strip=True) if h1 else ""

    description = ""
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        description = meta_desc['content'].strip()
    if not description:
        p = soup.find('p')
        if p:
            description = p.get_text(strip=True)[:200]

    breadcrumb = ""
    breadcrumb_el = soup.find('nav', class_=re.compile(r'breadcrumb', re.I))
    if breadcrumb_el:
        breadcrumb = ' > '.join([item.get_text(strip=True) for item in breadcrumb_el.find_all('a')])

    return title, description, breadcrumb


def extract_text_from_html(html_content: str) -> str:
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()

        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|docs', re.I))
        if main_content:
            soup = main_content

        text_parts = []

        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            level = heading.name[1]
            text_parts.append(f"\n{'#' * int(level)} {heading.get_text(strip=True)}\n")
            heading.decompose()

        for code_block in soup.find_all(['pre', 'code']):
            code_text = code_block.get_text(strip=True)
            if code_text:
                text_parts.append(f"\n```\n{code_text}\n```\n")
            code_block.decompose()

        text = soup.get_text(separator='\n', strip=True)

        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        full_text = '\n'.join(text_parts) + '\n' + text

        return full_text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return ""


def fetch_sitemap(sitemap_url: str, timeout: int) -> List[str]:
    logger.info(f"Fetching sitemap from {sitemap_url}")
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(sitemap_url)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            urls = []
            for url_element in root.findall('.//ns:url', namespace):
                loc = url_element.find('ns:loc', namespace)
                if loc is not None and loc.text:
                    url = normalize_url(loc.text)
                    if '/docs' in url:
                        urls.append(url)

            logger.info(f"Found {len(urls)} documentation URLs in sitemap")
            return urls
    except Exception as e:
        logger.error(f"Error fetching sitemap: {e}")
        return []


def build_sitemap_from_xml(sitemap_url: str, timeout: int) -> Dict[str, DocumentPage]:
    sitemap_urls = fetch_sitemap(sitemap_url, timeout)

    if not sitemap_urls:
        return {}

    sitemap: Dict[str, DocumentPage] = {}
    batch_size = 50

    logger.info(f"Fetching metadata for {len(sitemap_urls)} pages in batches of {batch_size}")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for i in range(0, len(sitemap_urls), batch_size):
            batch = sitemap_urls[i:i+batch_size]

            for url in batch:
                try:
                    logger.debug(f"Fetching metadata: {url}")
                    response = client.get(url)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')
                    title, description, breadcrumb = extract_page_metadata(soup, url)

                    doc_page = DocumentPage(
                        url=url,
                        title=title,
                        description=description,
                        breadcrumb=breadcrumb
                    )
                    sitemap[url] = doc_page

                except httpx.HTTPError as e:
                    logger.warning(f"HTTP error fetching {url}: {e}")
                except Exception as e:
                    logger.warning(f"Error processing {url}: {e}")

            logger.info(f"Processed {min(i+batch_size, len(sitemap_urls))}/{len(sitemap_urls)} pages")

    logger.info(f"Built sitemap with {len(sitemap)} pages")
    return sitemap


def build_sitemap_manual(base_url: str, max_depth: int, timeout: int) -> Dict[str, DocumentPage]:
    sitemap: Dict[str, DocumentPage] = {}
    visited_urls: Set[str] = set()
    urls_to_visit: List[Tuple[str, int]] = [(base_url, 0)]

    logger.info(f"Building sitemap manually from {base_url} with max depth {max_depth}")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        while urls_to_visit:
            current_url, depth = urls_to_visit.pop(0)
            normalized_url = normalize_url(current_url)

            if normalized_url in visited_urls or depth > max_depth:
                continue

            try:
                logger.info(f"Discovering page: {normalized_url} (depth: {depth})")
                response = client.get(current_url)
                response.raise_for_status()

                visited_urls.add(normalized_url)

                soup = BeautifulSoup(response.text, 'html.parser')
                title, description, breadcrumb = extract_page_metadata(soup, normalized_url)

                doc_page = DocumentPage(
                    url=normalized_url,
                    title=title,
                    description=description,
                    breadcrumb=breadcrumb
                )
                sitemap[normalized_url] = doc_page

                if depth < max_depth:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                            continue

                        absolute_url = urljoin(current_url, href)
                        normalized_link = normalize_url(absolute_url)

                        if 'help.moveworks.com/docs' in normalized_link and normalized_link not in visited_urls:
                            if not any(url == normalized_link for url, _ in urls_to_visit):
                                urls_to_visit.append((normalized_link, depth + 1))

            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching {current_url}: {e}")
            except Exception as e:
                logger.error(f"Error processing {current_url}: {e}")

    logger.info(f"Sitemap built with {len(sitemap)} pages")
    return sitemap


def calculate_relevance_score(page: DocumentPage, query: str, query_terms: List[str]) -> float:
    score = 0.0
    query_lower = query.lower()

    title_lower = page.title.lower()
    for term in query_terms:
        if len(term) > 2:
            if query_lower in title_lower:
                score += 50
            score += title_lower.count(term) * 10

    url_path = urlparse(page.url).path.lower()
    for term in query_terms:
        if len(term) > 2:
            if term in url_path:
                score += 5
            path_segments = url_path.split('/')
            if term in path_segments:
                score += 8

    description_lower = page.description.lower()
    for term in query_terms:
        if len(term) > 2:
            if query_lower in description_lower:
                score += 15
            score += description_lower.count(term) * 3

    breadcrumb_lower = page.breadcrumb.lower()
    for term in query_terms:
        if len(term) > 2:
            score += breadcrumb_lower.count(term) * 2

    return score


def select_relevant_pages(sitemap: Dict[str, DocumentPage], query: str, max_pages: int) -> List[DocumentPage]:
    logger.info(f"Selecting relevant pages from {len(sitemap)} available pages")

    query_terms = [term.lower() for term in query.split() if len(term) > 2]

    for page in sitemap.values():
        page.relevance_score = calculate_relevance_score(page, query, query_terms)

    relevant_pages = [page for page in sitemap.values() if page.relevance_score > 0]
    relevant_pages.sort(key=lambda p: p.relevance_score, reverse=True)

    selected_pages = relevant_pages[:max_pages]

    logger.info(f"Selected {len(selected_pages)} relevant pages out of {len(relevant_pages)} candidates")
    for i, page in enumerate(selected_pages[:5], 1):
        logger.info(f"  {i}. {page.title} (score: {page.relevance_score:.1f}) - {page.url}")

    return selected_pages


def fetch_page_content(pages: List[DocumentPage], timeout: int) -> List[DocumentPage]:
    logger.info(f"Fetching content for {len(pages)} selected pages")

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for page in pages:
            try:
                logger.info(f"Fetching content: {page.url}")
                response = client.get(page.url)
                response.raise_for_status()

                page.content = extract_text_from_html(response.text)

            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching {page.url}: {e}")
                page.content = ""
            except Exception as e:
                logger.error(f"Error processing {page.url}: {e}")
                page.content = ""

    return pages


def build_knowledge_base(pages: List[DocumentPage]) -> Dict[str, Any]:
    knowledge_base = {
        "total_pages": len(pages),
        "pages": [],
        "aggregated_content": "",
        "key_topics": [],
    }

    all_content_parts = []
    key_topics_set = set()

    for page in pages:
        if not page.content:
            continue

        page_info = {
            "title": page.title,
            "url": page.url,
            "description": page.description,
            "breadcrumb": page.breadcrumb,
            "relevance_score": page.relevance_score,
            "content_length": len(page.content),
            "content": page.content,
        }
        knowledge_base["pages"].append(page_info)

        all_content_parts.append(f"\n\n{'='*80}\n")
        all_content_parts.append(f"SOURCE: {page.title}\n")
        all_content_parts.append(f"URL: {page.url}\n")
        if page.breadcrumb:
            all_content_parts.append(f"PATH: {page.breadcrumb}\n")
        all_content_parts.append(f"{'='*80}\n\n")
        all_content_parts.append(page.content)

        if page.breadcrumb:
            topics = [t.strip() for t in page.breadcrumb.split('>')]
            key_topics_set.update(topics)

    knowledge_base["aggregated_content"] = ''.join(all_content_parts)
    knowledge_base["key_topics"] = list(key_topics_set)

    return knowledge_base


def query_moveworks_docs(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: QueryMoveworksDocsParams
) -> Dict[str, Any]:
    try:
        logger.info(f"=" * 80)
        logger.info(f"INTELLIGENT DOC QUERY: {params.query}")
        logger.info(f"=" * 80)

        logger.info("Step 1: Building sitemap...")

        if params.use_sitemap:
            sitemap_url = "https://help.moveworks.com/sitemap.xml"
            sitemap = build_sitemap_from_xml(sitemap_url, config.timeout)
        else:
            sitemap = build_sitemap_manual(
                base_url=config.docs_base_url,
                max_depth=3,
                timeout=config.timeout
            )

        if not sitemap:
            return {
                "success": False,
                "message": "Failed to build documentation sitemap",
                "query": params.query,
                "sitemap_size": 0,
                "selected_pages": 0,
                "knowledge_base": None,
            }

        logger.info("Step 2: Selecting relevant pages...")
        selected_pages = select_relevant_pages(sitemap, params.query, params.max_pages)

        if not selected_pages:
            return {
                "success": False,
                "message": "No relevant pages found for the query",
                "query": params.query,
                "sitemap_size": len(sitemap),
                "selected_pages": 0,
                "knowledge_base": None,
                "available_pages": [
                    {"title": page.title, "url": page.url, "description": page.description}
                    for page in list(sitemap.values())[:20]
                ],
            }

        logger.info("Step 3: Fetching content for selected pages...")
        pages_with_content = fetch_page_content(selected_pages, config.timeout)

        logger.info("Step 4: Building knowledge base...")
        knowledge_base = build_knowledge_base(pages_with_content)

        logger.info(f"Knowledge base ready with {knowledge_base['total_pages']} pages")
        logger.info(f"Total content length: {len(knowledge_base['aggregated_content'])} characters")

        return {
            "success": True,
            "message": f"Successfully built knowledge base from {len(selected_pages)} relevant pages",
            "query": params.query,
            "sitemap_size": len(sitemap),
            "selected_pages": len(selected_pages),
            "knowledge_base": knowledge_base,
            "summary": {
                "total_pages_discovered": len(sitemap),
                "relevant_pages_selected": len(selected_pages),
                "pages_with_content": len([p for p in pages_with_content if p.content]),
                "total_content_chars": len(knowledge_base['aggregated_content']),
                "key_topics": knowledge_base['key_topics'],
            },
        }

    except Exception as e:
        logger.error(f"Error querying Moveworks docs: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "query": params.query,
            "sitemap_size": 0,
            "selected_pages": 0,
            "knowledge_base": None,
        }
