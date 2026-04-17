"""
Full E2E test: Upload 3 new files → Organize → Chat → Verify multi-cluster
"""
import httpx
import time
import os

BASE = "http://localhost:8000"
timeout = httpx.Timeout(120.0)

print("=" * 60)
print("FULL E2E TEST — Upload New Files + Multi-Cluster")
print("=" * 60)

# Step 1: Check existing state
print("\n=== Current State ===")
r = httpx.get(f"{BASE}/api/stats", timeout=timeout)
stats = r.json()
print(f"  Before: {stats['total_files']} files, {stats['total_clusters']} clusters")

# Step 2: Upload 3 new files
print("\n=== Uploading 3 new files ===")
files_to_upload = [
    ("files", ("meeting_notes.md", open("test_files/meeting_notes.md", "rb"), "text/markdown")),
    ("files", ("tech_architecture.md", open("test_files/tech_architecture.md", "rb"), "text/markdown")),
    ("files", ("user_research.txt", open("test_files/user_research.txt", "rb"), "text/plain")),
]
r = httpx.post(f"{BASE}/api/upload", files=files_to_upload, timeout=timeout)
data = r.json()
for f in data.get("uploaded", []):
    print(f"  ✓ {f['filename']} — {f['text_length']} chars extracted")

# Step 3: Re-organize (now with 5 files total)
print("\n=== Re-organizing all 5 files with AI ===")
print("  This will take 60-120 seconds...")
start = time.time()
r = httpx.post(f"{BASE}/api/organize", timeout=timeout)
elapsed = time.time() - start
print(f"  Status: {r.status_code} (took {elapsed:.0f}s)")
print(f"  Result: {r.json()}")

# Step 4: Check results
print("\n=== Results ===")
r = httpx.get(f"{BASE}/api/stats", timeout=timeout)
stats = r.json()
print(f"  Total files:    {stats['total_files']}")
print(f"  Total clusters: {stats['total_clusters']}")
print(f"  Processed:      {stats['processed']}")
print(f"  Errors:         {stats['errors']}")

r = httpx.get(f"{BASE}/api/clusters", timeout=timeout)
clusters = r.json()
print(f"\n  📊 {len(clusters['clusters'])} clusters found:")
for cl in clusters["clusters"]:
    files_list = cl.get("files", [])
    print(f"\n  📁 {cl['title']}")
    print(f"     {cl['summary'][:100]}...")
    for f in files_list:
        primary = " ⭐PRIMARY" if f.get("is_primary") else ""
        print(f"     - {f['filename']} [{f.get('importance_label','?')}]{primary}")

# Step 5: Check summaries on disk
print("\n=== Summary .md files on disk ===")
summaries_dir = "summaries"
for fname in sorted(os.listdir(summaries_dir)):
    if fname.endswith(".summary.md"):
        fpath = os.path.join(summaries_dir, fname)
        size = os.path.getsize(fpath)
        # Read first few lines to check format
        with open(fpath, 'r', encoding='utf-8') as fp:
            first_lines = fp.readlines()[:3]
        has_frontmatter = first_lines[0].strip() == "---"
        print(f"  ✓ {fname} ({size} bytes) {'✅ YAML frontmatter' if has_frontmatter else '❌ no frontmatter'}")

# Step 6: Test AI Chat with cross-cluster question
print("\n=== Testing AI Chat (cross-cluster question) ===")
q1 = "ผู้ใช้มี pain points อะไรบ้าง และ MVP แก้ปัญหาอะไรได้"
print(f"  Q: {q1}")
r = httpx.post(f"{BASE}/api/chat", json={"question": q1}, timeout=timeout)
d = r.json()
print(f"\n  Answer (first 500 chars):")
print(f"  {d['answer'][:500]}")
print(f"\n  Cluster: {d.get('cluster',{}).get('title','N/A')}")
print(f"  Files: {[f['filename'] for f in d.get('files_used',[])]}")
print(f"  Modes: {d.get('retrieval_modes',{})}")

# Step 7: Another chat - technical question
print("\n=== Testing AI Chat (technical question) ===")
q2 = "Tech stack ของ Project KEY ใช้อะไรบ้าง อธิบายแต่ละ component"
print(f"  Q: {q2}")
r = httpx.post(f"{BASE}/api/chat", json={"question": q2}, timeout=timeout)
d = r.json()
print(f"\n  Answer (first 500 chars):")
print(f"  {d['answer'][:500]}")
print(f"\n  Cluster: {d.get('cluster',{}).get('title','N/A')}")
print(f"  Files: {[f['filename'] for f in d.get('files_used',[])]}")
print(f"  Modes: {d.get('retrieval_modes',{})}")

print("\n✅ FULL E2E TEST COMPLETE!")
print(f"   Open http://localhost:8000 to see {stats['total_files']} files across {stats['total_clusters']} clusters")
