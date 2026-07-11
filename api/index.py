# api/index.py
from fastmcp import FastMCP
import re

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
            except Exception:
                pass
        results.append({"title": title, "url": url, "content": content})
    results.sort(key=lambda x: len(x.get("content", "")), reverse=True)
    return results


@mcp.tool()
def web_search(query: str, max_results: int = 3) -> dict:
    """Search the web and return actual content from results."""
    try:
        results = _search_and_fetch(query, max_results)
        return {"success": True, "query": query, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def fetch_webpage(url: str) -> dict:
    """Fetch and return the text content of a webpage."""
    try:
        html = _fetch_url(url)
        content = _extract_text(html, 3000)
        return {"success": True, "url": url, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Vercel serverless handler
from fastmcp.server.http import SSEServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount

sse = SSEServerTransport("/messages/")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp.run_streamable_http_async(transport=streams[0])


app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)


async def handler(request, scope):
    return await app(scope, request.receive, request._send)
