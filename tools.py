# tools.py - Combined search + YouTube music MCP server
from fastmcp import FastMCP
import sys
import logging
import re

logger = logging.getLogger('Tools')

if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

mcp = FastMCP("Tools")


# ==================== SEARCH ====================

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
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
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


# ==================== YOUTUBE MUSIC ====================

def _search_youtube(query: str, max_results: int = 5) -> list:
    from yt_dlp import YoutubeDL
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
    }
    search_query = f"ytsearch{max_results}:{query}"
    results = []
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        if not info or 'entries' not in info:
            return results
        for entry in info['entries']:
            if entry is None:
                continue
            results.append({
                'id': entry.get('id', ''),
                'title': entry.get('title', ''),
                'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                'duration': entry.get('duration', 0),
                'channel': entry.get('channel', '') or entry.get('uploader', ''),
            })
    return results


def _get_stream_url(video_id: str) -> str:
    from yt_dlp import YoutubeDL
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'noplaylist': True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info:
            return info.get('url', '') or info.get('webpage_url', '')
    return ''


@mcp.tool()
def search_music(query: str, max_results: int = 5) -> dict:
    """Search YouTube for music and return video info."""
    try:
        results = _search_youtube(query, max_results)
        return {"success": True, "query": query, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"search_music error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_music_url(video_id: str) -> dict:
    """Get playable stream URL for a YouTube video."""
    try:
        stream_url = _get_stream_url(video_id)
        if stream_url:
            return {"success": True, "video_id": video_id, "stream_url": stream_url}
        return {"success": False, "error": "Could not get stream URL"}
    except Exception as e:
        logger.error(f"get_music_url error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
def play_music(query: str) -> dict:
    """Search and get playable URL for a song in one step."""
    try:
        results = _search_youtube(query, max_results=1)
        if not results:
            return {"success": False, "error": "No results found"}
        top = results[0]
        stream_url = _get_stream_url(top['id'])
        return {
            "success": True,
            "title": top['title'],
            "url": top['url'],
            "audio_url": stream_url,
            "stream_url": stream_url,
            "duration": top['duration'],
            "channel": top['channel'],
        }
    except Exception as e:
        logger.error(f"play_music error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
