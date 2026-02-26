import logging
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from moveworks_mcp.auth.auth_manager import AuthManager
from moveworks_mcp.utils.config import ServerConfig
from moveworks_mcp.tools.knowledge_base_manager import KnowledgeBaseManager, CachedDocument

logger = logging.getLogger(__name__)

DEFAULT_KB_NAME = "moveworks_docs"


class IndexUrlParams(BaseModel):

    url: str = Field(..., description="URL to index into the knowledge base")
    title: Optional[str] = Field(None, description="Optional title for the indexed content")
    description: Optional[str] = Field(None, description="Optional description for the indexed content")
    category: Optional[str] = Field(None, description="Optional category for organizing the indexed content")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags for the indexed content")
    priority: Optional[int] = Field(default=5, description="Priority level (1-10, default 5)")
    force_reindex: bool = Field(default=False, description="Force re-indexing even if URL already exists (updates existing document)")


class IndexMultipleUrlsParams(BaseModel):
    urls: List[Dict[str, Any]] = Field(
        ...,
        description="List of URLs with metadata. Each item should have 'url' and optionally 'title', 'description', 'category', 'tags', 'priority', 'force_reindex'"
    )
    force_reindex_all: bool = Field(default=False, description="Force re-index all URLs even if they exist (overrides individual force_reindex)")


class ListIndexedContentParams(BaseModel):

    category: Optional[str] = Field(None, description="Filter by category")
    limit: Optional[int] = Field(default=50, description="Maximum number of results to return")
    offset: Optional[int] = Field(default=0, description="Offset for pagination")
    search_query: Optional[str] = Field(None, description="Optional search query to filter results")


class RemoveIndexedContentParams(BaseModel):

    url: Optional[str] = Field(None, description="URL to remove from the index")
    content_id: Optional[str] = Field(None, description="Content ID to remove from the index")


class RefreshAllIndexedContentParams(BaseModel):

    dry_run: bool = Field(default=False, description="If true, only show what would be refreshed without actually updating")


def index_url(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: IndexUrlParams
) -> Dict[str, Any]:
    try:
        kb_manager = KnowledgeBaseManager()

        if not kb_manager.kb_exists(DEFAULT_KB_NAME):
            kb_manager.create_kb(
                DEFAULT_KB_NAME,
                config={
                    "kb_name": DEFAULT_KB_NAME,
                    "description": "Moveworks documentation and user-indexed content",
                    "source_url": "https://help.moveworks.com/docs",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            logger.info(f"Created knowledge base '{DEFAULT_KB_NAME}'")

        existing_doc = kb_manager.get_document(DEFAULT_KB_NAME, params.url)
        if existing_doc and not params.force_reindex:
            logger.info(f"Document already exists for URL: {params.url}, skipping re-index (use force_reindex=true to update)")
            content_id = hashlib.md5(params.url.encode('utf-8')).hexdigest()
            return {
                "success": True,
                "message": f"URL already indexed: {params.url} (skipped re-indexing, use force_reindex=true to update)",
                "content_id": content_id,
                "already_indexed": True,
                "reindexed": False,
                "indexed_content": {
                    "url": existing_doc.url,
                    "title": existing_doc.title,
                    "description": existing_doc.description,
                    **existing_doc.metadata
                }
            }
        elif existing_doc and params.force_reindex:
            logger.info(f"Force re-indexing document for URL: {params.url}")
            is_reindex = True
        else:
            is_reindex = False

        title = params.title or params.url
        description = params.description or f"User-indexed content from {params.url}"

        metadata = {
            "category": params.category or "external",
            "tags": params.tags or [],
            "priority": params.priority or 5,
            "source": "user_indexed",  
            "indexed_at": datetime.utcnow().isoformat(),
        }

        content = f"# {title}\n\n{description}\n\n**Source:** {params.url}\n\n**Category:** {metadata['category']}\n**Tags:** {', '.join(metadata['tags'])}\n**Priority:** {metadata['priority']}\n\nThis is a user-indexed reference link. Use this URL for more detailed information."

        breadcrumb = f"User Indexed / {metadata['category']}"

        document = CachedDocument(
            url=params.url,
            title=title,
            content=content,
            description=description,
            breadcrumb=breadcrumb,
            metadata=metadata
        )

        kb_manager.add_document(DEFAULT_KB_NAME, document)

        content_id = hashlib.md5(params.url.encode('utf-8')).hexdigest()

        action = "Re-indexed" if is_reindex else "Indexed"
        logger.info(f"Successfully {action.lower()} URL: {params.url} with ID: {content_id} into '{DEFAULT_KB_NAME}' KB")

        return {
            "success": True,
            "message": f"Successfully {action.lower()} URL: {params.url} into '{DEFAULT_KB_NAME}' knowledge base",
            "content_id": content_id,
            "kb_name": DEFAULT_KB_NAME,
            "already_indexed": is_reindex,
            "reindexed": is_reindex,
            "indexed_content": {
                "url": params.url,
                "title": title,
                "description": description,
                **metadata
            }
        }

    except Exception as e:
        logger.error(f"Error indexing URL {params.url}: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Failed to index URL: {str(e)}",
            "error": str(e)
        }


def index_multiple_urls(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: IndexMultipleUrlsParams
) -> Dict[str, Any]:

    results = []
    successful_count = 0
    failed_count = 0
    reindexed_count = 0

    for url_data in params.urls:
        try:
            force_reindex = params.force_reindex_all or url_data.get("force_reindex", False)

            index_params = IndexUrlParams(
                url=url_data.get("url"),
                title=url_data.get("title"),
                description=url_data.get("description"),
                category=url_data.get("category"),
                tags=url_data.get("tags", []),
                priority=url_data.get("priority", 5),
                force_reindex=force_reindex
            )

            result = index_url(config, auth_manager, index_params)
            results.append({
                "url": url_data.get("url"),
                "result": result
            })

            if result.get("success"):
                successful_count += 1
                if result.get("reindexed"):
                    reindexed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Error indexing URL {url_data.get('url')}: {e}")
            results.append({
                "url": url_data.get("url"),
                "result": {
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "error": str(e)
                }
            })
            failed_count += 1

    return {
        "success": failed_count == 0,
        "message": f"Processed {len(params.urls)} URLs: {successful_count} successful ({reindexed_count} re-indexed), {failed_count} failed",
        "total": len(params.urls),
        "successful": successful_count,
        "reindexed": reindexed_count,
        "failed": failed_count,
        "results": results
    }


def list_indexed_content(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListIndexedContentParams
) -> Dict[str, Any]:

    try:
        kb_manager = KnowledgeBaseManager()

        if not kb_manager.kb_exists(DEFAULT_KB_NAME):
            return {
                "success": True,
                "message": "No indexed content yet - knowledge base not created",
                "count": 0,
                "content": []
            }

        all_documents = kb_manager.get_all_documents(DEFAULT_KB_NAME)

        all_content = []
        for doc in all_documents:
            if doc.metadata.get("source") == "user_indexed":
                content_item = {
                    "url": doc.url,
                    "title": doc.title,
                    "description": doc.description,
                    "breadcrumb": doc.breadcrumb,
                    "content_hash": doc.content_hash,
                    **doc.metadata
                }
                all_content.append(content_item)

        if params.category:
            all_content = [
                content for content in all_content
                if content.get("category", "").lower() == params.category.lower()
            ]

        if params.search_query:
            search_lower = params.search_query.lower()
            all_content = [
                content for content in all_content
                if search_lower in content.get("title", "").lower()
                or search_lower in content.get("description", "").lower()
                or search_lower in content.get("url", "").lower()
            ]

        total_count = len(all_content)
        start_idx = params.offset
        end_idx = start_idx + params.limit
        paginated_content = all_content[start_idx:end_idx]

        logger.info(f"Retrieved {len(paginated_content)} user-indexed content items (total: {total_count})")

        return {
            "success": True,
            "message": f"Retrieved {len(paginated_content)} user-indexed content items from '{DEFAULT_KB_NAME}' KB",
            "count": len(paginated_content),
            "total_count": total_count,
            "offset": params.offset,
            "limit": params.limit,
            "kb_name": DEFAULT_KB_NAME,
            "content": paginated_content
        }

    except Exception as e:
        logger.error(f"Error listing indexed content: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }


def remove_indexed_content(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: RemoveIndexedContentParams
) -> Dict[str, Any]:
    try:
        if not params.url and not params.content_id:
            return {
                "success": False,
                "message": "Either 'url' or 'content_id' must be provided",
                "error": "Missing required parameter"
            }

        kb_manager = KnowledgeBaseManager()

        if not kb_manager.kb_exists(DEFAULT_KB_NAME):
            return {
                "success": False,
                "message": "No indexed content found - knowledge base does not exist",
                "error": "Knowledge base does not exist"
            }

        url_to_remove = params.url
        if params.content_id and not params.url:
            all_documents = kb_manager.get_all_documents(DEFAULT_KB_NAME)
            for doc in all_documents:
                doc_id = hashlib.md5(doc.url.encode('utf-8')).hexdigest()
                if doc_id == params.content_id:
                    url_to_remove = doc.url
                    break

            if not url_to_remove:
                return {
                    "success": False,
                    "message": f"No indexed content found with content_id: {params.content_id}",
                    "error": "Content not found"
                }

        document = kb_manager.get_document(DEFAULT_KB_NAME, url_to_remove)
        if not document:
            return {
                "success": False,
                "message": f"No indexed content found with URL: {url_to_remove}",
                "error": "Content not found"
            }

        if document.metadata.get("source") != "user_indexed":
            return {
                "success": False,
                "message": f"Cannot remove document: {url_to_remove} - Only user-indexed content can be removed",
                "error": "Cannot remove crawled documentation"
            }

        kb_path = kb_manager.get_kb_path(DEFAULT_KB_NAME)
        index = kb_manager._load_json(kb_path / "index.json")

        if url_to_remove in index["documents"]:
            doc_id = index["documents"][url_to_remove]["doc_id"]
            doc_path = kb_path / "docs" / f"{doc_id}.json"
            if doc_path.exists():
                doc_path.unlink()

            del index["documents"][url_to_remove]
            index["document_count"] -= 1
            index["updated_at"] = datetime.utcnow().isoformat()

            kb_manager._save_json(kb_path / "index.json", index)

            identifier = params.content_id or url_to_remove
            logger.info(f"Successfully removed user-indexed content: {identifier} from '{DEFAULT_KB_NAME}' KB")
            return {
                "success": True,
                "message": f"Successfully removed indexed content: {url_to_remove} from '{DEFAULT_KB_NAME}' KB",
                "removed_url": url_to_remove,
                "removed_identifier": identifier,
                "kb_name": DEFAULT_KB_NAME
            }
        else:
            return {
                "success": False,
                "message": f"Document not found in index: {url_to_remove}",
                "error": "Content not found in index"
            }

    except Exception as e:
        logger.error(f"Error removing indexed content: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }


def refresh_all_indexed_content(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: RefreshAllIndexedContentParams
) -> Dict[str, Any]:

    try:
        kb_manager = KnowledgeBaseManager()

        if not kb_manager.kb_exists(DEFAULT_KB_NAME):
            return {
                "success": False,
                "message": "No knowledge base found - nothing to refresh",
                "error": "Knowledge base does not exist"
            }

        all_documents = kb_manager.get_all_documents(DEFAULT_KB_NAME)
        user_indexed_docs = [
            doc for doc in all_documents
            if doc.metadata.get("source") == "user_indexed"
        ]

        if not user_indexed_docs:
            return {
                "success": True,
                "message": "No user-indexed content found to refresh",
                "total_indexed_urls": 0,
                "refreshed": 0,
                "urls": []
            }

        urls_to_refresh = []
        for doc in user_indexed_docs:
            url_data = {
                "url": doc.url,
                "title": doc.title,
                "description": doc.description,
                "category": doc.metadata.get("category", "external"),
                "tags": doc.metadata.get("tags", []),
                "priority": doc.metadata.get("priority", 5),
                "force_reindex": True  
            }
            urls_to_refresh.append(url_data)

        if params.dry_run:
            logger.info(f"DRY RUN: Would refresh {len(urls_to_refresh)} user-indexed URLs")
            return {
                "success": True,
                "message": f"DRY RUN: Would refresh {len(urls_to_refresh)} user-indexed URLs",
                "dry_run": True,
                "total_indexed_urls": len(urls_to_refresh),
                "urls_to_refresh": [{"url": u["url"], "title": u["title"]} for u in urls_to_refresh]
            }

        logger.info(f"Refreshing {len(urls_to_refresh)} user-indexed URLs...")
        
        refresh_params = IndexMultipleUrlsParams(
            urls=urls_to_refresh,
            force_reindex_all=True
        )
        
        result = index_multiple_urls(config, auth_manager, refresh_params)

        return {
            "success": result.get("success", False),
            "message": f"Refreshed all user-indexed content: {result.get('message')}",
            "dry_run": False,
            "total_indexed_urls": len(urls_to_refresh),
            "refreshed": result.get("reindexed", 0),
            "successful": result.get("successful", 0),
            "failed": result.get("failed", 0),
            "details": result
        }

    except Exception as e:
        logger.error(f"Error refreshing all indexed content: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "error": str(e)
        }
