# api/index.py
import json


def handler(request, response):
    response.status_code = 200
    response.headers["Content-Type"] = "application/json"
    response.body = json.dumps({"status": "ok", "message": "MCP Server is running"})
    return response
