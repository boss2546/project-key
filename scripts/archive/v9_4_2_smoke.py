"""End-to-end smoke test for v9.4.2 — run after server restart."""
import os, sys, asyncio, time
sys.path.insert(0, 'd:/PDB')
from dotenv import load_dotenv
load_dotenv('d:/PDB/.env')

from backend import ai_ingest, extraction
from backend.upload_worker import format_user_error

print('═══ V9.4.2 SMOKE SUITE ═══\n')

# ── TEST 1: classify_extraction_status (regression check) ──
print('[1] classify_extraction_status')
cases = [
    ("[AI ingest error: ClientError: 404]", "ocr_failed"),
    ("[AI ingest not configured: GOOGLE_API_KEY]", "unsupported"),
    ("[AI image: no description generated]", "ocr_failed"),
    ("[Image: OCR not available]", "ocr_failed"),
    ("[Empty file]", "empty"),
    ("Real text content", "ok"),
    ("[PDF encrypted]", "encrypted"),
]
fails = 0
for txt, want in cases:
    got = extraction.classify_extraction_status(txt)
    ok = '✓' if got == want else '✗'
    if got != want:
        fails += 1
    print(f"   {ok} {txt[:40]:<42} → {got} (want={want})")
print(f"   {'PASS' if fails==0 else f'FAIL x{fails}'}\n")

# ── TEST 2: format_user_error (new patterns) ──
print('[2] format_user_error (Gemini patterns)')
class ClientError(Exception):
    pass
errs = [
    Exception("404 NOT_FOUND model is no longer available"),
    Exception("FAILED_PRECONDITION File not in an ACTIVE state"),
    Exception("PERMISSION_DENIED"),
    ClientError("invalid_argument bad model"),
]
for exc in errs:
    msg = format_user_error(exc)
    print(f"   {type(exc).__name__:<13} → {msg[:80]}")
print()

# ── TEST 3: real MP4 video ingest (end-to-end Gemini) ──
print('[3] _ingest_video — real MP4 10.4MB')
mp4 = r'D:\PDB\uploads\93cee58f-2c2\9bf127d2-a9c_15192922_1080_1920_60fps.mp4'
t3_ok = False
if os.path.exists(mp4):
    async def t3():
        t0 = time.time()
        text = await ai_ingest._ingest_video(mp4, '.mp4')
        el = time.time() - t0
        ok = not any(m in text for m in ['[AI ingest error', '404', 'NOT_FOUND', 'FAILED_PRECONDITION'])
        prev = text[:80].replace(chr(10), ' ')
        print(f"   {'✓' if ok else '✗'} {el:.1f}s · {len(text)} chars · {prev}")
        return ok
    t3_ok = asyncio.run(t3())
else:
    print(f"   - MP4 missing ({mp4})")
    t3_ok = True
print()

# ── TEST 4: real JPG image ingest (Vision path) ──
print('[4] _ingest_image_smart — real JPG 691KB')
jpg = r'D:\PDB\uploads\93cee58f-2c2\d9c6baae-e80_dFQROr7oWzulq5Fa6rYsb1TIDQVacB9v8AYn4ytvb7rAj7XA1cBUilfQMpygAU46hH0.jpg'
t4_ok = False
if os.path.exists(jpg):
    async def t4():
        t0 = time.time()
        text = await ai_ingest.ingest_via_ai(jpg, 'jpg')
        el = time.time() - t0
        ok = not text.startswith('[AI') and len(text) > 100
        prev = text[:80].replace(chr(10), ' ')
        print(f"   {'✓' if ok else '✗'} {el:.1f}s · {len(text)} chars · {prev}")
        return ok
    t4_ok = asyncio.run(t4())
else:
    print(f"   - JPG missing ({jpg})")
    t4_ok = True
print()

# ── TEST 5: is_ai_format routing ──
print('[5] is_ai_format routing')
expected = {
    'jpg': True, 'png': True, 'heic': True, 'webp': True,
    'mp4': True, 'mov': True,
    'mp3': True, 'wav': True,
    'pdf': False, 'docx': False, 'txt': False,
}
fails5 = 0
for ext, want in expected.items():
    got = ai_ingest.is_ai_format(ext)
    if got != want:
        fails5 += 1
        print(f"   ✗ {ext}: {got} (want={want})")
print(f"   {'PASS' if fails5==0 else f'FAIL x{fails5}'}\n")

# ── TEST 6: live server endpoints ──
print('[6] Live server endpoints')
import urllib.request
import json
def get(p):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:8000{p}', timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None
status, body = get('/openapi.json')
print(f"   GET /openapi.json → {status} · APP_VERSION={body['info']['version']}")
status, body = get('/api/healthz/queue')
print(f"   GET /api/healthz/queue → {status} · worker={body['worker']['status']} · queue={body['queue']}")
print()

all_pass = (fails == 0 and t3_ok and t4_ok and fails5 == 0)
print(f"═══ RESULT: {'✓ ALL PASS' if all_pass else '✗ FAILS'} ═══")
sys.exit(0 if all_pass else 2)
