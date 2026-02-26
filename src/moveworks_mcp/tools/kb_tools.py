import logging
from typing import Any, Dict

from pydantic import BaseModel, Field

from moveworks_mcp.auth.auth_manager import AuthManager
from moveworks_mcp.tools.docs_crawler import (
    DocumentPage,
    build_sitemap_from_xml,
    build_sitemap_manual,
    fetch_page_content,
    select_relevant_pages,
)
from moveworks_mcp.tools.kb_search import HybridSearchEngine
from moveworks_mcp.tools.knowledge_base_manager import CachedDocument, KnowledgeBaseManager
from moveworks_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class IndexDocumentationParams(BaseModel):
    kb_name: str = Field(..., description="Name of the knowledge base to create or update")
    source_url: str = Field(
        default="https://help.moveworks.com/docs",
        description="Base URL of the documentation site to index"
    )
    description: str = Field(
        default="",
        description="Description of the knowledge base"
    )
    use_sitemap: bool = Field(
        default=True,
        description="Use sitemap.xml for faster discovery (default: True)"
    )
    max_pages: int = Field(
        default=50,
        description="Maximum number of pages to index (default: 50)"
    )
    force_refresh: bool = Field(
        default=False,
        description="Force re-indexing even if KB already exists (default: False)"
    )


class SearchKnowledgeBaseParams(BaseModel):
    """Parameters for searching a knowledge base."""

    query: str = Field(..., description="The question or topic to search for")
    kb_name: str = Field(
        default="moveworks_docs",
        description="Name of the knowledge base to search (default: moveworks_docs)"
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return (default: 10)"
    )
    use_semantic: bool = Field(
        default=True,
        description="Use semantic search with embeddings (default: True, requires sentence-transformers)"
    )
    return_format: str = Field(
        default="aggregated",
        description="Return format: 'aggregated' (combined content) or 'structured' (list of pages)"
    )


class ListKnowledgeBasesParams(BaseModel):
    pass  


class DeleteKnowledgeBaseParams(BaseModel):
    kb_name: str = Field(..., description="Name of the knowledge base to delete")


class ListKBDocumentsParams(BaseModel):
    kb_name: str = Field(
        default="moveworks_docs",
        description="Name of the knowledge base to list documents from"
    )


class GetDocumentByURLParams(BaseModel):
    url: str = Field(..., description="The exact URL of the document to retrieve")
    kb_name: str = Field(
        default="moveworks_docs",
        description="Name of the knowledge base to search in"
    )


_kb_manager = None


def get_kb_manager() -> KnowledgeBaseManager:
    """Get or create the global knowledge base manager instance."""
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager


def index_documentation(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: IndexDocumentationParams
) -> Dict[str, Any]:

    try:
        logger.info(f"=" * 80)
        logger.info(f"INDEXING DOCUMENTATION: {params.source_url}")
        logger.info(f"Knowledge Base: {params.kb_name}")
        logger.info(f"=" * 80)

        kb_manager = get_kb_manager()

        # Check if KB exists
        if kb_manager.kb_exists(params.kb_name):
            if not params.force_refresh:
                logger.info(f"Knowledge base '{params.kb_name}' already exists")
                stats = kb_manager.get_kb_stats(params.kb_name)
                return {
                    "success": True,
                    "message": f"Knowledge base '{params.kb_name}' already exists. Use force_refresh=true to re-index.",
                    "kb_name": params.kb_name,
                    "stats": stats,
                }
            else:
                logger.info(f"Force refresh enabled. Deleting existing KB '{params.kb_name}'")
                kb_manager.delete_kb(params.kb_name)

        logger.info(f"Creating knowledge base '{params.kb_name}'")
        kb_config = {
            "kb_name": params.kb_name,
            "description": params.description,
            "source_url": params.source_url,
        }
        kb_manager.create_kb(params.kb_name, config=kb_config)

        logger.info("Step 1: Building sitemap...")
        if params.use_sitemap:
            sitemap_url = f"{params.source_url.rstrip('/')}/sitemap.xml"
            if "help.moveworks.com" in params.source_url:
                sitemap_url = "https://help.moveworks.com/sitemap.xml"
            sitemap = build_sitemap_from_xml(sitemap_url, config.timeout)
        else:
            sitemap = build_sitemap_manual(
                base_url=params.source_url,
                max_depth=3,
                timeout=config.timeout
            )

        if not sitemap:
            return {
                "success": False,
                "message": "Failed to build documentation sitemap",
                "kb_name": params.kb_name,
            }

        logger.info(f"Discovered {len(sitemap)} pages")

        logger.info(f"Step 2: Selecting up to {params.max_pages} pages to index...")
        pages_list = list(sitemap.values())[:params.max_pages]

        logger.info(f"Step 3: Fetching content for {len(pages_list)} pages...")
        pages_with_content = fetch_page_content(pages_list, config.timeout)

        logger.info(f"Step 4: Indexing documents into KB '{params.kb_name}'...")
        indexed_count = 0
        for page in pages_with_content:
            if not page.content:
                continue

            cached_doc = CachedDocument(
                url=page.url,
                title=page.title,
                content=page.content,
                description=page.description,
                breadcrumb=page.breadcrumb,
            )

            kb_manager.add_document(params.kb_name, cached_doc)
            indexed_count += 1

        stats = kb_manager.get_kb_stats(params.kb_name)

        logger.info(f"Successfully indexed {indexed_count} documents")
        logger.info(f"Total content: {stats['total_content_chars']} characters")

        return {
            "success": True,
            "message": f"Successfully indexed {indexed_count} documents into knowledge base '{params.kb_name}'",
            "kb_name": params.kb_name,
            "indexed_count": indexed_count,
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Error indexing documentation: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "kb_name": params.kb_name,
        }


def search_knowledge_base(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: SearchKnowledgeBaseParams
) -> Dict[str, Any]:

    try:
        logger.info(f"=" * 80)
        logger.info(f"SEARCHING KNOWLEDGE BASE: {params.kb_name}")
        logger.info(f"Query: {params.query}")
        logger.info(f"=" * 80)

        kb_manager = get_kb_manager()

        if not kb_manager.kb_exists(params.kb_name):
            available_kbs = kb_manager.list_knowledge_bases()
            kb_names = [kb["kb_name"] for kb in available_kbs]
            return {
                "success": False,
                "message": f"Knowledge base '{params.kb_name}' not found. Available KBs: {kb_names}",
                "query": params.query,
                "available_knowledge_bases": kb_names,
            }

        search_engine = HybridSearchEngine(kb_manager)
        results = search_engine.hybrid_search(
            kb_name=params.kb_name,
            query=params.query,
            max_results=params.max_results,
            use_semantic=params.use_semantic,
        )

        if not results:
            return {
                "success": True,
                "message": "No relevant documents found",
                "query": params.query,
                "kb_name": params.kb_name,
                "results_count": 0,
                "results": [],
            }

        if params.return_format == "aggregated":
            all_content_parts = []
            for doc in results:
                all_content_parts.append(f"\n\n{'=' * 80}\n")
                all_content_parts.append(f"SOURCE: {doc.title}\n")
                all_content_parts.append(f"URL: {doc.url}\n")
                if doc.breadcrumb:
                    all_content_parts.append(f"PATH: {doc.breadcrumb}\n")
                all_content_parts.append(f"RELEVANCE: {doc.relevance_score:.1f}\n")
                all_content_parts.append(f"{'=' * 80}\n\n")
                all_content_parts.append(doc.content)

            aggregated_content = ''.join(all_content_parts)

            return {
                "success": True,
                "message": f"Found {len(results)} relevant documents",
                "query": params.query,
                "kb_name": params.kb_name,
                "results_count": len(results),
                "aggregated_content": aggregated_content,
                "pages": [
                    {
                        "title": doc.title,
                        "url": doc.url,
                        "description": doc.description,
                        "breadcrumb": doc.breadcrumb,
                        "relevance_score": doc.relevance_score,
                    }
                    for doc in results
                ],
            }
        else:
            return {
                "success": True,
                "message": f"Found {len(results)} relevant documents",
                "query": params.query,
                "kb_name": params.kb_name,
                "results_count": len(results),
                "results": [
                    {
                        "title": doc.title,
                        "url": doc.url,
                        "description": doc.description,
                        "breadcrumb": doc.breadcrumb,
                        "content": doc.content,
                        "relevance_score": doc.relevance_score,
                    }
                    for doc in results
                ],
            }

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "query": params.query,
            "kb_name": params.kb_name,
        }


def list_knowledge_bases(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListKnowledgeBasesParams
) -> Dict[str, Any]:

    try:
        kb_manager = get_kb_manager()
        kb_list = kb_manager.list_knowledge_bases()

        return {
            "success": True,
            "message": f"Found {len(kb_list)} knowledge bases",
            "count": len(kb_list),
            "knowledge_bases": kb_list,
        }

    except Exception as e:
        logger.error(f"Error listing knowledge bases: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "knowledge_bases": [],
        }


def delete_knowledge_base(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: DeleteKnowledgeBaseParams
) -> Dict[str, Any]:

    try:
        kb_manager = get_kb_manager()

        if not kb_manager.kb_exists(params.kb_name):
            return {
                "success": False,
                "message": f"Knowledge base '{params.kb_name}' not found",
                "kb_name": params.kb_name,
            }

        kb_manager.delete_kb(params.kb_name)

        return {
            "success": True,
            "message": f"Knowledge base '{params.kb_name}' deleted successfully",
            "kb_name": params.kb_name,
        }

    except Exception as e:
        logger.error(f"Error deleting knowledge base: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "kb_name": params.kb_name,
        }


def list_kb_documents(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListKBDocumentsParams
) -> Dict[str, Any]:

    try:
        kb_manager = get_kb_manager()

        if not kb_manager.kb_exists(params.kb_name):
            available_kbs = kb_manager.list_knowledge_bases()
            kb_names = [kb["kb_name"] for kb in available_kbs]
            return {
                "success": False,
                "message": f"Knowledge base '{params.kb_name}' not found",
                "available_knowledge_bases": kb_names,
            }

        documents = kb_manager.get_all_documents(params.kb_name)

        doc_list = []
        for doc in documents:
            doc_info = {
                "site_URL": doc.url,
                "title": doc.title,
                "description": doc.description,
            }
            doc_list.append(doc_info)

        return {
            "success": True,
            "message": f"Found {len(doc_list)} documents in '{params.kb_name}'",
            "kb_name": params.kb_name,
            "document_count": len(doc_list),
            "documents": doc_list,
        }

    except Exception as e:
        logger.error(f"Error listing KB documents: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "kb_name": params.kb_name,
        }


def get_document_by_url(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetDocumentByURLParams
) -> Dict[str, Any]:
    try:
        kb_manager = get_kb_manager()

        if not kb_manager.kb_exists(params.kb_name):
            available_kbs = kb_manager.list_knowledge_bases()
            kb_names = [kb["kb_name"] for kb in available_kbs]
            return {
                "success": False,
                "message": f"Knowledge base '{params.kb_name}' not found",
                "available_knowledge_bases": kb_names,
            }

        document = kb_manager.get_document(params.kb_name, params.url)

        if not document:
            return {
                "success": False,
                "message": f"Document with URL '{params.url}' not found in KB '{params.kb_name}'",
                "url": params.url,
                "kb_name": params.kb_name,
            }

        return {
            "success": True,
            "message": f"Found document: {document.title}",
            "url": document.url,
            "title": document.title,
            "description": document.description,
            "breadcrumb": document.breadcrumb,
            "content": document.content,
            "content_length": len(document.content),
        }

    except Exception as e:
        logger.error(f"Error retrieving document by URL: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "url": params.url,
            "kb_name": params.kb_name,
        }
