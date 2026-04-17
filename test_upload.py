"""End-to-end test: Upload real files → Organize with AI → Test Chat"""
import httpx
import os

BASE = "http://localhost:8000"

def main():
    # 1. Reset
    print("=== Resetting old data ===")
    r = httpx.delete(f"{BASE}/api/reset", timeout=10)
    print(f"  Reset: {r.status_code} {r.json()}")

    # 2. Upload real spec files
    files_to_upload = [
        r"c:\Users\meuok\Desktop\PDB\PRD.md",
        r"c:\Users\meuok\Desktop\PDB\สปกโปรเจ็ค.md",
    ]

    upload_files = []
    for fp in files_to_upload:
        if os.path.exists(fp):
            fname = os.path.basename(fp)
            upload_files.append(("files", (fname, open(fp, "rb"))))
            print(f"  Found: {fname}")
        else:
            print(f"  NOT FOUND: {fp}")

    print(f"\n=== Uploading {len(upload_files)} files ===")
    r = httpx.post(f"{BASE}/api/upload", files=upload_files, timeout=30)
    print(f"  Status: {r.status_code}")
    for f in r.json().get("uploaded", []):
        print(f"  ✓ {f['filename']} — {f['text_length']} chars extracted")

    # 3. Organize with AI (this calls the LLM!)
    print(f"\n=== Organizing with AI ===")
    print("  Calling LLM for clustering + scoring + summaries...")
    print("  This may take 30-90 seconds, please wait...")
    r = httpx.post(f"{BASE}/api/organize", timeout=300)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  Result: {r.json()}")
    else:
        print(f"  ERROR: {r.text[:500]}")
        return

    # 4. Check clusters
    print(f"\n=== Results ===")
    r = httpx.get(f"{BASE}/api/clusters", timeout=10)
    data = r.json()
    print(f"  Clusters: {data['total_clusters']}")
    print(f"  Files: {data['total_files']}")
    print(f"  Ready: {data['total_ready']}")
    for c in data.get("clusters", []):
        print(f"\n  📁 {c['title']}")
        print(f"     {c['summary'][:120]}")
        for f in c.get("files", []):
            label = f.get('importance_label', '?')
            primary = " ⭐PRIMARY" if f.get('is_primary') else ""
            print(f"     - {f['filename']} [{label}]{primary}")

    # 5. Test chat
    print(f"\n=== Testing AI Chat ===")
    question = "สรุปประเด็นสำคัญของโปรเจกต์นี้ให้หน่อย"
    print(f"  Q: {question}")
    r = httpx.post(f"{BASE}/api/chat", json={"question": question}, timeout=120)
    if r.status_code == 200:
        chat = r.json()
        print(f"\n  Answer:\n  {chat['answer'][:600]}")
        if chat.get('cluster'):
            print(f"\n  Cluster: {chat['cluster']['title']}")
        print(f"  Files: {[f['filename'] for f in chat.get('files_used', [])]}")
        print(f"  Modes: {chat.get('retrieval_modes', {})}")
    else:
        print(f"  Chat error: {r.status_code} {r.text[:300]}")

    print("\n✅ DONE — Open http://localhost:8000 in your browser to see everything!")

if __name__ == "__main__":
    main()
