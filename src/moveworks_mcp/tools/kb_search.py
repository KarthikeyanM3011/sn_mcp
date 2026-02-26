import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from moveworks_mcp.tools.knowledge_base_manager import CachedDocument, KnowledgeBaseManager

logger = logging.getLogger(__name__)


class TopicExtractor:
    COMPOUND_TERMS = [
        "http action",
        "compound action",
        "decision policy",
        "workflow routing",
        "api authentication",
        "single sign-on",
        "sso",
        "rest api",
        "web hook",
        "webhook",
        "action chaining",
        "error handling",
        "data mapping",
        "integration pattern",
        "user management",
        "access control",
        "rate limiting",
        "api endpoint",
        "http method",
        "request body",
        "response header",
        "status code",
    ]

    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "will", "with", "how", "what", "when", "where", "which",
        "who", "why", "about", "explain", "tell", "me", "can", "you", "do",
        "does", "work", "works", "use", "uses", "used"
    }

    @classmethod
    def extract_topics(cls, query: str) -> List[str]:
        query_lower = query.lower()
        topics = []

        for compound_term in cls.COMPOUND_TERMS:
            if compound_term in query_lower:
                topics.append(compound_term)
                query_lower = query_lower.replace(compound_term, " ")

        cleaned_query = re.sub(r'[^\w\s\-_]', ' ', query_lower)

        words = cleaned_query.split()

        meaningful_words = [
            word for word in words
            if word not in cls.STOP_WORDS and len(word) > 2
        ]

        for i in range(len(meaningful_words)):
            if meaningful_words[i] not in [t for topic in topics for t in topic.split()]:
                topics.append(meaningful_words[i])

            if i < len(meaningful_words) - 1:
                bigram = f"{meaningful_words[i]} {meaningful_words[i + 1]}"
                if bigram not in topics and bigram not in cls.COMPOUND_TERMS:
                    if len(meaningful_words[i]) > 3 and len(meaningful_words[i + 1]) > 3:
                        topics.append(bigram)

        unique_topics = []
        seen = set()
        for topic in topics:
            if topic not in seen:
                unique_topics.append(topic)
                seen.add(topic)

        return unique_topics[:5]


class SemanticSearchEngine:

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. Semantic search will be disabled. "
                "Install with: pip install sentence-transformers"
            )
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None

    def is_available(self) -> bool:
        return self.model is not None

    def create_embedding(self, text: str) -> Optional[np.ndarray]:
        if not self.is_available():
            return None

        try:
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]

            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:

        if embedding1 is None or embedding2 is None:
            return 0.0

        try:
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0

    def search_documents(
        self,
        query: str,
        documents: List[CachedDocument],
        threshold: float = 0.5,
        max_results: Optional[int] = None
    ) -> List[Tuple[CachedDocument, float]]:

        if not self.is_available():
            logger.warning("Semantic search not available, returning empty results")
            return []

        query_embedding = self.create_embedding(query)
        if query_embedding is None:
            return []

        results = []

        for doc in documents:
            doc_text = f"{doc.title} {doc.description} {doc.content[:500]}"
            doc_embedding = self.create_embedding(doc_text)

            if doc_embedding is None:
                continue

            similarity = self.compute_similarity(query_embedding, doc_embedding)

            if similarity >= threshold:
                results.append((doc, similarity))

        results.sort(key=lambda x: x[1], reverse=True)

        if max_results:
            results = results[:max_results]

        return results


class HybridSearchEngine:

    def __init__(self, kb_manager: KnowledgeBaseManager):

        self.kb_manager = kb_manager
        self.topic_extractor = TopicExtractor()
        self.semantic_engine = SemanticSearchEngine()

    def hybrid_search(
        self,
        kb_name: str,
        query: str,
        max_results: int = 10,
        use_semantic: bool = True,
        semantic_threshold: float = 0.5,
    ) -> List[CachedDocument]:

        logger.info(f"Hybrid search for query: '{query}' in KB: '{kb_name}'")

        all_documents = self.kb_manager.get_all_documents(kb_name)

        if not all_documents:
            logger.warning(f"No documents found in KB '{kb_name}'")
            return []

        logger.info("STEP 1: Multi-query search (topic extraction)")
        topics = self.topic_extractor.extract_topics(query)
        logger.info(f"Extracted topics: {topics}")

        multi_query_results = self._multi_query_search(all_documents, topics, max_per_topic=3)
        logger.info(f"Multi-query found {len(multi_query_results)} documents")

        semantic_results = []
        if use_semantic and self.semantic_engine.is_available():
            logger.info("STEP 2: Semantic search")
            semantic_results_with_scores = self.semantic_engine.search_documents(
                query,
                all_documents,
                threshold=semantic_threshold,
                max_results=max_results * 2  
            )
            semantic_results = [doc for doc, score in semantic_results_with_scores]
            logger.info(f"Semantic search found {len(semantic_results)} documents")
        else:
            logger.info("STEP 2: Semantic search skipped (not available or disabled)")

        logger.info("STEP 3: Combining and deduplicating results")
        combined_results = self._combine_and_deduplicate(
            multi_query_results,
            semantic_results
        )

        logger.info("STEP 4: Re-ranking by relevance")
        ranked_results = self._rerank_by_relevance(combined_results, query, topics)

        final_results = ranked_results[:max_results]

        logger.info(f"Final results: {len(final_results)} documents")
        for i, doc in enumerate(final_results[:5], 1):
            logger.info(f"  {i}. {doc.title} (score: {doc.relevance_score:.2f})")

        return final_results

    def _multi_query_search(
        self,
        documents: List[CachedDocument],
        topics: List[str],
        max_per_topic: int = 3
    ) -> List[CachedDocument]:

        results = []

        for topic in topics:
            topic_results = self._keyword_search(documents, topic, max_results=max_per_topic)
            results.extend(topic_results)

        return results

    def _keyword_search(
        self,
        documents: List[CachedDocument],
        query: str,
        max_results: int = 10
    ) -> List[CachedDocument]:

        query_lower = query.lower()
        query_terms = [term for term in query_lower.split() if len(term) > 2]

        scored_documents = []

        for doc in documents:
            score = self._calculate_keyword_score(doc, query_lower, query_terms)
            if score > 0:
                doc_copy = CachedDocument(
                    url=doc.url,
                    title=doc.title,
                    content=doc.content,
                    description=doc.description,
                    breadcrumb=doc.breadcrumb,
                    relevance_score=score,
                    metadata=doc.metadata,
                )
                scored_documents.append(doc_copy)

        scored_documents.sort(key=lambda d: d.relevance_score, reverse=True)

        return scored_documents[:max_results]

    def _calculate_keyword_score(
        self,
        doc: CachedDocument,
        query: str,
        query_terms: List[str]
    ) -> float:
        score = 0.0

        title_lower = doc.title.lower()
        description_lower = doc.description.lower()
        url_lower = doc.url.lower()
        breadcrumb_lower = doc.breadcrumb.lower()

        if query in title_lower:
            score += 100

        for term in query_terms:
            if term in title_lower:
                score += 20

        if query in url_lower:
            score += 15

        for term in query_terms:
            if term in url_lower:
                score += 10

        for term in query_terms:
            if term in description_lower:
                score += 5

        for term in query_terms:
            if term in breadcrumb_lower:
                score += 3

        return score

    def _combine_and_deduplicate(
        self,
        multi_query_results: List[CachedDocument],
        semantic_results: List[CachedDocument]
    ) -> List[CachedDocument]:

        seen_urls: Set[str] = set()
        combined = []

        for doc in multi_query_results:
            if doc.url not in seen_urls:
                combined.append(doc)
                seen_urls.add(doc.url)

        for doc in semantic_results:
            if doc.url not in seen_urls:
                combined.append(doc)
                seen_urls.add(doc.url)

        return combined

    def _rerank_by_relevance(
        self,
        documents: List[CachedDocument],
        query: str,
        topics: List[str]
    ) -> List[CachedDocument]:

        query_lower = query.lower()
        query_terms = [term for term in query_lower.split() if len(term) > 2]

        for doc in documents:
            base_score = self._calculate_keyword_score(doc, query_lower, query_terms)

            topic_matches = 0
            for topic in topics:
                topic_lower = topic.lower()
                if (topic_lower in doc.title.lower() or
                    topic_lower in doc.description.lower() or
                    topic_lower in doc.url.lower()):
                    topic_matches += 1

            topic_bonus = topic_matches * 25

            doc.relevance_score = base_score + topic_bonus

        documents.sort(key=lambda d: d.relevance_score, reverse=True)

        return documents
