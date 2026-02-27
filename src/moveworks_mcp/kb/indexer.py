import hashlib
import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pathlib import Path


DB_PATH = str(Path(__file__).parent.parent / "data" / "chroma_db")
CHUNK_COLLECTION = "mw_chunks"
PAGE_COLLECTION = "mw_pages"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

logger = logging.getLogger(__name__)


class KBIndexer:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.chunks = self.client.get_or_create_collection(
            CHUNK_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        self.pages = self.client.get_or_create_collection(PAGE_COLLECTION)
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)

    # ── existence check ──────────────────────────────────────────────────────

    def page_exists(self, url: str) -> bool:
        """Return True if this URL is already in the page store."""
        result = self.pages.get(ids=[url], include=[])
        return bool(result and result["ids"])

    # ── indexing ─────────────────────────────────────────────────────────────

    def index_page(self, page: dict, force: bool = False) -> str | None:
        """
        Index a single page.

        Returns the URL if the page was indexed, or None if it was skipped
        because it already exists and force=False (default).
        """
        url = page["url"]

        if not force and self.page_exists(url):
            logger.debug("Skipping already-indexed page: %s", url)
            return None

        title = page["title"]
        breadcrumb = page["breadcrumb"]
        content = page["content"]

        enriched_content = f"Navigation: {breadcrumb}\nTitle: {title}\n\n{content}"

        self.pages.upsert(
            ids=[url],
            documents=[enriched_content],
            metadatas=[{
                "url": url,
                "title": title,
                "breadcrumb": breadcrumb,
                "domain": self._extract_domain(url)
            }]
        )

        views = [
            breadcrumb,
            f"{title} - {breadcrumb}",
            enriched_content[:2000]
        ]
        view_labels = ["breadcrumb", "title_path", "full_content"]

        for i, (view_text, label) in enumerate(zip(views, view_labels)):
            if not view_text.strip():
                continue
            chunk_id = hashlib.md5(f"{url}::view::{i}".encode()).hexdigest()
            embedding = self.embedder.encode(view_text).tolist()
            self.chunks.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[view_text],
                metadatas=[{
                    "parent_url": url,
                    "title": title,
                    "breadcrumb": breadcrumb,
                    "view_type": label,
                    "domain": self._extract_domain(url)
                }]
            )

        logger.debug("Indexed page: %s", url)
        return url

    def index_pages(self, pages: dict[str, dict], force: bool = False) -> dict:
        """
        Index multiple pages, skipping any that are already in the store.

        Returns:
            {
                "indexed": [url, ...],   # newly written
                "skipped": [url, ...],   # already existed, not re-written
            }
        """
        indexed: list[str] = []
        skipped: list[str] = []

        for page in pages.values():
            result = self.index_page(page, force=force)
            if result is None:
                skipped.append(page["url"])
            else:
                indexed.append(result)

        if skipped:
            logger.info("index_pages: %d new, %d skipped (already indexed)", len(indexed), len(skipped))

        return {"indexed": indexed, "skipped": skipped}

    # ── removal ──────────────────────────────────────────────────────────────

    def remove_page(self, url: str):
        try:
            self.pages.delete(ids=[url])
        except Exception:
            pass

        existing = self.chunks.get(where={"parent_url": url})
        if existing and existing["ids"]:
            self.chunks.delete(ids=existing["ids"])

    def remove_domain(self, domain: str):
        page_results = self.pages.get(where={"domain": domain})
        if page_results and page_results["ids"]:
            self.pages.delete(ids=page_results["ids"])

        chunk_results = self.chunks.get(where={"domain": domain})
        if chunk_results and chunk_results["ids"]:
            self.chunks.delete(ids=chunk_results["ids"])

    # ── listing / retrieval ──────────────────────────────────────────────────

    def list_pages(self, domain: str = None) -> list[dict]:
        if domain:
            results = self.pages.get(where={"domain": domain}, include=["metadatas"])
        else:
            results = self.pages.get(include=["metadatas"])

        if not results or not results["metadatas"]:
            return []

        return [
            {
                "url": meta["url"],
                "title": meta["title"],
                "breadcrumb": meta["breadcrumb"],
                "domain": meta["domain"]
            }
            for meta in results["metadatas"]
        ]

    def get_full_page(self, url: str) -> str | None:
        result = self.pages.get(ids=[url], include=["documents"])
        if result and result["documents"]:
            return result["documents"][0]
        return None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _extract_domain(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc
