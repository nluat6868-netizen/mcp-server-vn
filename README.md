# MCP Search Server

MCP Server cung cấp công cụ tìm kiếm web, trả về nội dung thực tế từ kết quả tìm kiếm.

## Tính năng

- `web_search`: Tìm kiếm web và trả về nội dung thực tế
- `fetch_webpage`: Đọc nội dung trang web

## Cài đặt

```bash
pip install -r requirements.txt
```

## Sử dụng

### Chạy local (stdio)

```bash
python search.py
```

### Chạy qua WebSocket pipe

```bash
$env:MCP_ENDPOINT = "ws://your-server:port"
python mcp_pipe.py
```

### Deploy lên Vercel

```bash
vercel deploy
```

## Cấu trúc

```
mcp-server-vn/
├── api/
│   └── index.py       # Vercel serverless function (SSE)
├── search.py          # MCP tool tìm kiếm (local)
├── mcp_pipe.py        # WebSocket pipe
├── mcp_config.json    # Cấu hình server
├── vercel.json        # Vercel config
├── requirements.txt   # Dependencies
└── README.md
```

## Vercel Endpoint

Sau khi deploy, endpoint sẽ là:
```
https://your-project.vercel.app/sse
```

## License

MIT
