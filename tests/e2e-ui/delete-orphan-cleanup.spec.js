// End-to-end: upload file → organize → graph → delete → verify NO orphans left
// ทดสอบ fix สำหรับ MSG-DELETE-CASCADE-001 · v10.0.x
const { test, expect, request } = require('@playwright/test');

const BASE = 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'bossok2546@gmail.com';
const ADMIN_PASS = '0898661896za';

let token;
let api;

test.describe.serial('DELETE /api/files/{id} — orphan cleanup', () => {
  test.setTimeout(180000);  // 3 min · organize/graph build อาจช้าใน user ที่มีไฟล์เยอะ

  test.beforeAll(async () => {
    api = await request.newContext({ baseURL: BASE });
    const res = await api.post('/api/auth/login', {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASS },
    });
    expect(res.ok()).toBe(true);
    const body = await res.json();
    token = body.token;
  });

  test.afterAll(async () => {
    await api.dispose();
  });

  async function authReq(method, path, opts = {}) {
    return api.fetch(path, {
      method,
      headers: { Authorization: `Bearer ${token}`, ...(opts.headers || {}) },
      ...opts,
    });
  }

  test('D1 · upload → organize → graph contains node → DELETE → node gone', async () => {
    // ── Step 1: upload a small text file
    const uniqueTag = 'orphan_cleanup_test_' + Date.now();
    const filename = `orphan-test-${Date.now()}.txt`;
    const content = `${uniqueTag}\n` +
      `This is a test document for orphan cleanup verification.\n`.repeat(20);

    const uploadRes = await api.post('/api/upload', {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        files: { name: filename, mimeType: 'text/plain', buffer: Buffer.from(content) },
      },
    });
    expect(uploadRes.ok()).toBe(true);
    const uploadBody = await uploadRes.json();
    const fileId = uploadBody.uploaded?.[0]?.id || uploadBody.uploaded?.[0]?.file_id
                   || uploadBody.files?.[0]?.id;
    expect(fileId).toBeTruthy();

    // ── Step 2: wait for extraction (query /api/files แทน upload-status เพราะ upload-status
    // return เฉพาะ queued/extracting · file ที่ขึ้น "uploaded/organized" จะหายจาก list)
    let extracted = false;
    let finalStatus = null;
    for (let i = 0; i < 45; i++) {
      const fr = await authReq('GET', '/api/files');
      if (fr.ok()) {
        const fb = await fr.json();
        const list = fb.files || fb || [];
        const me = list.find(f => f.id === fileId);
        if (me) {
          finalStatus = me.processing_status;
          if (['uploaded', 'organized', 'ready'].includes(me.processing_status)) {
            extracted = true;
            break;
          }
          if (me.processing_status === 'error') {
            throw new Error('extraction error: ' + (me.extract_error || ''));
          }
        }
      }
      await new Promise(r => setTimeout(r, 1000));
    }
    expect(extracted, `extracted (last status=${finalStatus})`).toBe(true);

    // ── Step 3: build graph (force=true) → creates source_file node for the new file
    // ข้าม organize-new (ใช้เวลานานสำหรับ user ที่มีไฟล์เยอะ · graph node ก็เพียงพอ verify cleanup)
    const buildRes = await authReq('POST', '/api/graph/build?force=true');
    expect(buildRes.ok()).toBe(true);

    // ── Step 4: verify graph_node exists for this file
    const graphRes1 = await authReq('GET', '/api/graph/global');
    expect(graphRes1.ok()).toBe(true);
    const graphBefore = await graphRes1.json();
    const nodeForFile = (graphBefore.nodes || []).find(
      n => n.object_type === 'source_file' && n.object_id === fileId
    );
    expect(nodeForFile, `expected source_file graph node for ${fileId} before delete`).toBeTruthy();

    // ── Step 5: DELETE
    const delRes = await authReq('DELETE', `/api/files/${fileId}`);
    expect(delRes.ok()).toBe(true);

    // ── Step 6: verify graph_node GONE
    const graphRes2 = await authReq('GET', '/api/graph/global');
    expect(graphRes2.ok()).toBe(true);
    const graphAfter = await graphRes2.json();
    const stillThere = (graphAfter.nodes || []).find(
      n => n.object_type === 'source_file' && n.object_id === fileId
    );
    expect(stillThere, `graph node for deleted file ${fileId} should be gone`).toBeUndefined();

    // ── Step 7: verify edges touching that node are also gone
    const nodeIdsAfter = new Set((graphAfter.nodes || []).map(n => n.id));
    const orphanEdge = (graphAfter.edges || []).find(
      e => !nodeIdsAfter.has(e.source) || !nodeIdsAfter.has(e.target)
    );
    expect(orphanEdge, 'no edges should reference deleted nodes').toBeUndefined();

    // ── Step 8: verify file row gone
    const filesRes = await authReq('GET', '/api/files');
    expect(filesRes.ok()).toBe(true);
    const files = await filesRes.json();
    const stillFile = (files.files || files || []).find(f => f.id === fileId);
    expect(stillFile).toBeUndefined();
  });

  test('D2 · skip-duplicates also cleans orphans (regression: same gap)', async () => {
    // Create a file via upload
    const filename = `skip-orphan-${Date.now()}.txt`;
    const content = `skip dup test\n` + 'lorem ipsum dolor sit amet.\n'.repeat(15);
    const uploadRes = await api.post('/api/upload', {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        files: { name: filename, mimeType: 'text/plain', buffer: Buffer.from(content) },
      },
    });
    expect(uploadRes.ok()).toBe(true);
    const uploadBody = await uploadRes.json();
    const fileId = uploadBody.uploaded?.[0]?.id || uploadBody.uploaded?.[0]?.file_id
                   || uploadBody.files?.[0]?.id;
    expect(fileId).toBeTruthy();

    // wait extraction
    for (let i = 0; i < 30; i++) {
      const sr = await authReq('GET', '/api/upload-status');
      if (sr.ok()) {
        const sb = await sr.json();
        const me = (sb.items || []).find(it => it.file_id === fileId || it.id === fileId);
        if (!me || me.processing_status === 'uploaded' || me.processing_status === 'ready') break;
        if (me.processing_status === 'error') break;
      }
      await new Promise(r => setTimeout(r, 1000));
    }

    // build graph (force=true)
    await authReq('POST', '/api/graph/build?force=true');
    const graphRes1 = await authReq('GET', '/api/graph/global');
    const graphBefore = await graphRes1.json();
    const nodeBefore = (graphBefore.nodes || []).find(
      n => n.object_type === 'source_file' && n.object_id === fileId
    );
    expect(nodeBefore).toBeTruthy();

    // skip-duplicates (uses same delete flow) · use api.post() ตรงๆ เพื่อ auto JSON encoding
    const skipRes = await api.post('/api/files/skip-duplicates', {
      headers: { Authorization: `Bearer ${token}` },
      data: { file_ids: [fileId] },
    });
    if (!skipRes.ok()) {
      const errBody = await skipRes.text();
      throw new Error(`skip-duplicates failed ${skipRes.status()}: ${errBody}`);
    }
    const skipBody = await skipRes.json();
    expect(skipBody.deleted).toContain(fileId);

    // verify orphan gone
    const graphRes2 = await authReq('GET', '/api/graph/global');
    const graphAfter = await graphRes2.json();
    const nodeAfter = (graphAfter.nodes || []).find(
      n => n.object_type === 'source_file' && n.object_id === fileId
    );
    expect(nodeAfter).toBeUndefined();
  });
});
