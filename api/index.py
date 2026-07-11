# api/index.py
import json
import re
import urllib.request
import urllib.parse

try:
    from flask import Flask, request, jsonify
    app = Flask(__name__)
except ImportError:
    app = None


def _search(query):
    from ddgs import DDGS
    results = DDGS().text(query, max_results=3)
    data = []
    for r in results:
        url = r.get("href", "")
        content = r.get("body", "")
        if url:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()[:3000]
                if len(text) > len(content):
                    content = text
            except Exception:
                pass
        data.append({"title": r.get("title", ""), "url": url, "content": content})
    return data


if app:
    @app.route("/")
    def index():
        return jsonify({
            "status": "ok",
            "name": "MCP Search Server",
            "endpoints": {
                "search": "/api/search?query=...",
                "fetch": "/api/fetch?url=..."
            }
        })

    @app.route("/api/search")
    def search():
        q = request.args.get("query", "")
        if not q:
            return jsonify({"error": "Missing query"}), 400
        try:
            results = _search(q)
            return jsonify({"success": True, "query": q, "results": results})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/fetch")
    def fetch_page():
        url = request.args.get("url", "")
        if not url:
            return jsonify({"error": "Missing url"}), 400
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()[:3000]
            return jsonify({"success": True, "url": url, "content": text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# Entry point for Vercel
application = app
