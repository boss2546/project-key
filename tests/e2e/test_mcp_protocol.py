import json, urllib.request

BASE = "http://127.0.0.1:8000/mcp"

def mcp_call(method, msg_id, params=None):
    body = {"jsonrpc": "2.0", "method": method, "id": msg_id}
    if params:
        body["params"] = params
    req = urllib.request.Request(BASE)
    req.add_header("Content-Type", "application/json")
    req.data = json.dumps(body).encode()
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

# 1. Initialize
print("== initialize ==")
res = mcp_call("initialize", 1, {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "claude", "version": "1.0"}
})
print(json.dumps(res, indent=2))

# 2. Tools list
print("\n== tools/list ==")
res = mcp_call("tools/list", 2)
for t in res["result"]["tools"]:
    print(f"  {t['name']}: {t['description'][:50]}...")

# 3. Tool call - get_profile
print("\n== tools/call (get_profile) ==")
res = mcp_call("tools/call", 3, {"name": "get_profile", "arguments": {}})
print(json.dumps(res, indent=2, ensure_ascii=False)[:500])

# 4. Tool call - search_knowledge
print("\n== tools/call (search_knowledge) ==")
res = mcp_call("tools/call", 4, {"name": "search_knowledge", "arguments": {"query": "data bank"}})
print(json.dumps(res, indent=2, ensure_ascii=False)[:500])

print("\n✅ MCP Protocol Test Complete!")
