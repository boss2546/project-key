import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api"

def test_mcp_flow():
    print("🚀 Starting Detailed E2E Test for MCP Connector Layer (v4)")
    
    # 1. Info & Tools Check
    print("\n--- 1. Info & Tools Check ---")
    info_res = requests.get(f"{API_URL}/mcp/info")
    info = info_res.json()
    print(f"Server URL: {info['mcp_server_url']}")
    print(f"Tools Count: {len(info['available_tools'])}")
    for t in info['available_tools']:
        print(f" - {t['name']}: {t['description'][:50]}...")

    # 2. Token Management
    print("\n--- 2. Token Lifecycle Check ---")
    # Generate
    gen_res = requests.post(f"{API_URL}/mcp/tokens", json={"label": "Integration Test Token"})
    token_data = gen_res.json()
    raw_token = token_data['raw_token']
    token_id = token_data['id']
    print(f"Token Generated: {token_id} ({raw_token[:10]}...)")

    # List
    list_res = requests.get(f"{API_URL}/mcp/tokens")
    tokens = list_res.json()['tokens']
    print(f"Active Tokens in DB: {len([t for t in tokens if t['is_active']])}")

    # 3. Tool Calls (Success Scenarios)
    print("\n--- 3. MCP Tool Calls (Success) ---")
    headers = {"Authorization": f"Bearer {raw_token}"}
    
    tools_to_test = [
        ("get_profile", {}),
        ("list_context_packs", {}),
        ("search_knowledge", {"query": "test", "limit": 2})
    ]
    
    for tool_name, params in tools_to_test:
        start = time.time()
        res = requests.post(f"{API_URL}/mcp/tools/call", headers=headers, json={"tool": tool_name, "params": params})
        latency = (time.time() - start) * 1000
        data = res.json()
        status = data.get('status')
        print(f"Tool: [{tool_name:20}] Status: {status} Latency: {latency:.1f}ms (Reported: {data.get('latency_ms')}ms)")
        if status != "success":
            print(f"  ❌ Error: {data}")

    # 4. Security Check (Negative Scenarios)
    print("\n--- 4. Security Check ---")
    # Invalid Token
    bad_res = requests.post(f"{API_URL}/mcp/tools/call", headers={"Authorization": "Bearer pk_invalid"}, json={"tool": "get_profile"})
    print(f"Invalid Token Response: {bad_res.status_code} (Expected 401)")

    # Revoked Token
    requests.delete(f"{API_URL}/mcp/tokens/{token_id}")
    rev_res = requests.post(f"{API_URL}/mcp/tools/call", headers=headers, json={"tool": "get_profile"})
    print(f"Revoked Token Response: {rev_res.status_code} (Expected 401)")

    # 5. Usage Logs Check
    print("\n--- 5. Usage Logs Check ---")
    logs_res = requests.get(f"{API_URL}/mcp/logs?limit=10")
    logs = logs_res.json()['logs']
    print(f"Recent Logs retrieved: {len(logs)}")
    for l in logs[:5]:
        print(f" [{l['created_at'][-8:]}] Tool: {l['tool_name']:20} Status: {l['status']:8} Latency: {l['latency_ms']}ms")

    print("\n✅ Verification Script Complete.")

if __name__ == "__main__":
    try:
        test_mcp_flow()
    except Exception as e:
        print(f"❌ Test Failed: {e}")
