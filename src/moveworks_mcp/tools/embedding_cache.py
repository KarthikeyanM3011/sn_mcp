import json
import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingCache:
    def __init__(self, kb_path: Path):

        self.kb_path = kb_path
        self.embeddings_path = kb_path / "embeddings"
        self.vectors_path = self.embeddings_path / "vectors"
        self.metadata_path = self.embeddings_path / "embeddings.json"

        self.vectors_path.mkdir(parents=True, exist_ok=True)

        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        return {
            "model": "all-MiniLM-L6-v2",
            "dimension": 384,
            "document_count": 0,
            "documents": {} 
        }

    def _save_metadata(self):
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def has_embedding(self, doc_id: str) -> bool:
        return doc_id in self.metadata["documents"]

    def save_embedding(self, doc_id: str, url: str, embedding: np.ndarray):

        vector_file = self.vectors_path / f"{doc_id}.npy"

        np.save(vector_file, embedding)

        self.metadata["documents"][doc_id] = {
            "url": url,
            "vector_file": f"vectors/{doc_id}.npy",
            "shape": list(embedding.shape),
        }
        self.metadata["document_count"] = len(self.metadata["documents"])

        self._save_metadata()

        logger.debug(f"Saved embedding for document {doc_id}")

    def load_embedding(self, doc_id: str) -> Optional[np.ndarray]:

        if doc_id not in self.metadata["documents"]:
            return None

        vector_file = self.vectors_path / f"{doc_id}.npy"

        if not vector_file.exists():
            logger.warning(f"Vector file not found for document {doc_id}")
            return None

        try:
            embedding = np.load(vector_file)
            return embedding
        except Exception as e:
            logger.error(f"Error loading embedding for {doc_id}: {e}")
            return None

    def get_all_document_ids(self):
        return list(self.metadata["documents"].keys())

    def clear(self):
        import shutil
        if self.vectors_path.exists():
            shutil.rmtree(self.vectors_path)
        self.vectors_path.mkdir(parents=True, exist_ok=True)

        self.metadata = {
            "model": "all-MiniLM-L6-v2",
            "dimension": 384,
            "document_count": 0,
            "documents": {}
        }
        self._save_metadata()

        logger.info("Cleared all embeddings")

    def get_stats(self) -> Dict:
        total_size = 0
        for doc_info in self.metadata["documents"].values():
            vector_file = self.embeddings_path / doc_info["vector_file"]
            if vector_file.exists():
                total_size += vector_file.stat().st_size

        return {
            "document_count": self.metadata["document_count"],
            "model": self.metadata["model"],
            "dimension": self.metadata["dimension"],
            "total_size_mb": total_size / (1024 * 1024),
        }


def precompute_embeddings_for_kb(kb_name: str, kb_manager, semantic_engine):
    if not semantic_engine.is_available():
        logger.warning("Semantic search not available, cannot pre-compute embeddings")
        return {
            "success": False,
            "message": "sentence-transformers not installed"
        }

    logger.info(f"Pre-computing embeddings for KB: {kb_name}")

    documents = kb_manager.get_all_documents(kb_name)

    if not documents:
        return {
            "success": False,
            "message": f"No documents found in KB '{kb_name}'"
        }

    kb_path = kb_manager.get_kb_path(kb_name)
    cache = EmbeddingCache(kb_path)

    computed = 0
    skipped = 0

    for doc in documents:
        doc_id = kb_manager._generate_doc_id(doc.url)

        if cache.has_embedding(doc_id):
            skipped += 1
            continue

        doc_text = f"{doc.title} {doc.description} {doc.content[:500]}"
        embedding = semantic_engine.create_embedding(doc_text)

        if embedding is not None:
            cache.save_embedding(doc_id, doc.url, embedding)
            computed += 1

        if computed % 10 == 0:
            logger.info(f"Computed {computed}/{len(documents)} embeddings...")

    stats = cache.get_stats()

    logger.info(f"✓ Pre-computed {computed} embeddings, skipped {skipped}")
    logger.info(f"  Total embeddings: {stats['document_count']}")
    logger.info(f"  Storage size: {stats['total_size_mb']:.2f} MB")

    return {
        "success": True,
        "computed": computed,
        "skipped": skipped,
        "total": stats["document_count"],
        "storage_mb": stats["total_size_mb"],
    }
