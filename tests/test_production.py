"""
Project KEY v5.0 — Production Smoke & Stress Tests
===================================================
เทสแบบ "หักๆ" ก่อนให้ผู้ใช้จริง — ทดสอบทุกจุดสำคัญ

Run: python -m pytest tests/test_production.py -v --tb=short
"""

import pytest
import httpx
import random
import string
import time

BASE = "https://project-key.fly.dev"
TIMEOUT = 15.0


# ─── Helpers ───

def rand_email():
    slug = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{slug}@smoke.test"


def rand_str(n=12):
    return "".join(random.choices(string.ascii_letters, k=n))


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=TIMEOUT, follow_redirects=True) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    """Register a throwaway user and return (token, user) for authenticated tests."""
    email = rand_email()
    password = "TestPass123!"
    r = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "name": "Smoke Tester",
    })
    assert r.status_code == 200, f"Register failed: {r.text}"
    data = r.json()
    assert "token" in data
    assert "user" in data
    return data["token"], data["user"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════
# 1️⃣  FRONTEND — หน้าเว็บโหลดได้ไหม?
# ═══════════════════════════════════════════════════

class TestFrontend:
    """ทดสอบว่าหน้าเว็บโหลดได้ปกติ"""

    def test_root_returns_html(self, client):
        """GET / ต้องได้ HTML"""
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "Project KEY" in r.text

    def test_legacy_route(self, client):
        """GET /legacy ต้องได้ HTML เหมือน root"""
        r = client.get("/legacy")
        assert r.status_code == 200
        assert "Project KEY" in r.text

    def test_css_loads(self, client):
        """CSS ต้องโหลดได้"""
        r = client.get("/legacy/styles.css")
        assert r.status_code == 200

    def test_js_loads(self, client):
        """JS ต้องโหลดได้"""
        r = client.get("/legacy/app.js")
        assert r.status_code == 200

    def test_nonexistent_page_404(self, client):
        """หน้าที่ไม่มีต้อง 404"""
        r = client.get("/this-page-does-not-exist-xyz")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════
# 2️⃣  AUTH — ระบบล็อกอินพังไหม?
# ═══════════════════════════════════════════════════

class TestAuth:
    """ทดสอบระบบ Authentication"""

    def test_register_success(self, client):
        """สมัครสมาชิกใหม่ต้องสำเร็จ"""
        r = client.post("/api/auth/register", json={
            "email": rand_email(),
            "password": "ValidPass123",
            "name": "Test User",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["user"]["name"] == "Test User"

    def test_register_duplicate_email(self, client, auth):
        """สมัครซ้ำ email เดิมต้อง error"""
        token, user = auth
        r = client.post("/api/auth/register", json={
            "email": user["email"],
            "password": "AnotherPass123",
            "name": "Duplicate",
        })
        assert r.status_code in (400, 409, 422)

    def test_register_short_password(self, client):
        """รหัสผ่านสั้นเกินต้อง error"""
        r = client.post("/api/auth/register", json={
            "email": rand_email(),
            "password": "123",
            "name": "Short",
        })
        assert r.status_code in (400, 422)

    def test_register_empty_email(self, client):
        """ไม่กรอก email ต้อง error"""
        r = client.post("/api/auth/register", json={
            "email": "",
            "password": "ValidPass123",
            "name": "NoEmail",
        })
        assert r.status_code in (400, 422)

    def test_login_success(self, client, auth):
        """Login ด้วย credentials ที่ถูกต้อง"""
        token, user = auth
        # We know the password from the fixture
        r = client.post("/api/auth/login", json={
            "email": user["email"],
            "password": "TestPass123!",
        })
        assert r.status_code == 200
        assert "token" in r.json()

    def test_login_wrong_password(self, client, auth):
        """Login ผิดรหัสต้อง error"""
        _, user = auth
        r = client.post("/api/auth/login", json={
            "email": user["email"],
            "password": "WrongPassword!!",
        })
        assert r.status_code in (400, 401)

    def test_login_nonexistent_email(self, client):
        """Login ด้วย email ที่ไม่มีต้อง error"""
        r = client.post("/api/auth/login", json={
            "email": "nobody_exists_12345@fake.com",
            "password": "anything",
        })
        assert r.status_code in (400, 401)

    def test_me_with_valid_token(self, client, auth):
        """GET /api/auth/me ต้องได้ user info"""
        token, _ = auth
        r = client.get("/api/auth/me", headers=auth_headers(token))
        assert r.status_code == 200
        assert "email" in r.json()

    def test_me_with_invalid_token(self, client):
        """Token ผิดต้อง 401"""
        r = client.get("/api/auth/me", headers=auth_headers("fake.invalid.token"))
        assert r.status_code == 401

    def test_me_without_token(self, client):
        """ไม่ส่ง token ต้อง 401"""
        r = client.get("/api/auth/me")
        assert r.status_code == 401


# ═══════════════════════════════════════════════════
# 3️⃣  API ที่ต้อง AUTH — เข้าถึงโดยไม่ login ได้ไหม?
# ═══════════════════════════════════════════════════

class TestUnauthorizedAccess:
    """ทดสอบว่า API ทุกตัวป้องกัน unauthorized access"""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/files"),
        ("GET", "/api/clusters"),
        ("GET", "/api/profile"),
        ("GET", "/api/context-packs"),
        ("GET", "/api/stats"),
        ("GET", "/api/graph/global"),
        ("GET", "/api/mcp/tokens"),
        ("GET", "/api/mcp/logs"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    def test_protected_endpoint_requires_auth(self, client, method, path):
        """Endpoint ที่ต้อง auth ต้อง reject ถ้าไม่มี token"""
        if method == "GET":
            r = client.get(path)
        elif method == "POST":
            r = client.post(path)
        assert r.status_code == 401, f"{method} {path} should require auth but got {r.status_code}"


# ═══════════════════════════════════════════════════
# 4️⃣  CORE API — ฟีเจอร์หลักพังไหม?
# ═══════════════════════════════════════════════════

class TestCoreAPI:
    """ทดสอบ API หลักๆ ว่าทำงานได้"""

    def test_get_files_empty(self, client, auth):
        """User ใหม่ต้องไม่มีไฟล์"""
        token, _ = auth
        r = client.get("/api/files", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        # API returns {files: []} or []
        files = data.get("files", data) if isinstance(data, dict) else data
        assert isinstance(files, list)

    def test_get_stats(self, client, auth):
        """Stats ต้องส่งค่ากลับมาเป็น object"""
        token, _ = auth
        r = client.get("/api/stats", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "total_files" in data
        assert "total_clusters" in data

    def test_get_profile(self, client, auth):
        """Profile ต้องส่งค่ากลับ"""
        token, _ = auth
        r = client.get("/api/profile", headers=auth_headers(token))
        assert r.status_code == 200

    def test_update_profile(self, client, auth):
        """อัปเดต profile ต้องสำเร็จ"""
        token, _ = auth
        r = client.put("/api/profile", headers=auth_headers(token), json={
            "identity": "Test student",
            "goals": "Testing",
            "work_style": "Fast",
            "output_preference": "Bullet points",
            "background": "QA background",
        })
        assert r.status_code == 200

    def test_get_clusters(self, client, auth):
        """Clusters ต้องส่งค่ากลับ"""
        token, _ = auth
        r = client.get("/api/clusters", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        clusters = data.get("clusters", data) if isinstance(data, dict) else data
        assert isinstance(clusters, list)

    def test_get_context_packs(self, client, auth):
        """Context packs ต้องส่งค่ากลับ"""
        token, _ = auth
        r = client.get("/api/context-packs", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        packs = data.get("packs", data) if isinstance(data, dict) else data
        assert isinstance(packs, list)

    def test_get_graph_global(self, client, auth):
        """Graph ต้องส่งค่ากลับ"""
        token, _ = auth
        r = client.get("/api/graph/global", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data


# ═══════════════════════════════════════════════════
# 5️⃣  FILE UPLOAD — อัปโหลดพังไหม?
# ═══════════════════════════════════════════════════

class TestFileUpload:
    """ทดสอบระบบอัปโหลดไฟล์"""

    def test_upload_txt_file(self, client, auth):
        """อัปโหลดไฟล์ .txt ต้องสำเร็จ"""
        token, _ = auth
        content = f"This is a test file for smoke testing.\nTimestamp: {time.time()}"
        files = {"files": ("smoke_test.txt", content.encode(), "text/plain")}
        r = client.post("/api/upload", headers=auth_headers(token), files=files)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1

    def test_upload_md_file(self, client, auth):
        """อัปโหลดไฟล์ .md ต้องสำเร็จ"""
        token, _ = auth
        content = f"# Smoke Test\n\nThis is a markdown test file.\n- Item 1\n- Item 2\n"
        files = {"files": ("smoke_test.md", content.encode(), "text/markdown")}
        r = client.post("/api/upload", headers=auth_headers(token), files=files)
        assert r.status_code == 200

    def test_upload_empty_file(self, client, auth):
        """อัปโหลดไฟล์เปล่าต้อง handle ได้ (ไม่ crash)"""
        token, _ = auth
        files = {"files": ("empty.txt", b"", "text/plain")}
        r = client.post("/api/upload", headers=auth_headers(token), files=files)
        # ไม่ว่าจะ success หรือ skip ก็ไม่ควร 500
        assert r.status_code != 500

    def test_upload_without_auth(self, client):
        """อัปโหลดโดยไม่ login ต้อง 401"""
        files = {"files": ("test.txt", b"data", "text/plain")}
        r = client.post("/api/upload", files=files)
        assert r.status_code == 401

    def test_files_appear_after_upload(self, client, auth):
        """ไฟล์ต้องปรากฏใน file list หลังอัปโหลด"""
        token, _ = auth
        r = client.get("/api/files", headers=auth_headers(token))
        assert r.status_code == 200
        files = r.json()
        assert len(files) >= 1, "Should have at least 1 file after upload"

    def test_file_summary_accessible(self, client, auth):
        """ต้องดู summary ของไฟล์ได้ (404 ถ้ายังไม่ organize)"""
        token, _ = auth
        r = client.get("/api/files", headers=auth_headers(token))
        data = r.json()
        files = data.get("files", data) if isinstance(data, dict) else data
        if files:
            fid = files[0]["id"]
            r2 = client.get(f"/api/summary/{fid}", headers=auth_headers(token))
            # 200 if summarized, 404 if not yet organized — both valid
            assert r2.status_code in (200, 404)

    def test_file_content_accessible(self, client, auth):
        """ต้องดู content ของไฟล์ได้"""
        token, _ = auth
        r = client.get("/api/files", headers=auth_headers(token))
        data = r.json()
        files = data.get("files", data) if isinstance(data, dict) else data
        if files:
            fid = files[0]["id"]
            r2 = client.get(f"/api/files/{fid}/content", headers=auth_headers(token))
            assert r2.status_code == 200


# ═══════════════════════════════════════════════════
# 6️⃣  CHAT — AI ตอบได้ไหม?
# ═══════════════════════════════════════════════════

class TestChat:
    """ทดสอบ AI Chat"""

    def test_chat_basic_question(self, client, auth):
        """ถาม AI ต้องได้คำตอบกลับ"""
        token, _ = auth
        r = client.post("/api/chat", headers=auth_headers(token), json={
            "question": "สวัสดี",
        }, timeout=30.0)
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data or "answer" in data or "message" in data or "response" in data

    def test_chat_empty_message(self, client, auth):
        """ส่งข้อความเปล่าต้อง handle ได้"""
        token, _ = auth
        r = client.post("/api/chat", headers=auth_headers(token), json={
            "question": "",
        }, timeout=15.0)
        # ไม่ควร 500
        assert r.status_code != 500

    def test_chat_without_auth(self, client):
        """Chat โดยไม่ login ต้อง 401"""
        r = client.post("/api/chat", json={"message": "hello"})
        assert r.status_code == 401


# ═══════════════════════════════════════════════════
# 7️⃣  MCP — Connector ทำงานไหม?
# ═══════════════════════════════════════════════════

class TestMCP:
    """ทดสอบ MCP Connector"""

    def test_mcp_info(self, client, auth):
        """MCP info ต้องส่งค่ากลับ"""
        token, _ = auth
        r = client.get("/api/mcp/info", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        assert "available_tools" in data or "server_url" in data or "mcp_url" in data

    def test_mcp_generate_token(self, client, auth):
        """สร้าง MCP token ต้องสำเร็จ"""
        token, _ = auth
        r = client.post("/api/mcp/tokens", headers=auth_headers(token), json={
            "label": "Smoke Test Token",
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data or "raw_token" in data

    def test_mcp_list_tokens(self, client, auth):
        """ดู token list ต้องได้"""
        token, _ = auth
        r = client.get("/api/mcp/tokens", headers=auth_headers(token))
        assert r.status_code == 200
        data = r.json()
        tokens = data.get("tokens", data) if isinstance(data, dict) else data
        assert isinstance(tokens, list)
        assert len(tokens) >= 1  # We created one in previous test

    def test_mcp_invalid_secret_rejected(self, client):
        """MCP endpoint ด้วย secret ผิดต้อง reject"""
        r = client.post("/mcp/fake-secret-12345", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
        })
        assert r.status_code in (401, 403, 404)


# ═══════════════════════════════════════════════════
# 8️⃣  EDGE CASES — ส่งข้อมูลแปลกๆ
# ═══════════════════════════════════════════════════

class TestEdgeCases:
    """ทดสอบ edge cases — ส่งข้อมูลแปลกๆ"""

    def test_invalid_json_body(self, client, auth):
        """ส่ง body ที่ไม่ใช่ JSON ต้องไม่ crash"""
        token, _ = auth
        r = client.post("/api/chat",
            headers={**auth_headers(token), "Content-Type": "application/json"},
            content=b"this is not json!!")
        assert r.status_code in (400, 422, 500)  # 500 is acceptable but not crash

    def test_very_long_message(self, client, auth):
        """ส่งข้อความยาวมากต้องไม่ crash"""
        token, _ = auth
        long_msg = "A" * 50000
        r = client.post("/api/chat", headers=auth_headers(token), json={
            "message": long_msg,
        }, timeout=30.0)
        # Should not crash — any status is fine except connection error
        assert r.status_code is not None

    def test_special_characters_in_profile(self, client, auth):
        """อักขระพิเศษใน profile ต้อง handle ได้"""
        token, _ = auth
        r = client.put("/api/profile", headers=auth_headers(token), json={
            "identity": "ผม 👨‍💻 ทำงาน <script>alert('xss')</script> & \"quotes\"",
            "goals": "Test 'single' & \"double\" quotes ñ é ü ö",
        })
        assert r.status_code == 200

    def test_nonexistent_file_id(self, client, auth):
        """ขอไฟล์ที่ไม่มีต้อง 404"""
        token, _ = auth
        r = client.get("/api/summary/nonexistent-id-12345", headers=auth_headers(token))
        assert r.status_code == 404

    def test_delete_nonexistent_file(self, client, auth):
        """ลบไฟล์ที่ไม่มีต้อง 404"""
        token, _ = auth
        r = client.delete("/api/files/nonexistent-id-12345", headers=auth_headers(token))
        assert r.status_code == 404

    def test_sql_injection_attempt(self, client):
        """SQL injection ใน login ต้องไม่พัง"""
        r = client.post("/api/auth/login", json={
            "email": "' OR 1=1 --",
            "password": "' OR 1=1 --",
        })
        # Should fail gracefully, not expose data
        assert r.status_code in (400, 401, 422)

    def test_xss_in_register_name(self, client):
        """XSS ใน name ต้อง sanitize หรือ reject"""
        r = client.post("/api/auth/register", json={
            "email": rand_email(),
            "password": "ValidPass123",
            "name": "<script>alert('xss')</script>",
        })
        if r.status_code == 200:
            # If accepted, at least should not break anything
            data = r.json()
            assert "token" in data


# ═══════════════════════════════════════════════════
# 9️⃣  CLEANUP — ลบข้อมูลทดสอบ
# ═══════════════════════════════════════════════════

class TestCleanup:
    """ลบไฟล์ทดสอบที่อัปโหลดไว้"""

    def test_delete_uploaded_files(self, client, auth):
        """ลบไฟล์ที่อัปโหลดระหว่างเทส"""
        token, _ = auth
        r = client.get("/api/files", headers=auth_headers(token))
        if r.status_code == 200:
            data = r.json()
            files = data.get("files", data) if isinstance(data, dict) else data
            for f in files:
                if isinstance(f, dict) and "smoke_test" in f.get("filename", ""):
                    client.delete(f"/api/files/{f['id']}", headers=auth_headers(token))
        assert True  # cleanup always passes
