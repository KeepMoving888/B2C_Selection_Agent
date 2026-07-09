import json
import urllib.request
import os

for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
    os.environ.pop(k, None)

req = urllib.request.Request("http://localhost:9090/api/v1/targets")
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        d = json.load(resp)
    for t in d['data']['activeTargets']:
        print(f"{t['labels']['job']:20s} {t['health']:10s} {t.get('lastError', '')[:60]}")
except Exception as e:
    print(f"ERROR: {e}")
