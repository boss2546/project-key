import requests
import json

base = 'http://localhost:8080'
results = []

# Test 1: Landing page
r = requests.get(f'{base}/')
results.append(('GET /', r.status_code, 'Context Bank' in r.text))

# Test 2: Legacy page
r = requests.get(f'{base}/legacy')
results.append(('GET /legacy', r.status_code, 'Project KEY' in r.text))

# Test 3: Login API (existing user)
r = requests.post(f'{base}/api/auth/login', json={'email': 'testuser@contextbank.com', 'password': 'password123'})
login_data = r.json() if r.status_code == 200 else {}
token = login_data.get('token', '')
results.append(('POST /api/auth/login', r.status_code, bool(token)))

# Test 4: Auth me
if token:
    r = requests.get(f'{base}/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    results.append(('GET /api/auth/me', r.status_code, r.status_code == 200))

# Test 5: Files API
r = requests.get(f'{base}/api/files', headers={'Authorization': f'Bearer {token}'})
results.append(('GET /api/files', r.status_code, r.status_code == 200))

# Test 6: Stats API
r = requests.get(f'{base}/api/stats', headers={'Authorization': f'Bearer {token}'})
results.append(('GET /api/stats', r.status_code, r.status_code == 200))

# Test 7: Profile API
r = requests.get(f'{base}/api/profile', headers={'Authorization': f'Bearer {token}'})
results.append(('GET /api/profile', r.status_code, r.status_code == 200))

# Test 8: Context Packs
r = requests.get(f'{base}/api/context-packs', headers={'Authorization': f'Bearer {token}'})
results.append(('GET /api/context-packs', r.status_code, r.status_code == 200))

# Test 9: Graph data
r = requests.get(f'{base}/api/graph', headers={'Authorization': f'Bearer {token}'})
results.append(('GET /api/graph', r.status_code, r.status_code == 200))

# Test 10: Wrong login
r = requests.post(f'{base}/api/auth/login', json={'email': 'wrong@email.com', 'password': 'wrong'})
results.append(('POST /api/auth/login (bad)', r.status_code, r.status_code == 401))

# Test 11: Register duplicate
r = requests.post(f'{base}/api/auth/register', json={'email': 'testuser@contextbank.com', 'password': 'test123', 'name': 'Dup'})
results.append(('POST /api/auth/register (dup)', r.status_code, r.status_code == 409))

# Test 12: Next.js static assets
r = requests.get(f'{base}/_next/static/chunks/0x16dtromqros.css')
results.append(('GET /_next/static (CSS)', r.status_code, r.status_code == 200))

# Print results
print('=' * 60)
print('PRE-DEPLOY API TEST RESULTS')
print('=' * 60)
all_pass = True
for endpoint, status, ok in results:
    icon = 'PASS' if ok else 'FAIL'
    if not ok:
        all_pass = False
    print(f'  [{icon}] {endpoint} -> {status}')
print('=' * 60)
verdict = 'ALL PASS - SAFE TO DEPLOY' if all_pass else 'SOME FAILED - DO NOT DEPLOY'
print(f'OVERALL: {verdict}')
print(f'Tests: {sum(1 for _, _, ok in results if ok)}/{len(results)}')
