"""Quick API test for v4.3"""
import httpx
import sys

BASE = "http://localhost:8000"
passed = 0
failed = 0

def test(name, url, check_fn=None):
    global passed, failed
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if check_fn:
                result = check_fn(d)
                if result:
                    print(f"  ✅ {name}: {result}")
                    passed += 1
                else:
                    print(f"  ❌ {name}: check failed")
                    failed += 1
            else:
                print(f"  ✅ {name}: OK")
                passed += 1
        else:
            print(f"  ❌ {name}: HTTP {r.status_code}")
            failed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1

print("=" * 50)
print("Project KEY v4.3 — API Test Suite")
print("=" * 50)

# 1. Stats
print("\n📊 Stats API")
test("GET /api/stats", f"{BASE}/api/stats",
     lambda d: f"Files={d['total_files']}, Clusters={d['total_clusters']}, Nodes={d['total_nodes']}, Edges={d['total_edges']}")

# 2. Files
print("\n📁 Files API")
test("GET /api/files", f"{BASE}/api/files",
     lambda d: f"{len(d['files'])} files loaded")

# 3. Clusters
print("\n📂 Clusters API")
test("GET /api/clusters", f"{BASE}/api/clusters",
     lambda d: f"{d['total_clusters']} clusters, {d['total_ready']} ready")

# 4. Graph
print("\n🔗 Graph API")
test("GET /api/graph/global", f"{BASE}/api/graph/global",
     lambda d: f"{len(d['nodes'])} nodes, {len(d['edges'])} edges")
test("GET /api/graph/nodes", f"{BASE}/api/graph/nodes",
     lambda d: f"{len(d['nodes'])} nodes")
test("GET /api/graph/edges", f"{BASE}/api/graph/edges",
     lambda d: f"{len(d['edges'])} edges")

# 5. Profile
print("\n👤 Profile API")
test("GET /api/profile", f"{BASE}/api/profile",
     lambda d: f"Profile set: {d.get('identity_summary', 'N/A')[:40]}...")

# 6. Context Packs
print("\n📦 Context Packs API")
test("GET /api/context-packs", f"{BASE}/api/context-packs",
     lambda d: f"{d['count']} packs")

# 7. Suggestions
print("\n💡 Suggestions API")
test("GET /api/suggestions", f"{BASE}/api/suggestions",
     lambda d: f"{d['count']} suggestions")

# 8. Lenses
print("\n🔍 Lenses API")
test("GET /api/lenses", f"{BASE}/api/lenses",
     lambda d: f"{len(d['lenses'])} lenses")

# 9. MCP Info
print("\n🔧 MCP API")
test("GET /api/mcp/info", f"{BASE}/api/mcp/info",
     lambda d: f"{len(d['tools'])} tools available")

# 10. Frontend
print("\n🌐 Frontend")
try:
    r = httpx.get(f"{BASE}/", timeout=10)
    if r.status_code == 200 and "Project KEY" in r.text:
        print(f"  ✅ Homepage: loaded ({len(r.text)} bytes)")
        passed += 1
    else:
        print(f"  ❌ Homepage: unexpected content")
        failed += 1
except Exception as e:
    print(f"  ❌ Homepage: {e}")
    failed += 1

try:
    r = httpx.get(f"{BASE}/styles.css", timeout=10)
    if r.status_code == 200:
        print(f"  ✅ CSS: loaded ({len(r.text)} bytes)")
        passed += 1
    else:
        print(f"  ❌ CSS: HTTP {r.status_code}")
        failed += 1
except Exception as e:
    print(f"  ❌ CSS: {e}")
    failed += 1

try:
    r = httpx.get(f"{BASE}/app.js", timeout=10)
    if r.status_code == 200:
        print(f"  ✅ JS: loaded ({len(r.text)} bytes)")
        passed += 1
    else:
        print(f"  ❌ JS: HTTP {r.status_code}")
        failed += 1
except Exception as e:
    print(f"  ❌ JS: {e}")
    failed += 1

# Summary
print("\n" + "=" * 50)
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("🎉 ALL TESTS PASSED — Ready to deploy!")
else:
    print("⚠️  Some tests failed — check before deploying")
print("=" * 50)

sys.exit(0 if failed == 0 else 1)
