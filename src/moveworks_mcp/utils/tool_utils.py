from typing import Any, Callable, Dict, Tuple, Type

from moveworks_mcp.tools.kb_tools import (
    MwKbIndexPagesParams,
    MwKbIndexDomainParams,
    MwKbListParams,
    MwKbRemoveParams,
    MwKbSearchParams,
    mw_kb_index_pages,
    mw_kb_index_domain,
    mw_kb_list,
    mw_kb_remove,
    mw_kb_search,
)

ParamsModel = Type[Any]
ToolDefinition = Tuple[Callable, ParamsModel, Type, str, str]


def get_tool_definitions() -> Dict[str, ToolDefinition]:
    tool_definitions: Dict[str, ToolDefinition] = {
        "mw_kb_index_pages": (
            mw_kb_index_pages,
            MwKbIndexPagesParams,
            Dict[str, Any],
            (
                "Crawl and index one or more specific documentation page URLs into the Moveworks knowledge base. "
                "Each URL is fetched individually (no link-following). Extracts title, breadcrumb navigation path, "
                "and full content, then creates 3 semantic vectors per page for high-quality retrieval. "
                "Use this to add specific pages or refresh individual entries."
            ),
            "raw_dict",
        ),
        "mw_kb_index_domain": (
            mw_kb_index_domain,
            MwKbIndexDomainParams,
            Dict[str, Any],
            (
                "Crawl and index an entire documentation domain into the Moveworks knowledge base. "
                "Parses sitemap.xml first for fast URL discovery, then crawls concurrently in batches of 10. "
                "Stays within the domain boundary. Creates 3 semantic vectors per page "
                "(breadcrumb-only, title+breadcrumb, full content) backed by a ChromaDB persistent store. "
                "Use this once to build the full KB for a site like help.moveworks.com."
            ),
            "raw_dict",
        ),
        "mw_kb_list": (
            mw_kb_list,
            MwKbListParams,
            Dict[str, Any],
            (
                "List all pages currently indexed in the Moveworks knowledge base, grouped by domain. "
                "Each entry shows the URL, title, and navigation_path (breadcrumb hierarchy). "
                "Pass an optional domain filter to scope results. "
                "Use this to explore what documentation is available before searching."
            ),
            "raw_dict",
        ),
        "mw_kb_remove": (
            mw_kb_remove,
            MwKbRemoveParams,
            Dict[str, Any],
            (
                "Remove pages from the Moveworks knowledge base. "
                "Provide a list of specific URLs to remove individual pages, "
                "a domain string to remove all pages for that domain, or both. "
                "Cleans up both the chunk vectors and the full page store entries."
            ),
            "raw_dict",
        ),
        "mw_kb_search": (
            mw_kb_search,
            MwKbSearchParams,
            Dict[str, Any],
            (
                "Search the Moveworks knowledge base using hybrid semantic + BM25 retrieval. "
                "Encodes the query with sentence-transformers, queries all 3 vector types "
                "(breadcrumb, title_path, full_content), deduplicates by URL, "
                "re-ranks with BM25 (30%) blended with vector similarity (70%), "
                "and returns the top 10 full pages with rank, title, navigation_path, "
                "relevance score, and complete content. "
                "Use this after indexing to answer questions about Moveworks features."
                "For best results search one topic/term at a time in repeated way to get more knowledge"
            ),
            "raw_dict",
        ),
    }
    return tool_definitions
