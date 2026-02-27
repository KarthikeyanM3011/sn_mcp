import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from moveworks_mcp.auth.auth_manager import AuthManager
from moveworks_mcp.kb.crawler import DocCrawler
from moveworks_mcp.kb.indexer import KBIndexer
from moveworks_mcp.kb.search import KBSearch
from moveworks_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

# Singletons — loaded once, reused across all tool calls
_indexer: Optional[KBIndexer] = None
_searcher: Optional[KBSearch] = None


def get_indexer() -> KBIndexer:
    global _indexer
    if _indexer is None:
        _indexer = KBIndexer()
    return _indexer


def get_searcher() -> KBSearch:
    global _searcher
    if _searcher is None:
        _searcher = KBSearch()
    return _searcher


# ── Pydantic param models ──────────────────────────────────────────────────


class MwKbIndexPagesParams(BaseModel):
    urls: List[str] = Field(
        ...,
        description="One or more page URLs to crawl and index individually (no link-following)"
    )
    force_refresh: bool = Field(
        default=False,
        description="If True, re-index pages even if they already exist in the knowledge base (overwrite)"
    )


class MwKbIndexDomainParams(BaseModel):
    sitemap_url: str = Field(
        ...,
        description="Full URL to the sitemap.xml of the documentation site"
    )
    base_url: str = Field(
        ...,
        description="Base URL of the documentation domain (e.g. https://help.moveworks.com)"
    )
    max_pages: int = Field(
        default=300,
        description="Maximum number of pages to crawl and index (default: 300)"
    )
    force_refresh: bool = Field(
        default=False,
        description="If True, re-index pages even if they already exist in the knowledge base (overwrite)"
    )


class MwKbListParams(BaseModel):
    domain: Optional[str] = Field(
        default=None,
        description="Optional domain filter (e.g. 'help.moveworks.com'). Omit to list all indexed pages."
    )


class MwKbRemoveParams(BaseModel):
    urls: Optional[List[str]] = Field(
        default=None,
        description="List of specific page URLs to remove from the index"
    )
    domain: Optional[str] = Field(
        default=None,
        description="Domain whose pages should all be removed (e.g. 'help.moveworks.com')"
    )


class MwKbSearchParams(BaseModel):
    query: str = Field(
        ...,
        description="Natural-language search query. Returns top-10 pages via hybrid semantic + BM25 search."
    )


# ── Tool implementations ───────────────────────────────────────────────────


async def mw_kb_index_pages(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MwKbIndexPagesParams,
) -> Dict[str, Any]:
    try:
        crawler = DocCrawler(base_url=params.urls[0])
        pages = await crawler.crawl_multiple(params.urls)
        indexer = get_indexer()
        result = indexer.index_pages(pages, force=params.force_refresh)
        logger.info(
            "mw_kb_index_pages: %d indexed, %d skipped",
            len(result["indexed"]), len(result["skipped"]),
        )
        return {
            "status": "success",
            "indexed_count": len(result["indexed"]),
            "skipped_count": len(result["skipped"]),
            "indexed_urls": result["indexed"],
            "skipped_urls": result["skipped"],
        }
    except Exception as e:
        logger.error(f"mw_kb_index_pages error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def mw_kb_index_domain(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MwKbIndexDomainParams,
) -> Dict[str, Any]:
    try:
        crawler = DocCrawler(base_url=params.base_url, max_pages=params.max_pages)
        pages = await crawler.crawl_domain(sitemap_url=params.sitemap_url)
        indexer = get_indexer()
        result = indexer.index_pages(pages, force=params.force_refresh)
        logger.info(
            "mw_kb_index_domain: found %d pages, %d indexed, %d skipped",
            len(pages), len(result["indexed"]), len(result["skipped"]),
        )
        return {
            "status": "success",
            "domain": params.base_url,
            "total_pages_found": len(pages),
            "indexed_count": len(result["indexed"]),
            "skipped_count": len(result["skipped"]),
            "indexed_urls": result["indexed"],
            "skipped_urls": result["skipped"],
        }
    except Exception as e:
        logger.error(f"mw_kb_index_domain error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def mw_kb_list(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MwKbListParams,
) -> Dict[str, Any]:
    try:
        indexer = get_indexer()
        pages = indexer.list_pages(domain=params.domain)
        grouped: Dict[str, list] = {}
        for page in pages:
            d = page["domain"]
            grouped.setdefault(d, [])
            grouped[d].append({
                "url": page["url"],
                "title": page["title"],
                "navigation_path": page["breadcrumb"],
            })
        return {
            "total_pages": len(pages),
            "domains": grouped,
        }
    except Exception as e:
        logger.error(f"mw_kb_list error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def mw_kb_remove(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MwKbRemoveParams,
) -> Dict[str, Any]:
    try:
        indexer = get_indexer()
        removed = []
        if params.urls:
            for url in params.urls:
                indexer.remove_page(url)
                removed.append(url)
        if params.domain:
            indexer.remove_domain(params.domain)
            removed.append(f"all pages from domain: {params.domain}")
        logger.info(f"mw_kb_remove: removed {removed}")
        return {
            "status": "success",
            "removed": removed,
        }
    except Exception as e:
        logger.error(f"mw_kb_remove error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


def mw_kb_search(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MwKbSearchParams,
) -> Dict[str, Any]:
    try:
        searcher = get_searcher()
        results = searcher.search(params.query, top_k=10)
        return {
            "query": params.query,
            "total_results": len(results),
            "results": [
                {
                    "rank": i + 1,
                    "url": r["url"],
                    "title": r["title"],
                    "navigation_path": r["breadcrumb"],
                    "relevance_score": r["score"],
                    "content": r["content"],
                }
                for i, r in enumerate(results)
            ],
        }
    except Exception as e:
        logger.error(f"mw_kb_search error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
