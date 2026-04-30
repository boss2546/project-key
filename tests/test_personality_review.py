"""
🔵 ฟ้า — Personality Profile v6.0 Review Tests
=================================================
Tests ที่ฟ้าเขียนสำหรับ review code ของเขียว (commits 234c9ba + 4242ae5)
Run: python tests/test_personality_review.py
"""
import httpx
import json
import sys

BASE = "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, timeout=15.0)
results = []
passed = 0
failed = 0


def test(name, func):
    global passed, failed
    try:
        r = func()
        if r:
            results.append(f"✅ {name}")
            passed += 1
        else:
            results.append(f"❌ {name}")
            failed += 1
    except Exception as e:
        results.append(f"❌ {name}: {e}")
        failed += 1


# ─── Setup: Register/Login test user ───
email = "fah_review_test@test.com"
pw = "TestPass123!"
r = c.post("/api/auth/register", json={"email": email, "password": pw, "name": "Fah Test"})
if r.status_code == 409:
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
data = r.json()
token = data["token"]
h = {"Authorization": f"Bearer {token}"}


# T1: Reference endpoint (public, no auth)
def t1():
    r = c.get("/api/personality/reference")
    d = r.json()
    return (r.status_code == 200 and len(d["mbti"]["types"]) == 16 and
            len(d["enneagram"]["types"]) == 9 and len(d["clifton"]["all"]) == 34 and
            len(d["via"]["all"]) == 24 and len(d["mbti"]["test_links"]) >= 2)
test("T1: Reference endpoint (16 MBTI / 9 Enneagram / 34 Clifton / 24 VIA)", t1)


# T2: PUT 4 systems together
def t2():
    r = c.put("/api/profile", headers=h, json={
        "mbti": {"type": "INTJ-A", "source": "neris"},
        "enneagram": {"core": 5, "wing": 4},
        "clifton_top5": ["Strategic", "Learner", "Input", "Analytical", "Achiever"],
        "via_top5": ["Curiosity", "Love of Learning", "Honesty", "Judgment", "Perspective"],
    })
    d = r.json()
    return (r.status_code == 200 and d["mbti"]["type"] == "INTJ-A" and
            d["enneagram"]["core"] == 5 and d["enneagram"]["wing"] == 4 and
            len(d["clifton_top5"]) == 5 and len(d["via_top5"]) == 5)
test("T2: PUT 4 systems together", t2)


# T3: GET profile returns all 4 systems
def t3():
    r = c.get("/api/profile", headers=h)
    d = r.json()
    return (d["mbti"]["type"] == "INTJ-A" and d["enneagram"]["core"] == 5 and
            d["clifton_top5"][0] == "Strategic" and d["via_top5"][0] == "Curiosity")
test("T3: GET profile returns all 4 systems", t3)


# T4: History shows >= 4 entries after first save
def t4():
    r = c.get("/api/profile/personality/history", headers=h)
    d = r.json()
    return d["count"] >= 4
test("T4: History >= 4 entries after first save", t4)


# T5: Update 1 system → +1 history
def t5():
    r = c.get("/api/profile/personality/history", headers=h)
    before = r.json()["count"]
    c.put("/api/profile", headers=h, json={"mbti": {"type": "ENFP", "source": "official"}})
    r = c.get("/api/profile/personality/history", headers=h)
    after = r.json()["count"]
    return after == before + 1
test("T5: Update 1 system → +1 history entry", t5)


# T6: Same value twice → dedup (no new row)
def t6():
    r = c.get("/api/profile/personality/history", headers=h)
    before = r.json()["count"]
    c.put("/api/profile", headers=h, json={"mbti": {"type": "ENFP", "source": "official"}})
    r = c.get("/api/profile/personality/history", headers=h)
    after = r.json()["count"]
    return after == before
test("T6: Dedup — same value twice → no new history row", t6)


# T7: Clear field → history + cleared:true
def t7():
    c.put("/api/profile", headers=h, json={"mbti": None})
    r = c.get("/api/profile/personality/history?system=mbti", headers=h)
    h2 = r.json()["history"]
    return (len(h2) > 0 and h2[0]["data"].get("cleared") == True)
test("T7: Clear field → history row with cleared:true", t7)


# T8: Wrap-around wings
def t8():
    r1 = c.put("/api/profile", headers=h, json={"enneagram": {"core": 9, "wing": 1}})
    r2 = c.put("/api/profile", headers=h, json={"enneagram": {"core": 1, "wing": 9}})
    return r1.status_code == 200 and r2.status_code == 200
test("T8: Wing wrap-around 9w1 + 1w9 → 200", t8)


# T9: Invalid wing (4w7) → 422
def t9():
    r = c.put("/api/profile", headers=h, json={"enneagram": {"core": 4, "wing": 7}})
    return r.status_code == 422
test("T9: Invalid wing 4w7 → 422", t9)


# T10: Invalid MBTI type
def t10():
    r = c.put("/api/profile", headers=h, json={"mbti": {"type": "XXXX", "source": "neris"}})
    return r.status_code == 422
test("T10: Invalid MBTI type XXXX → 422", t10)


# T11: Invalid Clifton theme
def t11():
    r = c.put("/api/profile", headers=h, json={"clifton_top5": ["NotARealTheme"]})
    return r.status_code == 400
test("T11: Invalid Clifton theme → 400", t11)


# T12: Duplicate clifton themes
def t12():
    r = c.put("/api/profile", headers=h, json={"clifton_top5": ["Achiever", "Achiever"]})
    return r.status_code == 400
test("T12: Duplicate Clifton themes → 400", t12)


# T13: Too many (6 items)
def t13():
    r = c.put("/api/profile", headers=h, json={"clifton_top5": ["A", "B", "C", "D", "E", "F"]})
    return r.status_code == 422
test("T13: Too many Clifton (6 items) → 422", t13)


# T14: Invalid VIA strength
def t14():
    r = c.put("/api/profile", headers=h, json={"via_top5": ["FakeStrength"]})
    return r.status_code == 400
test("T14: Invalid VIA strength → 400", t14)


# T15: History filter by system
def t15():
    r = c.get("/api/profile/personality/history?system=enneagram", headers=h)
    d = r.json()
    return all(e["system"] == "enneagram" for e in d["history"])
test("T15: History filter by system", t15)


# T16: Invalid system filter
def t16():
    r = c.get("/api/profile/personality/history?system=invalid", headers=h)
    return r.status_code == 400
test("T16: Invalid system filter → 400", t16)


# T17: History without token → 401
def t17():
    r = c.get("/api/profile/personality/history")
    return r.status_code == 401
test("T17: History without token → 401", t17)


# T18: Reference no auth required
def t18():
    r = c.get("/api/personality/reference")
    return r.status_code == 200
test("T18: Reference no auth → 200", t18)


# T19: exclude_unset regression — empty string clears, {} no-op
def t19():
    c.put("/api/profile", headers=h, json={"identity_summary": "TestIdent"})
    r = c.get("/api/profile", headers=h)
    assert r.json()["identity_summary"] == "TestIdent"
    # Send empty object → identity should remain
    c.put("/api/profile", headers=h, json={})
    r = c.get("/api/profile", headers=h)
    assert r.json()["identity_summary"] == "TestIdent"
    # Send explicit empty string → should clear
    c.put("/api/profile", headers=h, json={"identity_summary": ""})
    r = c.get("/api/profile", headers=h)
    return r.json()["identity_summary"] == ""
test("T19: exclude_unset regression (empty clears, {} no-op)", t19)


# T20: Partial update — only mbti, others untouched
def t20():
    c.put("/api/profile", headers=h, json={
        "enneagram": {"core": 3, "wing": 2},
        "via_top5": ["Creativity", "Bravery"],
    })
    c.put("/api/profile", headers=h, json={"mbti": {"type": "ISTP", "source": "self_report"}})
    r = c.get("/api/profile", headers=h)
    d = r.json()
    return (d["mbti"]["type"] == "ISTP" and d["enneagram"]["core"] == 3 and
            d["via_top5"][0] == "Creativity")
test("T20: Partial update — only mbti, others untouched", t20)


# T21: limit=1 returns single entry
def t21():
    r = c.get("/api/profile/personality/history?limit=1", headers=h)
    d = r.json()
    return len(d["history"]) <= 1
test("T21: History limit=1 → 1 entry max", t21)


# T22: Clifton with 1 item → 200
def t22():
    r = c.put("/api/profile", headers=h, json={"clifton_top5": ["Achiever"]})
    return r.status_code == 200
test("T22: Clifton 1 item → 200", t22)


# T23: MBTI suffix check — -X invalid
def t23():
    r = c.put("/api/profile", headers=h, json={"mbti": {"type": "INTJ-X", "source": "neris"}})
    return r.status_code == 422
test("T23: Invalid suffix -X → 422", t23)


# T24: MBTI source invalid
def t24():
    r = c.put("/api/profile", headers=h, json={"mbti": {"type": "INTJ", "source": "random"}})
    return r.status_code == 422
test("T24: Invalid MBTI source → 422", t24)


# T25: VIA with "Appreciation of Beauty & Excellence" (& character)
def t25():
    r = c.put("/api/profile", headers=h, json={"via_top5": ["Appreciation of Beauty & Excellence"]})
    d = r.json()
    return r.status_code == 200 and "Appreciation" in d["via_top5"][0]
test('T25: VIA "Appreciation of Beauty & Excellence" → 200', t25)


# ─── Print Results ───
print()
for r in results:
    print(r)
print(f"\n📊 Results: {passed}/{passed+failed} passed, {failed} failed")

if failed > 0:
    sys.exit(1)
