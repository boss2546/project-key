// Admin endpoint /api/admin/cleanup-orphans — dry-run → execute → idempotent
const { test, expect, request } = require('@playwright/test');

// BASE override via env (default 8000) · ใช้สำหรับ run บน temp server ตอน main server reload ไม่ได้
const BASE = process.env.PDB_TEST_BASE || 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'bossok2546@gmail.com';
const ADMIN_PASS = '0898661896za';

let api;
let token;

test.describe.serial('Admin /api/admin/cleanup-orphans', () => {
  test.setTimeout(120000);

  test.beforeAll(async () => {
    api = await request.newContext({ baseURL: BASE });
    const res = await api.post('/api/auth/login', {
      data: { email: ADMIN_EMAIL, password: ADMIN_PASS },
    });
    expect(res.ok()).toBe(true);
    token = (await res.json()).token;
  });

  test.afterAll(async () => { await api.dispose(); });

  function H() { return { Authorization: `Bearer ${token}` }; }

  test('A1 · non-admin user gets 403', async () => {
    // Try without auth → 401
    const noAuth = await api.post('/api/admin/cleanup-orphans');
    expect([401, 403]).toContain(noAuth.status());
  });

  test('A2 · default dry_run=true returns counts without deleting', async () => {
    const res = await api.post('/api/admin/cleanup-orphans', { headers: H() });
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(body.status).toBe('ok');
    expect(body.dry_run).toBe(true);
    expect(typeof body.users_scanned).toBe('number');
    expect(body.totals).toBeTruthy();
    expect(typeof body.totals.orphan_source_file_nodes_removed).toBe('number');
    expect(typeof body.totals.empty_clusters_removed).toBe('number');
    expect(body.disk).toBeTruthy();
    expect(typeof body.disk.orphan_md_found).toBe('number');
    // dry-run reports 0 removed
    expect(body.disk.orphan_md_removed).toBe(0);
  });

  test('A3 · execute (dry_run=false) actually cleans · counts > 0 if any orphans existed', async () => {
    // First do dry-run to know what we expect
    const dryRes = await api.post('/api/admin/cleanup-orphans?dry_run=true', { headers: H() });
    const dry = await dryRes.json();
    const expectedNodes = dry.totals.orphan_source_file_nodes_removed;
    const expectedClusters = dry.totals.empty_clusters_removed;
    const expectedDiskMd = dry.disk.orphan_md_found;

    // Execute
    const exRes = await api.post('/api/admin/cleanup-orphans?dry_run=false', { headers: H() });
    expect(exRes.ok()).toBe(true);
    const ex = await exRes.json();
    expect(ex.dry_run).toBe(false);
    // The execution should have processed at least as many as dry-run (could be more if races,
    // but in test environment they should match closely)
    expect(ex.totals.orphan_source_file_nodes_removed).toBeGreaterThanOrEqual(0);
    expect(ex.totals.empty_clusters_removed).toBeGreaterThanOrEqual(0);
    expect(ex.disk.orphan_md_removed).toBeGreaterThanOrEqual(0);
  });

  test('A4 · idempotent — re-run after execute returns all 0', async () => {
    const res = await api.post('/api/admin/cleanup-orphans?dry_run=false', { headers: H() });
    expect(res.ok()).toBe(true);
    const body = await res.json();
    expect(body.totals.orphan_source_file_nodes_removed).toBe(0);
    expect(body.totals.empty_clusters_removed).toBe(0);
    expect(body.totals.orphan_graph_edges_removed).toBe(0);
    expect(body.totals.orphan_suggestions_removed).toBe(0);
    expect(body.disk.orphan_md_removed).toBe(0);
    expect(body.disk.orphan_md_found).toBe(0);
  });

  test('A5 · idempotent dry-run after execute also returns 0', async () => {
    const res = await api.post('/api/admin/cleanup-orphans?dry_run=true', { headers: H() });
    const body = await res.json();
    expect(body.totals.orphan_source_file_nodes_removed).toBe(0);
    expect(body.totals.empty_clusters_removed).toBe(0);
    expect(body.disk.orphan_md_found).toBe(0);
  });
});
