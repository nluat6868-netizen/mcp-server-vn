# search.py
from fastmcp import FastMCP
import sys
import logging
import re

logger = logging.getLogger('Search')

if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

mcp = FastMCP("Search")


def _fetch_url(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extract_text(html: str, max_len: int = 3000) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len]


def _search_and_fetch(query: str, max_results: int = 5) -> list:
    """Search and fetch content from best results."""
    from ddgs import DDGS

    search_results = DDGS().text(query, max_results=max_results)

    results = []
    for r in search_results[:max_results]:
        url = r.get("href", "")
        title = r.get("title", "")
        snippet = r.get("body", "")

        content = snippet
        if url:
            try:
                html = _fetch_url(url)
                extracted = _extract_text(html, 3000)
                if len(extracted) > len(snippet):
                    content = extracted
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")

        results.append({
            "title": title,
            "url": url,
            "content": content,
        })

    # Sort by content length (best content first)
    results.sort(key=lambda x: len(x.get("content", "")), reverse=True)

    return results


@mcp.tool()
def web_search(query: str, max_results: int = 3) -> dict:
    """Search the web and return actual content from results. Use this to find information like prices, news, facts, statistics."""
    try:
        results = _search_and_fetch(query, max_results)
        return {"success": True, "query": query, "results": results}
    except Exception as e:
        logger.error(f"web_search error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
def fetch_webpage(url: str) -> dict:
    """Fetch and return the text content of a webpage."""
    try:
        html = _fetch_url(url)
        content = _extract_text(html, 3000)
        return {"success": True, "url": url, "content": content}
    except Exception as e:
        logger.error(f"fetch_webpage error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
