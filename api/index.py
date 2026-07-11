# api/index.py
import json
import re
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify

app = Flask(__name__)


def _fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _extract_text(html, max_len=3000):
    text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len]


@app.route("/")
def index():
    return jsonify({"status": "ok", "name": "MCP Search Server"})


@app.route("/api/search")
def search():
    q = request.args.get("query", "")
    if not q:
        return jsonify({"error": "Missing query"}), 400
    try:
        from ddgs import DDGS
        results = DDGS().text(q, max_results=3)
        data = []
        for r in results:
            url = r.get("href", "")
            content = r.get("body", "")
            if url:
                try:
                    html = _fetch_url(url)
                    extracted = _extract_text(html, 3000)
                    if len(extracted) > len(content):
                        content = extracted
                except Exception:
                    pass
            data.append({"title": r.get("title", ""), "url": url, "content": content})
        return jsonify({"success": True, "query": q, "results": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


application = app
