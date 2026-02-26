from typing import Any, Callable, Dict, Tuple, Type
from moveworks_mcp.tools.docs_crawler import (
    QueryMoveworksDocsParams,
    query_moveworks_docs as query_docs_tool,
)
from moveworks_mcp.tools.kb_tools import (
    IndexDocumentationParams,
    SearchKnowledgeBaseParams,
    ListKnowledgeBasesParams,
    DeleteKnowledgeBaseParams,
    ListKBDocumentsParams,
    GetDocumentByURLParams,
    index_documentation,
    search_knowledge_base,
    list_knowledge_bases,
    delete_knowledge_base,
    list_kb_documents,
    get_document_by_url,
)
from moveworks_mcp.tools.indexer import (
    IndexUrlParams,
    IndexMultipleUrlsParams,
    ListIndexedContentParams,
    RemoveIndexedContentParams,
    RefreshAllIndexedContentParams,
    index_url as index_url_tool,
    index_multiple_urls as index_multiple_urls_tool,
    list_indexed_content as list_indexed_content_tool,
    remove_indexed_content as remove_indexed_content_tool,
    refresh_all_indexed_content as refresh_all_indexed_content_tool,
)

ParamsModel = Type[Any]
ToolDefinition = Tuple[Callable, ParamsModel, Type, str, str]


def get_tool_definitions() -> Dict[str, ToolDefinition]:
    tool_definitions: Dict[str, ToolDefinition] = {
        "query_moveworks_docs": (
            query_docs_tool,
            QueryMoveworksDocsParams,
            Dict[str, Any],
            "Query Moveworks documentation to answer questions about Moveworks agents, actions, and capabilities. This tool crawls and extracts content from the Moveworks documentation site in real-time (slower). For faster queries, use search_knowledge_base instead.",
            "raw_dict",
        ),
        "index_documentation": (
            index_documentation,
            IndexDocumentationParams,
            Dict[str, Any],
            "Index documentation into a persistent knowledge base for fast searching. Use this tool ONCE to build a cached knowledge base from documentation websites. After indexing, use search_knowledge_base for instant queries without re-crawling.",
            "raw_dict",
        ),
        "search_knowledge_base": (
            search_knowledge_base,
            SearchKnowledgeBaseParams,
            Dict[str, Any],
            "Search a cached knowledge base using hybrid search (multi-query + semantic + keyword). This is MUCH FASTER than real-time crawling. Automatically finds ALL relevant pages for multi-topic queries (e.g., 'http action compound action decision policy'). Returns comprehensive content from multiple pages to provide complete context.",
            "raw_dict",
        ),
        "list_knowledge_bases": (
            list_knowledge_bases,
            ListKnowledgeBasesParams,
            Dict[str, Any],
            "List all available knowledge bases with their statistics (document count, size, last updated, etc.). Use this to see what knowledge bases are available for searching.",
            "raw_dict",
        ),
        "delete_knowledge_base": (
            delete_knowledge_base,
            DeleteKnowledgeBaseParams,
            Dict[str, Any],
            "Delete a knowledge base and all its cached documents. Use this to remove outdated or unused knowledge bases.",
            "raw_dict",
        ),
        "list_kb_documents": (
            list_kb_documents,
            ListKBDocumentsParams,
            Dict[str, Any],
            "List all available documents/site data in a knowledge base. Returns a list of objects where each has site_URL, title, and description. The AI will decide which documents to use based on the query. Use this to see all available documentation pages in the knowledge base.",
            "raw_dict",
        ),
        "get_document_by_url": (
            get_document_by_url,
            GetDocumentByURLParams,
            Dict[str, Any],
            "Retrieve a specific document from the knowledge base by its exact URL. Returns the complete document with title, description, breadcrumb, and full content. Use this when you know the exact URL of the page you need.",
            "raw_dict",
        ),
        "index_url": (
            index_url_tool,
            IndexUrlParams,
            Dict[str, Any],
            "Index a single URL into the Moveworks MCP knowledge base with metadata (title, description, category, tags, priority). Use this to add external documentation or resources to the knowledge base for quick retrieval.",
            "raw_dict",
        ),
        "index_multiple_urls": (
            index_multiple_urls_tool,
            IndexMultipleUrlsParams,
            Dict[str, Any],
            "Index multiple URLs into the Moveworks MCP knowledge base in batch. Efficiently add multiple external resources at once with their metadata.",
            "raw_dict",
        ),
        "list_indexed_content": (
            list_indexed_content_tool,
            ListIndexedContentParams,
            Dict[str, Any],
            "List all indexed content from the Moveworks MCP knowledge base. Filter by category, search query, and use pagination (limit/offset) to browse indexed URLs.",
            "raw_dict",
        ),
        "remove_indexed_content": (
            remove_indexed_content_tool,
            RemoveIndexedContentParams,
            Dict[str, Any],
            "Remove indexed content from the Moveworks MCP knowledge base by URL or content ID. Use this to clean up outdated or unwanted indexed content.",
            "raw_dict",
        ),
        "refresh_all_indexed_content": (
            refresh_all_indexed_content_tool,
            RefreshAllIndexedContentParams,
            Dict[str, Any],
            "Refresh (re-index) all user-indexed URLs to update their content. Useful when documentation has been updated and you want to refresh all indexed content at once. Use dry_run=true to preview what will be refreshed.",
            "raw_dict",
        ),
    }
    return tool_definitions
