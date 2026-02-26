import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DocumentMetadata:

    def __init__(
        self,
        url: str,
        title: str,
        description: str = "",
        breadcrumb: str = "",
        content_hash: str = "",
        indexed_at: str = "",
    ):
        self.url = url
        self.title = title
        self.description = description
        self.breadcrumb = breadcrumb
        self.content_hash = content_hash
        self.indexed_at = indexed_at or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "breadcrumb": self.breadcrumb,
            "content_hash": self.content_hash,
            "indexed_at": self.indexed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMetadata":
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            breadcrumb=data.get("breadcrumb", ""),
            content_hash=data.get("content_hash", ""),
            indexed_at=data.get("indexed_at", ""),
        )


class CachedDocument:

    def __init__(
        self,
        url: str,
        title: str,
        content: str,
        description: str = "",
        breadcrumb: str = "",
        relevance_score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.title = title
        self.content = content
        self.description = description
        self.breadcrumb = breadcrumb
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
        self.content_hash = self._compute_content_hash()

    def _compute_content_hash(self) -> str:
        content_bytes = self.content.encode('utf-8')
        return hashlib.sha256(content_bytes).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "description": self.description,
            "breadcrumb": self.breadcrumb,
            "relevance_score": self.relevance_score,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CachedDocument":
        doc = cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            description=data.get("description", ""),
            breadcrumb=data.get("breadcrumb", ""),
            relevance_score=data.get("relevance_score", 0.0),
            metadata=data.get("metadata", {}),
        )
        return doc


class KnowledgeBaseManager:
    def __init__(self, base_path: Optional[str] = None):

        if base_path is None:
            base_path = os.path.expanduser("~/.moveworks_mcp/knowledge_base")

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Knowledge base manager initialized at: {self.base_path}")

    def get_kb_path(self, kb_name: str) -> Path:
        return self.base_path / kb_name

    def kb_exists(self, kb_name: str) -> bool:
        kb_path = self.get_kb_path(kb_name)
        return kb_path.exists() and (kb_path / "index.json").exists()

    def create_kb(self, kb_name: str, config: Optional[Dict[str, Any]] = None) -> bool:

        kb_path = self.get_kb_path(kb_name)

        if self.kb_exists(kb_name):
            logger.warning(f"Knowledge base '{kb_name}' already exists")
            return False

        kb_path.mkdir(parents=True, exist_ok=True)
        (kb_path / "docs").mkdir(exist_ok=True)
        (kb_path / "embeddings").mkdir(exist_ok=True)

        index = {
            "kb_name": kb_name,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "document_count": 0,
            "documents": {},  
        }
        self._save_json(kb_path / "index.json", index)

        if config is None:
            config = {
                "kb_name": kb_name,
                "description": "",
                "source_url": "",
                "created_at": datetime.utcnow().isoformat(),
            }
        self._save_json(kb_path / "config.json", config)

        logger.info(f"Created knowledge base '{kb_name}' at {kb_path}")
        return True

    def add_document(self, kb_name: str, document: CachedDocument) -> bool:

        if not self.kb_exists(kb_name):
            raise ValueError(f"Knowledge base '{kb_name}' does not exist")

        kb_path = self.get_kb_path(kb_name)
        index = self._load_json(kb_path / "index.json")

        doc_id = self._generate_doc_id(document.url)

        doc_path = kb_path / "docs" / f"{doc_id}.json"
        self._save_json(doc_path, document.to_dict())

        if document.url not in index["documents"]:
            index["document_count"] += 1

        index["documents"][document.url] = {
            "doc_id": doc_id,
            "title": document.title,
            "description": document.description,
            "breadcrumb": document.breadcrumb,
            "content_hash": document.content_hash,
            "indexed_at": datetime.utcnow().isoformat(),
        }
        index["updated_at"] = datetime.utcnow().isoformat()

        self._save_json(kb_path / "index.json", index)
        logger.debug(f"Added document '{document.title}' to KB '{kb_name}'")

        return True

    def get_document(self, kb_name: str, url: str) -> Optional[CachedDocument]:

        if not self.kb_exists(kb_name):
            return None

        kb_path = self.get_kb_path(kb_name)
        index = self._load_json(kb_path / "index.json")

        if url not in index["documents"]:
            return None

        doc_id = index["documents"][url]["doc_id"]
        doc_path = kb_path / "docs" / f"{doc_id}.json"

        if not doc_path.exists():
            logger.warning(f"Document file not found: {doc_path}")
            return None

        doc_data = self._load_json(doc_path)
        return CachedDocument.from_dict(doc_data)

    def get_all_documents(self, kb_name: str) -> List[CachedDocument]:

        if not self.kb_exists(kb_name):
            return []

        kb_path = self.get_kb_path(kb_name)
        index = self._load_json(kb_path / "index.json")

        documents = []
        for url, doc_info in index["documents"].items():
            doc = self.get_document(kb_name, url)
            if doc:
                documents.append(doc)

        return documents

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:

        kb_list = []

        for kb_dir in self.base_path.iterdir():
            if kb_dir.is_dir() and (kb_dir / "index.json").exists():
                index = self._load_json(kb_dir / "index.json")
                config = self._load_json(kb_dir / "config.json")

                kb_list.append({
                    "kb_name": index.get("kb_name", kb_dir.name),
                    "description": config.get("description", ""),
                    "document_count": index.get("document_count", 0),
                    "created_at": index.get("created_at", ""),
                    "updated_at": index.get("updated_at", ""),
                    "source_url": config.get("source_url", ""),
                })

        return kb_list

    def delete_kb(self, kb_name: str) -> bool:

        kb_path = self.get_kb_path(kb_name)

        if not self.kb_exists(kb_name):
            logger.warning(f"Knowledge base '{kb_name}' does not exist")
            return False

        import shutil
        shutil.rmtree(kb_path)
        logger.info(f"Deleted knowledge base '{kb_name}'")
        return True

    def get_kb_stats(self, kb_name: str) -> Optional[Dict[str, Any]]:

        if not self.kb_exists(kb_name):
            return None

        kb_path = self.get_kb_path(kb_name)
        index = self._load_json(kb_path / "index.json")
        config = self._load_json(kb_path / "config.json")

        total_content_length = 0
        for url in index["documents"].keys():
            doc = self.get_document(kb_name, url)
            if doc:
                total_content_length += len(doc.content)

        return {
            "kb_name": kb_name,
            "description": config.get("description", ""),
            "document_count": index.get("document_count", 0),
            "total_content_chars": total_content_length,
            "created_at": index.get("created_at", ""),
            "updated_at": index.get("updated_at", ""),
            "source_url": config.get("source_url", ""),
        }

    @staticmethod
    def _generate_doc_id(url: str) -> str:
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    @staticmethod
    def _save_json(path: Path, data: Any) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _load_json(path: Path) -> Any:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
