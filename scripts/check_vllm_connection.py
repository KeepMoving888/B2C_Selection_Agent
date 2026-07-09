#!/usr/bin/env python3
"""Check connection to local vLLM service (manual utility)."""
import os
import sys
import urllib.request

# Clear any proxy settings
for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(k, None)

urls = [
    "http://127.0.0.1:8002/v1/models",
    "http://localhost:8002/v1/models",
]

for url in urls:
    try:
        print(f"Trying {url} ...")
        resp = urllib.request.urlopen(url, timeout=5)
        data = resp.read().decode("utf-8")
        print(f"OK: {data[:500]}")
        sys.exit(0)
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

sys.exit(1)
