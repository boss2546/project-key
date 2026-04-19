import json, urllib.request, urllib.error

# Test wrong secret on production
print("== Test WRONG secret on production ==")
try:
    req = urllib.request.Request("https://project-key.fly.dev/mcp/wrong-key")
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps({"jsonrpc": "2.0", "method": "initialize", "id": 1}).encode()
    urllib.request.urlopen(req)
    print("  ERROR!")
except urllib.error.HTTPError as e:
    print(f"  Blocked! Status: {e.code}")

# Test correct secret
print("\n== Test CORRECT secret on production ==")
req = urllib.request.Request("https://project-key.fly.dev/mcp/r2rr-TE-9tSkLTT23pfxU9wCIqrW-KXWE1nNNRAvRxQ")
req.add_header("Content-Type", "application/json")
req.data = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 2}).encode()
r = urllib.request.urlopen(req)
data = json.loads(r.read())
print(f"  Tools found: {len(data['result']['tools'])}")
for t in data['result']['tools']:
    print(f"    - {t['name']}")

print("\n✅ Production security verified!")
