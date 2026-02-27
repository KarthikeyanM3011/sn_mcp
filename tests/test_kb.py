"""
Live integration test for the moveworks_mcp KB.

Steps
-----
1. Crawl & index 4 real help.moveworks.com pages
2. Index the same 4 pages again — all must be skipped (dedup check)
3. Search  "compound actions"
4. Search  "script actions"
5. Remove  all 4 indexed pages and verify cleanup

Run:
    python3 tests/test_kb.py
"""
import sys
import asyncio
import logging
from pathlib import Path

# ── make moveworks_mcp importable when running directly ──────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from moveworks_mcp.kb.crawler import DocCrawler
from moveworks_mcp.kb.indexer import KBIndexer
from moveworks_mcp.kb.search import KBSearch

# ── logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,          # silence noisy third-party libs
    format="%(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("kb_test")
log.setLevel(logging.DEBUG)
# Show crawler warnings (fetch errors, HTTP status problems) in output
logging.getLogger("moveworks_mcp.kb.crawler").setLevel(logging.WARNING)

# ── URLs to index ─────────────────────────────────────────────────────────────
URLS = [
    "https://help.moveworks.com/docs/switch",
    "https://help.moveworks.com/docs/action",
    "https://help.moveworks.com/docs/compound-actions",
    "https://help.moveworks.com/docs/python-reference",
]
DOMAIN = "help.moveworks.com"

DIVIDER = "─" * 70


def banner(text: str):
    print(f"\n{DIVIDER}")
    print(f"  {text}")
    print(DIVIDER)


def check(condition: bool, msg: str):
    status = "✓ PASS" if condition else "✗ FAIL"
    print(f"  {status}  {msg}")
    if not condition:
        sys.exit(1)


# ── Step 1 — First index (all new) ───────────────────────────────────────────
async def step_index_first(indexer: KBIndexer) -> dict[str, dict]:
    banner("STEP 1 — Crawl & Index (first run — all new)")
    crawler = DocCrawler(base_url=f"https://{DOMAIN}")

    print(f"  Crawling {len(URLS)} pages …")
    pages = await crawler.crawl_multiple(URLS)

    print(f"  Fetched  : {len(pages)} / {len(URLS)} pages")
    for url, page in pages.items():
        print(f"    • [{page['title'][:55]}]  {url}")
        print(f"      breadcrumb : {page['breadcrumb']}")
        print(f"      content    : {len(page['content'])} chars")

    print("\n  Indexing into ChromaDB …")
    result = indexer.index_pages(pages)
    print(f"  Indexed  : {len(result['indexed'])} pages")
    print(f"  Skipped  : {len(result['skipped'])} pages (already existed)")

    for url in URLS:
        stored = indexer.get_full_page(url) is not None
        print(f"    {'✓' if stored else '✗'} {url}")

    check(len(result["indexed"]) == len(pages), "All fetched pages were indexed on first run")
    check(len(result["skipped"]) == 0, "No pages skipped on first run")
    return pages


# ── Step 2 — Second index (all duplicates) ───────────────────────────────────
async def step_index_dedup(indexer: KBIndexer, pages: dict[str, dict]):
    banner("STEP 2 — Re-index same pages (dedup check — all must be skipped)")

    result = indexer.index_pages(pages)
    print(f"  Indexed  : {len(result['indexed'])} pages  (expected 0)")
    print(f"  Skipped  : {len(result['skipped'])} pages  (expected {len(pages)})")
    for url in result["skipped"]:
        print(f"    ↩ skipped  {url}")

    check(len(result["indexed"]) == 0, "No pages re-indexed on duplicate run")
    check(len(result["skipped"]) == len(pages), "All pages skipped on duplicate run")


# ── Step 3 — Search ───────────────────────────────────────────────────────────
def step_search(searcher: KBSearch, query: str, step_num: int):
    banner(f'STEP {step_num} — Search: "{query}"')
    results = searcher.search(query, top_k=5)

    if not results:
        print("  (no results)")
    else:
        for r in results:
            print(f"  [{r['score']:.4f}]  {r['title']}")
            print(f"           url  : {r['url']}")
            print(f"           path : {r['breadcrumb']}")
            snippet = r["content"].replace("\n", " ")[:140]
            print(f"           ...  : {snippet}")
            print()

    check(len(results) > 0, f'Search returned at least 1 result for "{query}"')


# ── Step 5 — Remove ───────────────────────────────────────────────────────────
def step_remove(indexer: KBIndexer):
    banner("STEP 5 — Remove all indexed pages")

    before = indexer.list_pages(domain=DOMAIN)
    print(f"  Pages before removal : {len(before)}")

    print(f"  Calling remove_domain('{DOMAIN}') …")
    indexer.remove_domain(DOMAIN)

    after = indexer.list_pages(domain=DOMAIN)
    print(f"  Pages after  removal : {len(after)}")

    check(after == [], "Index is empty after remove_domain")

    chunk_results = indexer.chunks.get(where={"domain": DOMAIN})
    leftover_chunks = chunk_results["ids"] if chunk_results else []
    check(leftover_chunks == [], "No chunk vectors left for domain")

    print("\n  Index cleaned up successfully.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'═' * 70}")
    print("  Moveworks KB  —  Live Integration Test")
    print(f"{'═' * 70}")

    indexer = KBIndexer()
    searcher = KBSearch()

    # Pre-cleanup: remove any leftovers from a previous interrupted run
    leftover = indexer.list_pages(domain=DOMAIN)
    if leftover:
        print(f"\n  [pre-cleanup] Removing {len(leftover)} leftover pages from a previous run …")
        indexer.remove_domain(DOMAIN)

    # 1. First index — all 4 pages are new
    pages = asyncio.run(step_index_first(indexer))

    # 2. Re-index the same pages — all must be skipped
    asyncio.run(step_index_dedup(indexer, pages))

    # 3 & 4. Search
    step_search(searcher, "compound actions", step_num=3)
    step_search(searcher, "script actions",   step_num=4)

    # 5. Remove everything and verify
    step_remove(indexer)

    print(f"\n{'═' * 70}")
    print("  ALL STEPS PASSED")
    print(f"{'═' * 70}\n")


if __name__ == "__main__":
    main()
