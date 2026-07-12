# tools.py - Combined search + YouTube music MCP server
from fastmcp import FastMCP
import sys
import logging
import re
import traceback
import json

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger('Tools')

if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

logger.info("tools.py starting up...")

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


# ==================== MUSIC ====================

def _search_music_api(query: str) -> dict:
    """Search music using vkeys.cn API (works on ESP32 xiaozhi)."""
    import urllib.request
    import urllib.parse

    logger.info(f"_search_music_api: query={query}")
    encoded = urllib.parse.quote(query)
    sources = ['tencent', 'netease']

    for source in sources:
        url = f'https://api.vkeys.cn/v2/music/{source}?word={encoded}&choose=1&quality=2'
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if data.get('code') == 200 and data.get('data'):
                    d = data['data']
                    music_url = d.get('url', '')
                    if music_url:
                        logger.info(f"_search_music_api: found '{d.get('song')}' from {source}")
                        return {
                            'title': d.get('song', ''),
                            'artist': d.get('singer', ''),
                            'url': music_url,
                            'source': source,
                        }
        except Exception as e:
            logger.warning(f"_search_music_api: {source} failed: {e}")

    logger.info(f"_search_music_api: no results for '{query}'")
    return {}


def _search_youtube_fallback(query: str) -> dict:
    """Fallback: search YouTube (may not work on ESP32)."""
    from yt_dlp import YoutubeDL
    logger.info(f"_search_youtube_fallback: query={query}")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if info and 'entries' in info and info['entries']:
                entry = info['entries'][0]
                if entry:
                    # Get stream URL
                    ydl_opts2 = {
                        'quiet': True,
                        'no_warnings': True,
                        'format': 'bestaudio[ext=m4a]/bestaudio/best',
                        'noplaylist': True,
                    }
                    with YoutubeDL(ydl_opts2) as ydl2:
                        info2 = ydl2.extract_info(f"https://www.youtube.com/watch?v={entry['id']}", download=False)
                        stream_url = info2.get('url', '') if info2 else ''
                        if stream_url:
                            logger.info(f"_search_youtube_fallback: found '{entry.get('title')}'")
                            return {
                                'title': entry.get('title', ''),
                                'artist': entry.get('channel', '') or entry.get('uploader', ''),
                                'url': stream_url,
                                'source': 'youtube',
                            }
    except Exception as e:
        logger.error(f"_search_youtube_fallback error: {e}")
    return {}


@mcp.tool()
def search_music(query: str, max_results: int = 5) -> dict:
    """Search music and return song info with playable URL."""
    try:
        result = _search_music_api(query)
        if not result:
            result = _search_youtube_fallback(query)
        if result:
            return {"success": True, "query": query, "count": 1, "results": [result]}
        return {"success": False, "error": "No results found"}
    except Exception as e:
        logger.error(f"search_music error: {e}")
        return {"success": False, "error": str(e)}


@mcp.tool()
def play_music(query: str) -> dict:
    """Search and get playable URL for a song. Returns direct HTTP URL compatible with ESP32."""
    logger.info(f"play_music called: query={query}")
    try:
        result = _search_music_api(query)
        if not result:
            result = _search_youtube_fallback(query)
        if not result:
            logger.warning("play_music: no results found")
            return {"success": False, "error": "No results found"}
        resp = {
            "success": True,
            "title": result['title'],
            "artist": result['artist'],
            "url": result['url'],
            "audio_url": result['url'],
            "stream_url": result['url'],
            "source": result['source'],
        }
        logger.info(f"play_music: returning '{result['title']}' - {result['artist']} (source={result['source']})")
        return resp
    except Exception as e:
        logger.error(f"play_music error: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
