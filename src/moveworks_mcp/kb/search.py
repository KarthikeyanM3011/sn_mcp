from rank_bm25 import BM25Okapi
from moveworks_mcp.kb.indexer import KBIndexer


class KBSearch:
    def __init__(self):
        self.indexer = KBIndexer()

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        embedding = self.indexer.embedder.encode(query).tolist()

        chunk_results = self.indexer.chunks.query(
            query_embeddings=[embedding],
            n_results=min(top_k * 4, 40),
            include=["metadatas", "distances", "documents"]
        )

        url_scores: dict[str, float] = {}
        url_meta: dict[str, dict] = {}

        if chunk_results and chunk_results["metadatas"]:
            for meta, dist in zip(chunk_results["metadatas"][0], chunk_results["distances"][0]):
                url = meta["parent_url"]
                score = 1.0 - dist
                if url not in url_scores or score > url_scores[url]:
                    url_scores[url] = score
                    url_meta[url] = meta

        bm25_scores = self._bm25_search(query, url_scores.keys())
        for url, bm25_score in bm25_scores.items():
            if url in url_scores:
                url_scores[url] = url_scores[url] * 0.7 + bm25_score * 0.3
            else:
                url_scores[url] = bm25_score * 0.3

        ranked_urls = sorted(url_scores.keys(), key=lambda u: url_scores[u], reverse=True)[:top_k]

        results = []
        for url in ranked_urls:
            full_content = self.indexer.get_full_page(url)
            if not full_content:
                continue
            meta = url_meta.get(url, {})
            results.append({
                "url": url,
                "title": meta.get("title", ""),
                "breadcrumb": meta.get("breadcrumb", ""),
                "score": round(url_scores[url], 4),
                "content": full_content
            })

        return results

    def _bm25_search(self, query: str, candidate_urls) -> dict[str, float]:
        candidate_urls = list(candidate_urls)
        if not candidate_urls:
            return {}

        docs = []
        for url in candidate_urls:
            content = self.indexer.get_full_page(url) or ""
            docs.append(content.lower().split())

        if not docs:
            return {}

        bm25 = BM25Okapi(docs)
        scores = bm25.get_scores(query.lower().split())
        max_score = max(scores) if max(scores) > 0 else 1.0

        return {
            url: float(score / max_score)
            for url, score in zip(candidate_urls, scores)
            if score > 0
        }
