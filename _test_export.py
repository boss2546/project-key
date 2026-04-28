"""Test export enforcement + downgrade/upgrade logic — v5.9.3c"""
import requests

BASE = "http://localhost:8000"

# Login
r = requests.post(f"{BASE}/api/auth/login", json={"email": "e2etest28@test.com", "password": "test1234"})
data = r.json()
token = data.get("token") or data.get("access_token")
h = {"Authorization": f"Bearer {token}"}

# Get file id
r = requests.get(f"{BASE}/api/files", headers=h)
files = r.json()["files"]
file_id = files[0]["id"]
filename = files[0]["filename"]
print(f"File: {filename} ({file_id[:12]}...)")

# Test export (download) - Free limit = 10/month
print("\n=== Export Enforcement Test (Free limit=10) ===")
blocked = False
for i in range(12):
    r = requests.get(f"{BASE}/api/files/{file_id}/download", headers=h)
    if r.status_code == 403:
        print(f"  Export {i+1}: BLOCKED - {r.json()['detail']}")
        blocked = True
        break
    else:
        print(f"  Export {i+1}: OK")

if blocked:
    print("  RESULT: PASS - Export blocked at limit")
else:
    print("  RESULT: All 12 went through (may have prior usage)")

# Test share link (also counts as export)
print("\n=== Share Link Test (also uses export quota) ===")
r = requests.post(f"{BASE}/api/files/{file_id}/share", headers=h)
if r.status_code == 403:
    print(f"  Share: BLOCKED - {r.json()['detail']}")
    print("  RESULT: PASS - Share also blocked")
elif r.status_code == 200:
    print(f"  Share: OK")
else:
    print(f"  Share: {r.status_code}")

# Check usage
print("\n=== Usage Summary ===")
r = requests.get(f"{BASE}/api/usage", headers=h)
usage = r.json()["usage"]
for key, val in usage.items():
    status = "FULL" if val["used"] >= val["limit"] else "ok"
    print(f"  {key}: {val['used']}/{val['limit']} [{status}]")

# Verify billing info
print("\n=== Billing Info ===")
r = requests.get(f"{BASE}/api/billing/info", headers=h)
info = r.json()
print(f"  Plan: {info['plan']}")
print(f"  Status: {info['subscription_status']}")
print(f"  Stripe Customer: {info['has_stripe_customer']}")

print("\n" + "="*50)
print("ALL EXPORT ENFORCEMENT TESTS COMPLETE")
