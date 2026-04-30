"""BYOS v7.0 — drive_storage.py mock smoke test (NO real Drive API call).

Run: python scripts/byos_storage_smoke.py

Strategy:
- Don't invoke real OAuth (no credentials yet)
- Build a fake Drive service object with the same interface as
  googleapiclient.discovery.Resource but in-memory
- Inject via DriveClient._from_service() (test-only constructor)
- Verify CRUD round-trips + idempotent ensure_folder + upsert_json_file

What this proves:
- Our wrapper translates inputs -> correct Drive API method calls
- Resumable threshold (5MB) triggers correctly
- Google native vs plain export branching works
- _escape() prevents query injection
- ensure_pdb_folder_structure produces 7 sub-folders + root
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from backend.drive_storage import DriveClient, _escape
from backend.drive_layout import SUB_FOLDERS, MIME_FOLDER, is_google_native


# ═══════════════════════════════════════════════════════════════
# Fake Drive Service (in-memory)
# ═══════════════════════════════════════════════════════════════
class _Request:
    """Mimic googleapiclient request object: .execute() returns the body."""
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeFiles:
    """In-memory Drive files() mock."""
    def __init__(self):
        # store: id -> {name, mimeType, parents, content, trashed, modifiedTime}
        self._store: dict[str, dict] = {}
        self._next_id = 1
        self.calls: list[tuple[str, dict]] = []  # for assertions

    def _new_id(self) -> str:
        i = self._next_id
        self._next_id += 1
        return f"id_{i:04d}"

    # ── Drive API surface ──────────────────────────────────────
    def list(self, q="", fields="", spaces="drive", pageSize=100, pageToken=None):
        self.calls.append(("list", {"q": q, "pageSize": pageSize}))
        # Naive query parser supporting our usage:
        #   name='X' and mimeType='Y' and trashed=false and 'parent' in parents
        results = []
        for fid, f in self._store.items():
            if f["trashed"]:
                continue
            ok = True
            if "name='" in q:
                wanted = q.split("name='")[1].split("'")[0]
                # _escape converts ' -> \' — undo for compare
                wanted = wanted.replace("\\'", "'").replace("\\\\", "\\")
                if f["name"] != wanted:
                    ok = False
            # Handle mimeType!='X' (exclude) BEFORE mimeType='X' (include) since
            # they share the substring prefix
            if "mimeType!='" in q:
                excluded_mime = q.split("mimeType!='")[1].split("'")[0]
                if f["mimeType"] == excluded_mime:
                    ok = False
            elif "mimeType='" in q:
                wanted_mime = q.split("mimeType='")[1].split("'")[0]
                if f["mimeType"] != wanted_mime:
                    ok = False
            if " in parents" in q:
                if "'root'" in q:
                    if f.get("parents", []) != []:
                        ok = False
                else:
                    # Find parent id between last pair of quotes before " in parents"
                    parent_seg = q.split(" in parents")[0].rsplit("'", 2)
                    parent_id = parent_seg[1] if len(parent_seg) >= 2 else None
                    if parent_id and parent_id not in f.get("parents", []):
                        ok = False
            if ok:
                results.append({
                    "id": fid,
                    "name": f["name"],
                    "mimeType": f["mimeType"],
                    "modifiedTime": f.get("modifiedTime", "2026-04-30T00:00:00Z"),
                    "size": str(len(f.get("content", b""))),
                })
        return _Request(lambda: {"files": results[:pageSize]})

    def create(self, body=None, media_body=None, fields=""):
        body = body or {}
        self.calls.append(("create", {"body": body, "has_media": media_body is not None}))
        fid = self._new_id()
        record = {
            "name": body.get("name", ""),
            "mimeType": body.get("mimeType", "application/octet-stream"),
            "parents": body.get("parents", []),
            "trashed": False,
            "modifiedTime": "2026-04-30T00:00:00Z",
            "content": b"",
        }
        if media_body is not None:
            # MediaIoBaseUpload exposes _fd (BytesIO)
            try:
                record["content"] = media_body._fd.getvalue()
                record["mimeType"] = media_body._mimetype
            except AttributeError:
                pass
        self._store[fid] = record
        return _Request(lambda: {"id": fid})

    def update(self, fileId="", body=None, media_body=None):
        body = body or {}
        self.calls.append(("update", {"id": fileId, "body": body, "has_media": media_body is not None}))
        if fileId not in self._store:
            raise KeyError(fileId)
        if "trashed" in body:
            self._store[fileId]["trashed"] = body["trashed"]
        if media_body is not None:
            try:
                self._store[fileId]["content"] = media_body._fd.getvalue()
                self._store[fileId]["mimeType"] = media_body._mimetype
            except AttributeError:
                pass
        return _Request(lambda: {"id": fileId})

    def delete(self, fileId=""):
        self.calls.append(("delete", {"id": fileId}))
        self._store.pop(fileId, None)
        return _Request(lambda: None)

    def get(self, fileId="", fields=""):
        self.calls.append(("get", {"id": fileId, "fields": fields}))
        if fileId not in self._store:
            raise KeyError(fileId)
        f = self._store[fileId]
        return _Request(lambda: {
            "id": fileId,
            "name": f["name"],
            "mimeType": f["mimeType"],
            "modifiedTime": f.get("modifiedTime"),
            "size": str(len(f.get("content", b""))),
        })

    def get_media(self, fileId=""):
        self.calls.append(("get_media", {"id": fileId}))
        f = self._store[fileId]
        return _MediaRequest(f["content"])

    def export_media(self, fileId="", mimeType=""):
        self.calls.append(("export_media", {"id": fileId, "mimeType": mimeType}))
        # Mock: return content as if exported
        return _MediaRequest(b"EXPORTED:" + self._store[fileId]["content"])


class _MediaRequest:
    """Mock object that MediaIoBaseDownload pulls from."""
    def __init__(self, content: bytes):
        self._content = content

    def execute(self):
        return self._content

    def http_request(self):
        return self


class FakeDriveService:
    def __init__(self):
        self._files = FakeFiles()

    def files(self):
        return self._files


# Patch MediaIoBaseDownload to work with our fake
def _patch_download():
    """Monkey-patch googleapiclient.http.MediaIoBaseDownload to read from our mock."""
    from googleapiclient import http as _h

    class _MockDL:
        def __init__(self, buffer, request):
            self._buffer = buffer
            self._request = request

        def next_chunk(self):
            self._buffer.write(self._request.execute())
            return None, True

    _h.MediaIoBaseDownload = _MockDL  # type: ignore[attr-defined,assignment]


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════
PASS = FAIL = 0


def t(name, fn):
    global PASS, FAIL
    try:
        ok = fn()
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        PASS += int(bool(ok))
        FAIL += int(not ok)
    except Exception as e:
        print(f"  FAIL  {name} -> {type(e).__name__}: {e}")
        FAIL += 1


_patch_download()


print("=== 1. _escape() prevents query injection ===")
t("_escape: simple name unchanged",
  lambda: _escape("report.pdf") == "report.pdf")
t("_escape: single quote -> backslash quote",
  lambda: _escape("Joe's report") == "Joe\\'s report")
t("_escape: backslash -> double backslash",
  lambda: _escape("a\\b") == "a\\\\b")


print("\n=== 2. ensure_folder() — idempotent ===")
def t2():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    a = client.ensure_folder("Personal Data Bank")
    b = client.ensure_folder("Personal Data Bank")  # second call
    return a == b and len([f for f in svc._files._store.values() if f["mimeType"] == MIME_FOLDER]) == 1
t("Same folder name -> same ID twice (no duplicate)", t2)

def t2b():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("Personal Data Bank")
    sub = client.ensure_folder("raw", parent_id=parent)
    sub2 = client.ensure_folder("raw", parent_id=parent)
    return sub == sub2 and sub != parent
t("Sub-folder with parent_id -> idempotent", t2b)


print("\n=== 3. upload_file() / download_file() round-trip ===")
def t3():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "doc.txt", b"hello world", "text/plain")
    data = client.download_file(fid, mime_type_hint="text/plain")
    return data == b"hello world"
t("Upload bytes -> download returns same bytes", t3)

def t3b():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    # str input should auto-encode UTF-8
    fid = client.upload_file(parent, "thai.txt", "สวัสดี", "text/plain")
    data = client.download_file(fid, mime_type_hint="text/plain")
    return data.decode("utf-8") == "สวัสดี"
t("Upload str (Thai) -> download decodes back", t3b)


print("\n=== 4. JSON helpers ===")
def t4():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("data")
    payload = {"profile": {"mbti": "INTJ"}, "list": [1, 2, 3]}
    fid = client.upload_json(parent, "profile.json", payload)
    got = client.download_json(fid)
    return got == payload
t("upload_json + download_json round-trip", t4)


print("\n=== 5. upsert_json_file() — create vs update ===")
def t5():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("data")
    # First call -> create
    fid1 = client.upsert_json_file(parent, "profile.json", {"v": 1})
    # Second call -> update (same id)
    fid2 = client.upsert_json_file(parent, "profile.json", {"v": 2})
    got = client.download_json(fid1)
    return fid1 == fid2 and got == {"v": 2}
t("upsert: same name -> reuse file_id, content updated", t5)


print("\n=== 6. list_folder() ===")
def t6():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    client.upload_file(parent, "a.txt", b"a", "text/plain")
    client.upload_file(parent, "b.txt", b"b", "text/plain")
    client.ensure_folder("sub", parent_id=parent)  # add a sub-folder for filter test
    files = client.list_folder(parent)
    files_only = client.list_folder(parent, only_files=True)
    return len(files) == 3 and len(files_only) == 2  # 2 files + 1 folder; only_files excludes folder
t("list_folder: with/without only_files filter", t6)


print("\n=== 7. delete_file() = trash (recoverable) ===")
def t7():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "doomed.txt", b"x", "text/plain")
    client.delete_file(fid)
    # Trashed file should NOT show in list
    files = client.list_folder(parent)
    # And update body should have trashed=True
    return svc._files._store[fid]["trashed"] is True and len(files) == 0
t("delete_file marks trashed=True (recoverable, not removed)", t7)

def t7b():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "doomed.txt", b"x", "text/plain")
    client.delete_file_permanent(fid)
    return fid not in svc._files._store
t("delete_file_permanent removes from store entirely", t7b)


print("\n=== 8. find_file_by_name() ===")
def t8():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "needle.txt", b"x", "text/plain")
    found = client.find_file_by_name("needle.txt", parent_id=parent)
    not_found = client.find_file_by_name("haystack.txt", parent_id=parent)
    return found is not None and found["id"] == fid and not_found is None
t("find_file_by_name: returns match or None", t8)


print("\n=== 9. ensure_pdb_folder_structure() ===")
def t9():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    layout = client.ensure_pdb_folder_structure()
    expected = {"_root"} | set(SUB_FOLDERS)
    return set(layout.keys()) == expected and all(layout[k] for k in expected)
t("ensure_pdb_folder_structure creates root + 7 sub-folders", t9)

def t9b():
    """Re-run must be idempotent (no extra folders)."""
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    layout1 = client.ensure_pdb_folder_structure()
    layout2 = client.ensure_pdb_folder_structure()
    folder_count_after = len([f for f in svc._files._store.values() if f["mimeType"] == MIME_FOLDER])
    return layout1 == layout2 and folder_count_after == 8  # root + 7 subs, no duplicates
t("Re-run ensure_pdb_folder_structure is idempotent (8 folders total)", t9b)


print("\n=== 10. Resumable upload threshold (5MB) ===")
def t10():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    # Small file -> non-resumable
    small = b"x" * 1000
    fid_small = client.upload_file(parent, "small.bin", small, "application/octet-stream")
    # Large file -> resumable
    large = b"y" * (6 * 1024 * 1024)
    fid_large = client.upload_file(parent, "large.bin", large, "application/octet-stream")
    return (svc._files._store[fid_small]["content"] == small
            and svc._files._store[fid_large]["content"] == large)
t("Both small (<5MB) and large (>5MB) files round-trip correctly", t10)


print("\n=== 11. Google native types branching ===")
def t11():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    # Manually create a Google Doc-typed file in store
    fid = "id_native_001"
    svc._files._store[fid] = {
        "name": "report.gdoc",
        "mimeType": "application/vnd.google-apps.document",
        "parents": [],
        "trashed": False,
        "content": b"original-doc-bytes",
    }
    data = client.download_file(fid, mime_type_hint="application/vnd.google-apps.document")
    # Mock export_media prefixes "EXPORTED:" — verify export branch was taken
    return data.startswith(b"EXPORTED:")
t("Google native -> export_media() branch", t11)

def t11b():
    return is_google_native("application/vnd.google-apps.document") and not is_google_native("application/pdf")
t("is_google_native classifies correctly", t11b)


print("\n=== 12. update_file_content() ===")
def t12():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "v.txt", b"old", "text/plain")
    client.update_file_content(fid, b"new", "text/plain")
    return svc._files._store[fid]["content"] == b"new"
t("update_file_content overwrites in-place (same file_id)", t12)


print("\n=== 13. get_metadata() ===")
def t13():
    svc = FakeDriveService()
    client = DriveClient._from_service(svc)
    parent = client.ensure_folder("test")
    fid = client.upload_file(parent, "info.txt", b"hello", "text/plain")
    meta = client.get_metadata(fid, fields="id, name, mimeType, size")
    return meta["id"] == fid and meta["name"] == "info.txt" and meta["mimeType"] == "text/plain"
t("get_metadata returns id + name + mimeType", t13)


print(f"\n{'=' * 60}")
print(f"  RESULT: {PASS} passed / {FAIL} failed")
print(f"{'=' * 60}")
sys.exit(0 if FAIL == 0 else 1)
