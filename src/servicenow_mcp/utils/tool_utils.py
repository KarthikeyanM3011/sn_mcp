from typing import Any, Callable, Dict, Tuple, Type

from servicenow_mcp.tools.knowledge_base import (
    CreateArticleParams,
    CreateKnowledgeBaseParams,
    GetArticleParams,
    ListArticlesParams,
    ListKnowledgeBasesParams,
    PublishArticleParams,
    UpdateArticleParams,
)
from servicenow_mcp.tools.knowledge_base import (
    CreateCategoryParams as CreateKBCategoryParams,
)
from servicenow_mcp.tools.knowledge_base import (
    ListCategoriesParams as ListKBCategoriesParams,
)
from servicenow_mcp.tools.knowledge_base import (
    create_article as create_article_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    create_knowledge_base as create_knowledge_base_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    get_article as get_article_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    list_articles as list_articles_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    list_knowledge_bases as list_knowledge_bases_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    publish_article as publish_article_tool,
)
from servicenow_mcp.tools.knowledge_base import (
    update_article as update_article_tool,
)

ParamsModel = Type[Any]

ToolDefinition = Tuple[
    Callable,
    ParamsModel,
    Type,
    str,
    str,
]


def get_tool_definitions(
    create_kb_category_tool_impl: Callable, list_kb_categories_tool_impl: Callable
) -> Dict[str, ToolDefinition]:
    tool_definitions: Dict[str, ToolDefinition] = {
        "create_knowledge_base": (
            create_knowledge_base_tool,
            CreateKnowledgeBaseParams,
            str,
            "Create a new knowledge base in ServiceNow",
            "json_dict",
        ),
        "list_knowledge_bases": (
            list_knowledge_bases_tool,
            ListKnowledgeBasesParams,
            Dict[str, Any],
            "List knowledge bases from ServiceNow",
            "raw_dict",
        ),
        "create_category": (
            create_kb_category_tool_impl,
            CreateKBCategoryParams,
            str,
            "Create a new category in a knowledge base",
            "json_dict",
        ),
        "list_categories": (
            list_kb_categories_tool_impl,
            ListKBCategoriesParams,
            Dict[str, Any],
            "List categories in a knowledge base",
            "raw_dict",
        ),
        "create_article": (
            create_article_tool,
            CreateArticleParams,
            str,
            "Create a new knowledge article",
            "json_dict",
        ),
        "update_article": (
            update_article_tool,
            UpdateArticleParams,
            str,
            "Update an existing knowledge article",
            "json_dict",
        ),
        "publish_article": (
            publish_article_tool,
            PublishArticleParams,
            str,
            "Publish a knowledge article",
            "json_dict",
        ),
        "list_articles": (
            list_articles_tool,
            ListArticlesParams,
            Dict[str, Any],
            "List knowledge articles",
            "raw_dict",
        ),
        "get_article": (
            get_article_tool,
            GetArticleParams,
            Dict[str, Any],
            "Get a specific knowledge article by ID",
            "raw_dict",
        ),
    }
    return tool_definitions