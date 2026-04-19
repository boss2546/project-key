import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

# 1. Get the secret from /api/mcp/info
res = urllib.request.urlopen(f"{BASE}/api/mcp/info")
info = json.loads(res.read())
connector_url = info["mcp_connector_url"]
print(f"Connector URL: {connector_url}")
print(f"  (Secret embedded in URL path)")

# 2. Test WITHOUT secret — should get 404
print("\n== Test WITHOUT secret (POST /mcp) ==")
try:
    req = urllib.request.Request(f"{BASE}/mcp")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1}).encode()
    urllib.request.urlopen(req)
    print("  ERROR: Should have been rejected!")
except urllib.error.HTTPError as e:
    print(f"  Blocked! Status: {e.code} (Expected 404/405)")

# 3. Test WITH wrong secret — should get 401
print("\n== Test WITH WRONG secret ==")
try:
    req = urllib.request.Request(f"{BASE}/mcp/wrong-secret-123")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1}).encode()
    urllib.request.urlopen(req)
    print("  ERROR: Should have been rejected!")
except urllib.error.HTTPError as e:
    print(f"  Blocked! Status: {e.code} (Expected 401)")

# 4. Test WITH correct secret — should work
print("\n== Test WITH CORRECT secret ==")
req = urllib.request.Request(connector_url)
req.add_header("Content-Type", "application/json")
req.data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {"protocolVersion": "2024-11-05"}}).encode()
r = urllib.request.urlopen(req)
data = json.loads(r.read())
print(f"  SUCCESS! Server: {data['result']['serverInfo']['name']} v{data['result']['serverInfo']['version']}")

# 5. Test tools/call with correct secret
print("\n== Test tools/call with correct secret ==")
req2 = urllib.request.Request(connector_url)
req2.add_header("Content-Type", "application/json")
req2.data = json.dumps({"jsonrpc": "2.0", "method": "tools/call", "id": 2, "params": {"name": "get_profile", "arguments": {}}}).encode()
r2 = urllib.request.urlopen(req2)
data2 = json.loads(r2.read())
print(f"  Profile: {data2['result']['content'][0]['text'][:100]}...")

print("\n✅ Security Test Complete — Only correct URL works!")
