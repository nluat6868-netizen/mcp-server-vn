# api/index.py
import json
import re
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "status": "ok",
                "message": "MCP Search Server is running",
                "tools": ["web_search", "fetch_webpage"],
                "usage": {
                    "search": "GET /api/search?query=your+query",
                    "fetch": "GET /api/fetch?url=https://example.com"
                }
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

        elif self.path.startswith("/api/search"):
            query = self._get_param("query")
            if not query:
                self._send_json({"success": False, "error": "Missing 'query' parameter"}, 400)
                return

            try:
                from ddgs import DDGS
                results = DDGS().text(query, max_results=3)
                data = []
                for r in results:
                    url = r.get("href", "")
                    content = r.get("body", "")
                    # Try fetch content
                    if url:
                        try:
                            req = urllib.request.Request(url, headers={
                                "User-Agent": "Mozilla/5.0"
                            })
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                html = resp.read().decode("utf-8", errors="replace")
                            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                            text = re.sub(r'<[^>]+>', ' ', text)
                            text = re.sub(r'&[a-zA-Z]+;', ' ', text)
                            text = re.sub(r'\s+', ' ', text).strip()[:3000]
                            if len(text) > len(content):
                                content = text
                        except Exception:
                            pass
                    data.append({"title": r.get("title", ""), "url": url, "content": content})
                self._send_json({"success": True, "query": query, "results": data})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)

        elif self.path.startswith("/api/fetch"):
            url = self._get_param("url")
            if not url:
                self._send_json({"success": False, "error": "Missing 'url' parameter"}, 400)
                return
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'&[a-zA-Z]+;', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()[:3000]
                self._send_json({"success": True, "url": url, "content": text})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

    def _get_param(self, name):
        if "?" in self.path:
            qs = self.path.split("?", 1)[1]
            for param in qs.split("&"):
                if param.startswith(f"{name}="):
                    return urllib.parse.unquote(param.split("=", 1)[1])
        return None

    def _send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
