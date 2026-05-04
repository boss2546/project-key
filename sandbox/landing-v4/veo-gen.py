"""
Flexible Veo video generator for PDB landing-v4.
─────────────────────────────────────────────────────────────────────────────
รัน:
    $env:GEMINI_API_KEY = "AIzaSy..."   # PowerShell
    python d:/PDB/sandbox/landing-v4/veo-gen.py prompts/01-hero.txt assets/01-hero.mp4

หรือ default mode (gen all 3 prompts):
    python d:/PDB/sandbox/landing-v4/veo-gen.py --all

Args:
    <prompt-file>  <output-mp4>   หรือ
    --all                          (gen ทุกตัวใน prompts/ ตามลำดับ)
    --model veo-3.0-generate-001   (default: veo-2.0-generate-001 — เสถียรสุด)
    --aspect 16:9                  (or 9:16 / 1:1)
    --duration 8                   (default 8s)
"""
import os
import sys
import json
import time
import argparse
import urllib.request
import urllib.error
import urllib.parse

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not KEY:
    print("ERROR: ตั้ง env var ก่อน — $env:GEMINI_API_KEY = \"AIzaSy...\"")
    sys.exit(1)

BASE = "https://generativelanguage.googleapis.com/v1beta"
HERE = os.path.dirname(os.path.abspath(__file__))


def http(method, url, body=None):
    req = urllib.request.Request(
        url, method=method,
        headers={"Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def gen_one(prompt_text, out_path, model="veo-2.0-generate-001", aspect="16:9", duration=8):
    print(f"\n═══ Generate: {os.path.basename(out_path)} ═══")
    print(f"  Model: {model}")
    print(f"  Aspect: {aspect}  Duration: {duration}s")
    print(f"  Prompt: {prompt_text[:120]}…")

    body = {
        "instances": [{"prompt": prompt_text}],
        "parameters": {
            "aspectRatio": aspect,
            "durationSeconds": duration,
            "sampleCount": 1,
            "personGeneration": "dont_allow",
        },
    }
    status, resp = http("POST", f"{BASE}/models/{model}:predictLongRunning?key={KEY}", body)
    if status != 200:
        print(f"  ✗ start failed HTTP {status}: {json.dumps(resp, indent=2)[:500]}")
        return False
    op_name = resp.get("name", "")
    print(f"  Operation: {op_name}")
    print("  Polling every 15s …")

    for i in range(20):  # max 5 min
        time.sleep(15)
        status, op = http("GET", f"{BASE}/{op_name}?key={KEY}")
        done = op.get("done", False)
        print(f"    poll {i+1}: done={done}")
        if done:
            if "error" in op:
                print(f"  ✗ error: {json.dumps(op['error'], indent=2)}")
                return False
            videos = op.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
            if not videos:
                print(f"  ✗ no video samples in response: {json.dumps(op, indent=2)[:600]}")
                return False
            uri = videos[0].get("video", {}).get("uri", "")
            if not uri:
                print(f"  ✗ no uri")
                return False
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            sep = "&" if "?" in uri else "?"
            full = uri if "key=" in uri else f"{uri}{sep}key={KEY}"
            req = urllib.request.Request(full)
            with urllib.request.urlopen(req, timeout=120) as r, open(out_path, "wb") as f:
                f.write(r.read())
            size = os.path.getsize(out_path) / 1024 / 1024
            print(f"  ✓ saved → {out_path} ({size:.2f} MB)")
            return True

    print("  ⚠ timeout 5 min")
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt_file", nargs="?", help="path to .txt file containing the prompt")
    p.add_argument("output_file", nargs="?", help="output mp4 path")
    p.add_argument("--all", action="store_true", help="gen all prompts/*.txt → assets/*.mp4")
    p.add_argument("--model", default="veo-2.0-generate-001")
    p.add_argument("--aspect", default="16:9")
    p.add_argument("--duration", type=int, default=8)
    args = p.parse_args()

    if args.all:
        prompts_dir = os.path.join(HERE, "prompts")
        assets_dir = os.path.join(HERE, "assets")
        files = sorted(f for f in os.listdir(prompts_dir) if f.endswith(".txt"))
        if not files:
            print(f"  ✗ no prompts in {prompts_dir}")
            sys.exit(1)
        for fname in files:
            base = os.path.splitext(fname)[0]
            prompt = open(os.path.join(prompts_dir, fname), "r", encoding="utf-8").read().strip()
            out = os.path.join(assets_dir, f"{base}.mp4")
            if os.path.exists(out):
                print(f"\n[skip] {out} already exists")
                continue
            ok = gen_one(prompt, out, args.model, args.aspect, args.duration)
            if not ok:
                print("  ✗ stopping on failure")
                sys.exit(1)
        print("\n✓ all prompts generated")
    else:
        if not args.prompt_file or not args.output_file:
            print("ERROR: usage:  veo-gen.py <prompt.txt> <output.mp4>   or   --all")
            sys.exit(1)
        prompt_path = args.prompt_file if os.path.isabs(args.prompt_file) else os.path.join(HERE, args.prompt_file)
        out_path = args.output_file if os.path.isabs(args.output_file) else os.path.join(HERE, args.output_file)
        if not os.path.exists(prompt_path):
            print(f"  ✗ prompt file not found: {prompt_path}")
            sys.exit(1)
        prompt = open(prompt_path, "r", encoding="utf-8").read().strip()
        ok = gen_one(prompt, out_path, args.model, args.aspect, args.duration)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
