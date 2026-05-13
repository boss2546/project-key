"""v9.4.3 smoke — error codes, i18n boundary, reprocess hardening."""
import os, sys, asyncio, time
sys.path.insert(0, 'd:/PDB')
from dotenv import load_dotenv
load_dotenv('d:/PDB/.env')

from backend.upload_worker import format_user_error, ERROR_CODES, MAX_RETRY_ATTEMPTS

print('═══ V9.4.3 SMOKE ═══\n')
fails = 0

# ── 1. format_user_error returns CODE for each pattern ──
print('[1] format_user_error → CODE')
class ClientError(Exception): pass
cases = [
    (Exception("encrypted file"),                           "ENCRYPTED"),
    (FileNotFoundError("no such file or directory: x.pdf"),  "FILE_MISSING"),
    (TimeoutError("timed out waiting"),                      "TIMEOUT"),
    (MemoryError("out of memory"),                           "OUT_OF_MEMORY"),
    (UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"),  "ENCODING"),
    (Exception("Quota exceeded"),                            "QUOTA_EXCEEDED"),
    (Exception("google api 503 unavailable"),                "GEMINI_UNAVAILABLE"),
    (Exception("google auth failed"),                        "GEMINI_AUTH"),
    (Exception("404 NOT_FOUND no longer available"),         "MODEL_DEPRECATED"),
    (Exception("FAILED_PRECONDITION not in an active state"),"FILE_NOT_ACTIVE"),
    (Exception("PERMISSION_DENIED"),                         "PERMISSION_DENIED"),
    (ClientError("invalid_argument bad model"),              "CLIENT_ERROR"),
    (Exception("tesseract is not installed"),                "OCR_FAIL"),
    (Exception("connection refused"),                        "NETWORK"),
    (Exception("random unknown failure"),                    "UNKNOWN"),
]
for exc, want in cases:
    got = format_user_error(exc)
    ok = '✓' if got == want else '✗'
    if got != want: fails += 1
    print(f"   {ok} {type(exc).__name__:<22} '{str(exc)[:38]:<40}' → {got} (want={want})")
print(f"   {'PASS' if fails==0 else f'FAIL x{fails}'}\n")

# ── 2. ERROR_CODES has all returned codes + each has TH/EN tuple ──
print('[2] ERROR_CODES coverage + structure')
returned_codes = set(format_user_error(exc) for exc, _ in cases)
missing = returned_codes - set(ERROR_CODES.keys())
if missing:
    fails += 1
    print(f"   ✗ codes returned but no entry: {missing}")
else:
    print(f"   ✓ all {len(returned_codes)} returned codes have ERROR_CODES entries")

bad_struct = [k for k, v in ERROR_CODES.items()
              if not (isinstance(v, tuple) and len(v) == 2 and all(isinstance(x, str) for x in v))]
if bad_struct:
    fails += 1
    print(f"   ✗ malformed entries: {bad_struct}")
else:
    print(f"   ✓ all {len(ERROR_CODES)} entries are (TH, EN) tuples")
print()

# ── 3. Frontend ERROR_CODE_LABELS mirrors backend ──
print('[3] Frontend ERROR_CODE_LABELS in app.js mirrors backend')
import re
with open('d:/PDB/legacy-frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()
m = re.search(r'const ERROR_CODE_LABELS = \{(.+?)\};', js, re.DOTALL)
if not m:
    fails += 1
    print('   ✗ ERROR_CODE_LABELS not found in app.js')
else:
    block = m.group(1)
    fe_codes = set(re.findall(r'^\s*([A-Z_]+):\s*\{', block, re.MULTILINE))
    be_codes = set(ERROR_CODES.keys())
    only_be = be_codes - fe_codes
    only_fe = fe_codes - be_codes
    if only_be or only_fe:
        fails += 1
        print(f'   ✗ mismatch — only_backend={only_be}, only_frontend={only_fe}')
    else:
        print(f'   ✓ {len(fe_codes)} codes match between backend + frontend')
print()

# ── 4. Frontend STEP_TRANSLATIONS_EN coverage ──
print('[4] Frontend STEP_TRANSLATIONS_EN regex sanity')
m = re.search(r'const STEP_TRANSLATIONS_EN = \[(.+?)\];', js, re.DOTALL)
if not m:
    fails += 1
    print('   ✗ STEP_TRANSLATIONS_EN not found')
else:
    block = m.group(1)
    n_patterns = len(re.findall(r'\[/.+?/,', block))
    if n_patterns >= 10:
        print(f'   ✓ {n_patterns} regex patterns defined')
    else:
        fails += 1
        print(f'   ✗ only {n_patterns} patterns (expected ≥10)')
print()

# ── 5. localizeError + localizeBackendStep helpers exist ──
print('[5] Frontend helpers exist')
for fn in ['localizeError', 'localizeBackendStep']:
    if f'function {fn}' in js:
        print(f'   ✓ {fn}()')
    else:
        fails += 1
        print(f'   ✗ {fn}() missing')
print()

# ── 6. reprocess endpoint: MAX_RETRY check + clear text ──
print('[6] reprocess endpoint hardening')
with open('d:/PDB/backend/main.py', 'r', encoding='utf-8') as f:
    main_src = f.read()
checks = [
    ('extracted_text = ""',       'clears extracted_text'),
    ('extraction_status = ""',    'clears extraction_status'),
    ('attempt_count = (file.attempt_count or 0) + 1', 'increments attempt_count'),
    ('NOT_RETRYABLE',             '409 NOT_RETRYABLE on max'),
]
# we want all of these in the reprocess handler region
reproc_idx = main_src.find('reprocess_file:')
reproc_end = main_src.find('async def ', reproc_idx + 100)
reproc_block = main_src[reproc_idx:reproc_end] if reproc_idx > 0 else ''
for needle, desc in checks:
    if needle in reproc_block:
        print(f'   ✓ {desc}')
    else:
        fails += 1
        print(f'   ✗ {desc} (needle: {needle!r} not in reprocess block)')
print()

# ── 7. _mark_job_failed maps ENCRYPTED → encrypted extraction_status ──
print('[7] _mark_job_failed code→extraction_status mapping')
mark_idx = main_src.find('_mark_job_failed')  # main.py — none, this is in upload_worker
with open('d:/PDB/backend/upload_worker.py', 'r', encoding='utf-8') as f:
    worker_src = f.read()
mark_idx = worker_src.find('async def _mark_job_failed')
mark_end = worker_src.find('async def ', mark_idx + 50)
mark_block = worker_src[mark_idx:mark_end]
if 'msg == "ENCRYPTED"' in mark_block:
    print('   ✓ ENCRYPTED code maps to extraction_status="encrypted"')
else:
    fails += 1
    print('   ✗ ENCRYPTED code mapping missing')
print()

# ── 8. Existing edge cases still pass ──
print('[8] Re-run edge_cases.py')
import subprocess
try:
    r = subprocess.run([sys.executable, 'd:/PDB/scripts/edge/edge_cases.py'],
                       capture_output=True, text=True, timeout=240)
    if 'PASS: 10/10' in r.stdout:
        print('   ✓ 10/10 edge cases still pass')
    else:
        fails += 1
        last = r.stdout.strip().splitlines()[-3:]
        print(f'   ✗ edge tests degraded: {last}')
except Exception as e:
    fails += 1
    print(f'   ✗ edge tests crashed: {e}')
print()

print(f"═══ RESULT: {'✓ ALL PASS' if fails == 0 else f'✗ {fails} FAIL'} ═══")
sys.exit(0 if fails == 0 else 2)
