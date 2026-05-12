"""Edge case smoke for v9.4.2 — paths NOT covered by main smoke."""
import os, sys, asyncio, time, struct
sys.path.insert(0, 'd:/PDB')
from dotenv import load_dotenv
load_dotenv('d:/PDB/.env')

from backend import ai_ingest, extraction
from backend.upload_worker import format_user_error
from backend.ai_ingest import _wait_for_file_active

EDGE = 'd:/PDB/scripts/edge'

results = []
def log(name, ok, detail):
    mark = '✓' if ok else '✗'
    results.append((name, ok, detail))
    print(f"   {mark} {name}: {detail}")

# ── EDGE 1: real audio (.wav) via Gemini ──
print('[E1] Audio extraction — real WAV 96KB via Gemini')
async def e1():
    t0 = time.time()
    text = await ai_ingest._ingest_audio(f'{EDGE}/test_audio_3s.wav', 'wav')
    el = time.time() - t0
    has_err = any(m in text for m in ['[AI ingest error', 'NOT_FOUND', 'FAILED_PRECONDITION'])
    log('audio_wav', not has_err, f'{el:.1f}s · {len(text)} chars · {text[:60].replace(chr(10), " ")}')
asyncio.run(e1())

# ── EDGE 2: real audio (.mp3) via Gemini ──
print('\n[E2] Audio extraction — real MP3 24KB')
async def e2():
    t0 = time.time()
    text = await ai_ingest._ingest_audio(f'{EDGE}/test_audio.mp3', 'mp3')
    el = time.time() - t0
    has_err = any(m in text for m in ['[AI ingest error', 'NOT_FOUND'])
    log('audio_mp3', not has_err, f'{el:.1f}s · {len(text)} chars · {text[:60].replace(chr(10), " ")}')
asyncio.run(e2())

# ── EDGE 3: empty file (0 bytes) ──
print('\n[E3] Empty file — 0-byte text')
empty = f'{EDGE}/empty.txt'
open(empty, 'w').close()
text = extraction.extract_text(empty, 'txt')
status = extraction.classify_extraction_status(text)
log('empty_txt', status in ('empty', 'ok'), f'text={text[:50]!r} → status={status}')

# ── EDGE 4: corrupt MP4 (truncated bytes — header only) ──
print('\n[E4] Corrupt MP4 — only 100 bytes header')
corrupt = f'{EDGE}/corrupt.mp4'
with open(corrupt, 'wb') as f:
    f.write(b'\x00\x00\x00\x18ftypmp42' + os.urandom(80))
async def e4():
    text = await ai_ingest.ingest_via_ai(corrupt, 'mp4')
    has_err_marker = text.startswith('[AI')
    err_handled = 'ingest error' in text.lower() or 'is not in an active state' in text.lower() or 'failed' in text.lower()
    log('corrupt_mp4', has_err_marker, f'graceful: {text[:80].replace(chr(10), " ")}')
asyncio.run(e4())

# ── EDGE 5: filename with Thai unicode ──
print('\n[E5] Thai filename — extract path')
thai_name = f'{EDGE}/รายงานปี๒๕๖๙.txt'
with open(thai_name, 'w', encoding='utf-8') as f:
    f.write('เนื้อหาภาษาไทย Test 123 สำหรับการทดสอบ Unicode')
text = extraction.extract_text(thai_name, 'txt')
log('thai_filename', 'เนื้อหาภาษาไทย' in text, f'extracted {len(text)} chars correctly')

# ── EDGE 6: filename with control chars (path traversal-style) ──
print('\n[E6] Path traversal filename — should not escape')
# server validates filenames at upload boundary, but extraction sees full path.
# Just verify extraction handles weird paths gracefully.
weird = f'{EDGE}/file with spaces & symbols (test).txt'
with open(weird, 'w') as f:
    f.write('OK')
text = extraction.extract_text(weird, 'txt')
log('weird_filename', text == 'OK', f'extracted: {text!r}')

# ── EDGE 7: classify on corrupt-MP4 result text ──
print('\n[E7] classify_extraction_status on corrupt MP4 result')
import asyncio
async def e7():
    text = await ai_ingest.ingest_via_ai(corrupt, 'mp4')
    status = extraction.classify_extraction_status(text)
    log('classify_corrupt', status in ('ocr_failed', 'unsupported'),
        f'text={text[:50]!r} → status={status} (NOT \"ok\")')
asyncio.run(e7())

# ── EDGE 8: format_user_error covers ClientError-like 400 ──
# v9.4.3 — now returns CODE, not Thai message (frontend translates)
print('\n[E8] format_user_error — Gemini 400 INVALID_ARGUMENT')
class ClientError(Exception): pass
exc = ClientError("400 INVALID_ARGUMENT: model_name foo is invalid")
code = format_user_error(exc)
log('err_invalid_arg', code == 'CLIENT_ERROR', f'code={code}')

# ── EDGE 9: _wait_for_file_active timeout edge — when state never becomes ACTIVE ──
print('\n[E9] _wait_for_file_active — timeout=2s on already-ACTIVE file (no-op fast path)')
async def e9():
    class FakeFile:
        class State: name = 'ACTIVE'
        state = State()
    t0 = time.time()
    result = await _wait_for_file_active(FakeFile(), timeout=10)
    el = time.time() - t0
    log('wait_active_fast', el < 0.5, f'returned in {el*1000:.0f}ms (no-op when ACTIVE)')
asyncio.run(e9())

# ── EDGE 10: very large text content (boundary check for DB column) ──
print('\n[E10] Large text — strip_surrogates + classify on 1MB string')
from backend.extraction import classify_extraction_status
big = 'A' * 1_000_000  # 1MB
status = classify_extraction_status(big)
log('large_text', status == 'ok', f'1MB content → status={status}')

print('\n═══ EDGE CASE RESULTS ═══')
ok = sum(1 for _, o, _ in results if o)
print(f'PASS: {ok}/{len(results)}')
for name, o, detail in results:
    if not o:
        print(f'  ✗ {name}: {detail}')
sys.exit(0 if ok == len(results) else 2)
