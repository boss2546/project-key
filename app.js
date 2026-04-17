/* ════════════════════════════════════════════════════════════
   PROJECT KEY — Application Logic (MVP v2)
   Personal Data Space + AI Context Layer
   ════════════════════════════════════════════════════════════ */

const API_BASE = '';  // Same origin since FastAPI serves frontend

// ─── APP STATE ───
const state = {
  currentPage: 'my-data',
  files: [],
  clusters: [],
  contextPacks: [],
  chatMessages: [],
  profile: null,
  isOrganizing: false,
  selectedPackType: 'project'
};

// ─── DOM REFS ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── INITIALIZATION ───
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initUpload();
  initChat();
  initSummaryPanel();
  initProfilePanel();
  initCreatePackModal();
  loadFiles();
  loadStats();
  loadProfile();
  loadContextPacks();
});

// ════════════════════════════════════════════════════════════
// NAVIGATION
// ════════════════════════════════════════════════════════════

function initNavigation() {
  $$('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      navigateTo(page);
    });
  });
}

function navigateTo(page) {
  state.currentPage = page;
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  $(`[data-page="${page}"]`).classList.add('active');
  $$('.page').forEach(p => p.classList.remove('active'));
  const pageEl = $(`#page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  if (page === 'my-data') { loadFiles(); loadContextPacks(); }
  if (page === 'organized') loadClusters();
  if (page === 'ai-chat') updateChatWelcomeIndicators();
}

// ════════════════════════════════════════════════════════════
// DATA LOADING
// ════════════════════════════════════════════════════════════

async function loadFiles() {
  try {
    const res = await fetch(`${API_BASE}/api/files`);
    const data = await res.json();
    state.files = data.files || [];
    renderFileList();
    loadStats();
  } catch (e) {
    console.error('Failed to load files:', e);
  }
}

async function loadClusters() {
  try {
    const res = await fetch(`${API_BASE}/api/clusters`);
    const data = await res.json();
    state.clusters = data.clusters || [];
    if ($('#cluster-count')) $('#cluster-count').textContent = data.total_clusters || 0;
    if ($('#organized-file-count')) $('#organized-file-count').textContent = data.total_files || 0;
    if ($('#summary-count')) $('#summary-count').textContent = data.total_ready || 0;
    renderClusters();
  } catch (e) {
    console.error('Failed to load clusters:', e);
  }
}

async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    const data = await res.json();
    $('#total-files-count').textContent = `${data.total_files} files`;
    $('#total-clusters-count').textContent = `${data.total_clusters} collections`;
    $('#total-packs-count').textContent = `${data.total_context_packs} context packs`;
    $('#processed-count').textContent = `${data.processed} processed`;

    // Update status cards
    updateProfileStatusCard(data.profile_set);
    updatePacksStatusCard(data.total_context_packs);
    updateAIReadyCard(data.processed, data.profile_set, data.total_context_packs);
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

async function loadProfile() {
  try {
    const res = await fetch(`${API_BASE}/api/profile`);
    state.profile = await res.json();
    updateProfileUI();
  } catch (e) {
    console.error('Failed to load profile:', e);
  }
}

async function loadContextPacks() {
  try {
    const res = await fetch(`${API_BASE}/api/context-packs`);
    const data = await res.json();
    state.contextPacks = data.packs || [];
    renderContextPacks();
  } catch (e) {
    console.error('Failed to load context packs:', e);
  }
}

// ════════════════════════════════════════════════════════════
// STATUS CARDS
// ════════════════════════════════════════════════════════════

function updateProfileStatusCard(isSet) {
  const desc = $('#profile-card-status');
  const badge = $('#profile-card-badge');
  if (isSet) {
    desc.textContent = 'ตั้งค่าแล้ว';
    badge.textContent = 'Active';
    badge.className = 'status-card-badge active';
  } else {
    desc.textContent = 'ยังไม่ได้ตั้งค่า';
    badge.textContent = 'Setup';
    badge.className = 'status-card-badge';
  }
}

function updatePacksStatusCard(count) {
  const desc = $('#packs-card-status');
  const badge = $('#packs-card-badge');
  desc.textContent = `${count} packs`;
  badge.textContent = count > 0 ? 'Ready' : '—';
  badge.className = count > 0 ? 'status-card-badge active' : 'status-card-badge';
}

function updateAIReadyCard(processed, profileSet, packsCount) {
  const desc = $('#ai-ready-status');
  const badge = $('#ai-ready-badge');
  const layers = [];
  if (profileSet) layers.push('Profile');
  if (packsCount > 0) layers.push('Packs');
  if (processed > 0) layers.push('Files');

  if (layers.length >= 2) {
    desc.textContent = layers.join(' + ');
    badge.textContent = 'Ready';
    badge.className = 'status-card-badge active';
  } else if (layers.length === 1) {
    desc.textContent = `${layers[0]} พร้อม`;
    badge.textContent = 'Partial';
    badge.className = 'status-card-badge ready';
  } else {
    desc.textContent = 'ยังไม่พร้อม';
    badge.textContent = '—';
    badge.className = 'status-card-badge';
  }
}

// ════════════════════════════════════════════════════════════
// PROFILE
// ════════════════════════════════════════════════════════════

function initProfilePanel() {
  const overlay = $('#profile-overlay');
  const closeBtn = $('#btn-close-profile');
  const openBtn = $('#btn-open-profile');

  openBtn.addEventListener('click', openProfilePanel);
  closeBtn.addEventListener('click', closeProfilePanel);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeProfilePanel(); });
}

function openProfilePanel() {
  const overlay = $('#profile-overlay');
  if (state.profile) {
    $('#pf-identity').value = state.profile.identity_summary || '';
    $('#pf-goals').value = state.profile.goals || '';
    $('#pf-working-style').value = state.profile.working_style || '';
    $('#pf-output-style').value = state.profile.preferred_output_style || '';
    $('#pf-background').value = state.profile.background_context || '';
  }
  overlay.classList.add('active');
}

function closeProfilePanel() {
  $('#profile-overlay').classList.remove('active');
}

async function saveProfile() {
  const data = {
    identity_summary: $('#pf-identity').value.trim(),
    goals: $('#pf-goals').value.trim(),
    working_style: $('#pf-working-style').value.trim(),
    preferred_output_style: $('#pf-output-style').value.trim(),
    background_context: $('#pf-background').value.trim()
  };

  try {
    const res = await fetch(`${API_BASE}/api/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    state.profile = await res.json();
    updateProfileUI();
    closeProfilePanel();
    showToast('✅ บันทึกโปรไฟล์เรียบร้อย — AI จะใช้ข้อมูลนี้ในการตอบคำถาม', 'success');
    loadStats();
  } catch (e) {
    showToast('บันทึกโปรไฟล์ไม่สำเร็จ', 'error');
  }
}

function updateProfileUI() {
  const p = state.profile;
  const isSet = p && p.exists;
  const dot = $('#profile-status-dot');
  const text = $('#profile-status-text');
  const chatDot = $('#chat-profile-dot');
  const chatLabel = $('#chat-profile-label');

  if (isSet) {
    dot.classList.add('active');
    text.textContent = 'Active';
    if (chatDot) chatDot.classList.add('active');
    if (chatLabel) chatLabel.textContent = 'Profile: Active';
  } else {
    dot.classList.remove('active');
    text.textContent = 'Not configured';
    if (chatDot) chatDot.classList.remove('active');
    if (chatLabel) chatLabel.textContent = 'Profile: Not set';
  }
}

function updateChatWelcomeIndicators() {
  const p = state.profile;
  const profileStatus = $('#welcome-profile-status');
  const packsStatus = $('#welcome-packs-status');
  const collectionsStatus = $('#welcome-collections-status');
  const filesStatus = $('#welcome-files-status');

  if (profileStatus) profileStatus.textContent = (p && p.exists) ? '✓' : '—';
  if (packsStatus) packsStatus.textContent = state.contextPacks.length > 0 ? `${state.contextPacks.length}` : '—';
  if (collectionsStatus) collectionsStatus.textContent = state.clusters.length > 0 ? `${state.clusters.length}` : '—';
  if (filesStatus) filesStatus.textContent = state.files.length > 0 ? `${state.files.length}` : '—';
}

// ════════════════════════════════════════════════════════════
// FILE UPLOAD
// ════════════════════════════════════════════════════════════

function initUpload() {
  const zone = $('#upload-zone');
  const input = $('#file-input');
  const btnUpload = $('#btn-upload');

  zone.addEventListener('click', () => input.click());
  btnUpload.addEventListener('click', () => input.click());

  input.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    input.value = '';
  });

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    handleFiles(e.dataTransfer.files);
  });
}

async function handleFiles(fileList) {
  if (!fileList || fileList.length === 0) return;

  const formData = new FormData();
  let validCount = 0;
  const allowedTypes = ['pdf', 'txt', 'md', 'docx'];

  for (const file of fileList) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (allowedTypes.includes(ext)) {
      formData.append('files', file);
      validCount++;
    } else {
      showToast(`ไม่รองรับไฟล์ประเภท: .${ext}`, 'error');
    }
  }

  if (validCount === 0) return;
  showToast(`กำลังอัปโหลด ${validCount} ไฟล์...`, 'success');

  try {
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.uploaded && data.uploaded.length > 0) {
      showToast(`✅ อัปโหลดสำเร็จ ${data.uploaded.length} ไฟล์!`, 'success');
      await new Promise(r => setTimeout(r, 300));
      await loadFiles();
      await loadStats();
    }
  } catch (e) {
    console.error('Upload failed:', e);
    showToast('อัปโหลดไม่สำเร็จ: ' + e.message, 'error');
  }
}

// ════════════════════════════════════════════════════════════
// ORGANIZE
// ════════════════════════════════════════════════════════════

async function triggerOrganize() {
  if (state.isOrganizing) return;
  state.isOrganizing = true;

  const btn = $('#btn-organize');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 11-6.219-8.56"/>
      </svg>
      กำลังจัดระเบียบด้วย AI...
    `;
  }

  showToast('🧠 AI กำลังจัดระเบียบไฟล์ของคุณ... อาจใช้เวลาสักครู่', 'success');

  try {
    const res = await fetch(`${API_BASE}/api/organize`, { method: 'POST' });
    const data = await res.json();

    if (res.ok) {
      showToast('✅ จัดระเบียบ ให้คะแนน และสรุปเรียบร้อยแล้ว!', 'success');
      await loadFiles();
      await loadStats();
      await loadClusters();
    } else {
      showToast('จัดระเบียบไม่สำเร็จ: ' + (data.detail || 'ข้อผิดพลาด'), 'error');
    }
  } catch (e) {
    console.error('Organize failed:', e);
    showToast('จัดระเบียบไม่สำเร็จ: ' + e.message, 'error');
  } finally {
    state.isOrganizing = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
        </svg>
        จัดระเบียบด้วย AI
      `;
    }
  }
}

// ════════════════════════════════════════════════════════════
// RENDER: FILE LIST
// ════════════════════════════════════════════════════════════

function renderFileList() {
  const container = $('#file-list');
  const countBadge = $('#file-count-badge');
  countBadge.textContent = `${state.files.length} files`;

  if (state.files.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <polyline points="13 2 13 9 20 9"/>
          </svg>
        </div>
        <p class="empty-state-title">ยังไม่มีไฟล์ในพื้นที่ส่วนตัว</p>
        <p class="empty-state-text">อัปโหลดไฟล์สำคัญของคุณเพื่อเริ่มต้น ระบบจะจัดระเบียบ สร้างสรุป และเตรียม context ให้คุณอัตโนมัติ</p>
      </div>
    `;
    return;
  }

  const hasUnorganized = state.files.some(f => f.processing_status === 'uploaded');
  const organizeBtn = hasUnorganized ? `
    <button class="btn btn-primary" id="btn-organize" onclick="triggerOrganize()" style="margin-bottom: 20px;">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="7" height="7"/>
        <rect x="14" y="3" width="7" height="7"/>
        <rect x="3" y="14" width="7" height="7"/>
      </svg>
      จัดระเบียบด้วย AI
    </button>
  ` : '';

  container.innerHTML = organizeBtn + state.files.map(file => `
    <div class="file-item" data-id="${file.id}">
      <div class="file-icon ${file.filetype}">${file.filetype}</div>
      <div class="file-info">
        <div class="file-name">${escapeHtml(file.filename)}</div>
        <div class="file-meta">
          <span>${file.filetype.toUpperCase()}</span>
          <span class="file-meta-sep"></span>
          <span>${formatDate(file.uploaded_at)}</span>
          ${file.text_length ? `<span class="file-meta-sep"></span><span>${formatTextLength(file.text_length)}</span>` : ''}
        </div>
      </div>
      <span class="status-badge ${file.processing_status}">
        ${formatStatus(file.processing_status)}
      </span>
      <button class="btn-close" onclick="deleteFile('${file.id}')" title="ลบไฟล์" style="margin-left: 8px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
  `).join('');
}

function formatStatus(status) {
  const statusMap = {
    uploaded: 'Uploaded',
    processing: 'Processing…',
    organized: 'Organized',
    ready: 'Summary Ready',
    error: 'Error'
  };
  return statusMap[status] || status;
}

function formatDate(isoDate) {
  if (!isoDate) return '';
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString('th-TH', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return isoDate; }
}

function formatTextLength(len) {
  if (len > 10000) return `${Math.round(len / 1000)}K chars`;
  return `${len.toLocaleString()} chars`;
}

async function deleteFile(fileId) {
  const confirmed = await showConfirm(
    'ยืนยันการลบ',
    'ลบไฟล์นี้หรือ? ไม่สามารถย้อนกลับได้'
  );
  if (!confirmed) return;
  try {
    await fetch(`${API_BASE}/api/files/${fileId}`, { method: 'DELETE' });
    showToast('ลบไฟล์แล้ว', 'success');
    await loadFiles();
    await loadStats();
  } catch (e) {
    showToast('ลบไฟล์ไม่สำเร็จ', 'error');
  }
}

// ════════════════════════════════════════════════════════════
// RENDER: CONTEXT PACKS
// ════════════════════════════════════════════════════════════

function renderContextPacks() {
  const container = $('#packs-grid');
  if (!container) return;

  if (state.contextPacks.length === 0) {
    container.innerHTML = `
      <div class="packs-empty">
        <p>ยังไม่มี Context Pack — สร้างจากไฟล์และ Collections เพื่อให้ AI มีบริบทพร้อมใช้</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.contextPacks.map(pack => `
    <div class="pack-card" data-pack-id="${pack.id}">
      <div class="pack-card-header">
        <div class="pack-card-icon">${pack.type_icon || '📦'}</div>
        <div class="pack-card-title">${escapeHtml(pack.title)}</div>
        <span class="pack-card-type">${pack.type_label || pack.type}</span>
      </div>
      <div class="pack-card-body">${escapeHtml(pack.summary_text ? pack.summary_text.slice(0, 200) + '...' : 'No content')}</div>
      <div class="pack-card-footer">
        <span>${pack.source_count || 0} sources · ${formatDate(pack.updated_at)}</span>
        <div class="pack-card-actions">
          <button class="pack-action-btn" onclick="regeneratePackAction('${pack.id}')" title="Regenerate">🔄</button>
          <button class="pack-action-btn danger" onclick="deletePackAction('${pack.id}')" title="Delete">🗑</button>
        </div>
      </div>
    </div>
  `).join('');
}

async function deletePackAction(packId) {
  const confirmed = await showConfirm('ลบ Context Pack', 'ลบ Context Pack นี้หรือ?');
  if (!confirmed) return;
  try {
    await fetch(`${API_BASE}/api/context-packs/${packId}`, { method: 'DELETE' });
    showToast('ลบ Context Pack แล้ว', 'success');
    await loadContextPacks();
    await loadStats();
  } catch (e) {
    showToast('ลบไม่สำเร็จ', 'error');
  }
}

async function regeneratePackAction(packId) {
  showToast('🔄 กำลัง regenerate Context Pack...', 'success');
  try {
    const res = await fetch(`${API_BASE}/api/context-packs/${packId}/regenerate`, { method: 'POST' });
    if (res.ok) {
      showToast('✅ Regenerate สำเร็จ!', 'success');
      await loadContextPacks();
    } else {
      showToast('Regenerate ไม่สำเร็จ', 'error');
    }
  } catch (e) {
    showToast('Regenerate ไม่สำเร็จ: ' + e.message, 'error');
  }
}

// ════════════════════════════════════════════════════════════
// CREATE CONTEXT PACK MODAL
// ════════════════════════════════════════════════════════════

function initCreatePackModal() {
  const overlay = $('#create-pack-overlay');
  const closeBtn = $('#btn-close-create-pack');

  closeBtn.addEventListener('click', closeCreatePackModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeCreatePackModal(); });

  // Pack type buttons
  $$('.pack-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.pack-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.selectedPackType = btn.dataset.type;
    });
  });
}

async function openCreatePackModal() {
  // Refresh data
  await loadFiles();
  await loadClusters();

  const selector = $('#source-selector');
  let html = '';

  // Add clusters as options
  if (state.clusters.length > 0) {
    html += '<div style="font-size: 10px; color: var(--text-muted); padding: 4px 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Collections</div>';
    state.clusters.forEach(c => {
      html += `
        <label class="source-check-item">
          <input type="checkbox" value="cluster:${c.id}">
          <span class="source-check-label">📁 ${escapeHtml(c.title)}</span>
          <span class="source-check-type">${c.file_count || 0} files</span>
        </label>
      `;
    });
  }

  // Add files as options
  const readyFiles = state.files.filter(f => f.processing_status === 'ready' || f.processing_status === 'organized');
  if (readyFiles.length > 0) {
    html += '<div style="font-size: 10px; color: var(--text-muted); padding: 4px 8px; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600;">Files</div>';
    readyFiles.forEach(f => {
      html += `
        <label class="source-check-item">
          <input type="checkbox" value="file:${f.id}">
          <span class="source-check-label">📄 ${escapeHtml(f.filename)}</span>
          <span class="source-check-type">${f.filetype}</span>
        </label>
      `;
    });
  }

  if (!html) {
    html = '<div class="packs-empty"><p>ยังไม่มีไฟล์หรือ Collections ที่พร้อม</p></div>';
  }

  selector.innerHTML = html;
  $('#pack-title').value = '';
  $('#create-pack-overlay').classList.add('active');
}

function closeCreatePackModal() {
  $('#create-pack-overlay').classList.remove('active');
}

async function generatePack() {
  const title = $('#pack-title').value.trim();
  if (!title) {
    showToast('กรุณาใส่ชื่อ Context Pack', 'error');
    return;
  }

  const checked = $$('#source-selector input[type="checkbox"]:checked');
  const sourceFileIds = [];
  const sourceClusterIds = [];

  checked.forEach(cb => {
    const [type, id] = cb.value.split(':');
    if (type === 'file') sourceFileIds.push(id);
    if (type === 'cluster') sourceClusterIds.push(id);
  });

  if (sourceFileIds.length === 0 && sourceClusterIds.length === 0) {
    showToast('กรุณาเลือก sources อย่างน้อย 1 รายการ', 'error');
    return;
  }

  const btn = $('#btn-generate-pack');
  btn.disabled = true;
  btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 11-6.219-8.56"/></svg> Generating...';

  showToast('🧠 AI กำลังสร้าง Context Pack...', 'success');

  try {
    const res = await fetch(`${API_BASE}/api/context-packs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: state.selectedPackType,
        title,
        source_file_ids: sourceFileIds,
        source_cluster_ids: sourceClusterIds
      })
    });

    if (res.ok) {
      showToast('✅ สร้าง Context Pack สำเร็จ!', 'success');
      closeCreatePackModal();
      await loadContextPacks();
      await loadStats();
    } else {
      const err = await res.json();
      showToast('สร้างไม่สำเร็จ: ' + (err.detail || 'Error'), 'error');
    }
  } catch (e) {
    showToast('สร้างไม่สำเร็จ: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg> Generate Context Pack';
  }
}

// ════════════════════════════════════════════════════════════
// RENDER: CLUSTERS
// ════════════════════════════════════════════════════════════

const CLUSTER_COLORS = [
  'linear-gradient(135deg, #6383ff, #4a6cf7)',
  'linear-gradient(135deg, #4fc3f7, #29b6f6)',
  'linear-gradient(135deg, #81c784, #66bb6a)',
  'linear-gradient(135deg, #ffd54f, #ffb300)',
  'linear-gradient(135deg, #b39ddb, #9575cd)',
  'linear-gradient(135deg, #ff8a65, #ff7043)'
];

function renderClusters() {
  const container = $('#clusters-grid');

  if (state.clusters.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
            <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
          </svg>
        </div>
        <p class="empty-state-title">ยังไม่มี Collections</p>
        <p class="empty-state-text">อัปโหลดไฟล์ใน My Data แล้วคลิก "จัดระเบียบด้วย AI" เพื่อจัดกลุ่มไฟล์อย่างเป็นระบบ</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.clusters.map((cluster, idx) => {
    const color = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];
    const files = cluster.files || [];
    const derivedPacks = cluster.derived_packs || [];

    // Derived packs row
    let derivedHtml = '';
    if (derivedPacks.length > 0) {
      derivedHtml = `
        <div class="cluster-derived-packs">
          <span class="derived-label">Context Packs:</span>
          ${derivedPacks.map(p => `<span class="derived-pack-chip">📦 ${escapeHtml(p.title)}</span>`).join('')}
        </div>
      `;
    }

    return `
      <div class="cluster-card" data-cluster-id="${cluster.id}">
        <div class="cluster-header">
          <div class="cluster-title-area">
            <div class="cluster-name">
              <div class="cluster-icon" style="background: ${color}; color: white;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                  <rect x="3" y="14" width="7" height="7"/>
                </svg>
              </div>
              ${escapeHtml(cluster.title)}
            </div>
            <p class="cluster-summary">${escapeHtml(cluster.summary)}</p>
          </div>
          <span class="cluster-file-count">${files.length} files</span>
        </div>
        ${derivedHtml}
        <div class="cluster-files">
          ${files.map(file => `
            <div class="cluster-file" onclick="openSummary('${file.id}')">
              <div class="cluster-file-icon" style="${getFileIconStyle(file.filetype)}">${file.filetype}</div>
              <div class="cluster-file-info">
                <div class="cluster-file-name">
                  ${escapeHtml(file.filename)}
                  ${file.is_primary ? `<span class="primary-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                    Primary
                  </span>` : ''}
                </div>
                <div class="cluster-file-snippet">${escapeHtml(file.snippet || '')}</div>
              </div>
              <div class="cluster-file-badges">
                ${file.importance_label ? `<span class="importance-badge ${file.importance_label}">${translateImportance(file.importance_label)}</span>` : ''}
                ${file.has_summary ? `<button class="btn-view-summary" onclick="event.stopPropagation(); openSummary('${file.id}')">View Summary</button>` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }).join('');
}

function getFileIconStyle(type) {
  return {
    pdf: 'background: rgba(239, 83, 80, 0.12); color: #ef5350;',
    docx: 'background: rgba(66, 165, 245, 0.12); color: #42a5f5;',
    md: 'background: rgba(129, 199, 132, 0.12); color: #81c784;',
    txt: 'background: rgba(255, 213, 79, 0.12); color: #ffd54f;'
  }[type] || '';
}

// ════════════════════════════════════════════════════════════
// SUMMARY PANEL
// ════════════════════════════════════════════════════════════

function initSummaryPanel() {
  const overlay = $('#summary-overlay');
  const closeBtn = $('#btn-close-summary');
  closeBtn.addEventListener('click', closeSummary);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeSummary(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSummary(); });
}

async function openSummary(fileId) {
  const overlay = $('#summary-overlay');
  const title = $('#summary-panel-title');
  const meta = $('#summary-panel-meta');
  const body = $('#summary-panel-body');

  title.textContent = 'Loading...';
  meta.innerHTML = '';
  body.innerHTML = '<p style="color: var(--text-tertiary);">กำลังโหลดสรุป...</p>';
  overlay.classList.add('active');

  try {
    const res = await fetch(`${API_BASE}/api/summary/${fileId}`);
    if (!res.ok) {
      body.innerHTML = '<p style="color: var(--status-error);">ยังไม่มีสรุป กรุณาจัดระเบียบไฟล์ก่อน</p>';
      return;
    }

    const data = await res.json();
    title.textContent = data.filename;
    meta.innerHTML = `
      <span class="summary-meta-tag">${data.filetype.toUpperCase()}</span>
      <span class="summary-meta-tag">Importance: ${translateImportance(data.importance_label)} (${data.importance_score})</span>
      ${data.is_primary ? `<span class="summary-meta-tag" style="color: var(--accent-primary);">★ Primary File</span>` : ''}
      <span class="summary-meta-tag">Collection: ${escapeHtml(data.cluster)}</span>
    `;

    body.innerHTML = `
      <h4>สรุป</h4>
      <p>${escapeHtml(data.summary_text)}</p>

      <h4>หัวข้อสำคัญ</h4>
      <ul>${(data.key_topics || []).map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>

      <h4>ข้อเท็จจริงสำคัญ</h4>
      <ul>${(data.key_facts || []).map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>

      <h4>ทำไมไฟล์นี้สำคัญ</h4>
      <p>${escapeHtml(data.why_important)}</p>

      <h4>แนะนำการใช้งาน</h4>
      <p>${escapeHtml(data.suggested_usage)}</p>
    `;
  } catch (e) {
    body.innerHTML = `<p style="color: var(--status-error);">โหลดสรุปไม่สำเร็จ: ${e.message}</p>`;
  }
}

function closeSummary() {
  $('#summary-overlay').classList.remove('active');
}

// ════════════════════════════════════════════════════════════
// AI CHAT (v2 — with injection transparency)
// ════════════════════════════════════════════════════════════

function initChat() {
  const input = $('#chat-input');
  const sendBtn = $('#btn-send');

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  $$('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      input.value = chip.dataset.prompt;
      input.dispatchEvent(new Event('input'));
      sendMessage();
    });
  });
}

async function sendMessage() {
  const input = $('#chat-input');
  const question = input.value.trim();
  if (!question) return;

  // Hide welcome
  const welcome = $('#chat-welcome');
  if (welcome) welcome.style.display = 'none';

  addChatBubble('user', question);
  input.value = '';
  input.style.height = 'auto';

  const thinkingId = showThinking();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    removeThinking(thinkingId);

    if (!res.ok) {
      const err = await res.json();
      addChatBubble('assistant', `ข้อผิดพลาด: ${err.detail || 'ไม่สามารถรับคำตอบได้'}`, null);
      return;
    }

    const data = await res.json();
    addChatBubble('assistant', data.answer, data);
    updateSourcesPanel(data);

  } catch (e) {
    removeThinking(thinkingId);
    addChatBubble('assistant', `ข้อผิดพลาดการเชื่อมต่อ: ${e.message}`, null);
  }
}

function addChatBubble(role, content, sourceData) {
  const container = $('#chat-messages');
  const bubble = document.createElement('div');
  bubble.className = `chat-bubble ${role}`;

  if (role === 'user') {
    bubble.innerHTML = `
      <div class="chat-avatar human">U</div>
      <div class="chat-bubble-content"><p>${escapeHtml(content)}</p></div>
    `;
  } else {
    let formatted = escapeHtml(content)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n- /g, '<br>• ')
      .replace(/\n• /g, '<br>• ')
      .replace(/\n\* /g, '<br>• ')
      .replace(/\n/g, '<br>');

    // Injection badge
    let injectionHtml = '';
    if (sourceData && sourceData.injection_summary) {
      injectionHtml = `<div class="chat-injection-badge">🧠 ${escapeHtml(sourceData.injection_summary)}</div>`;
    }

    // Source chips
    let sourcesHtml = '';
    if (sourceData && sourceData.files_used && sourceData.files_used.length > 0) {
      const modeColors = { summary: 'var(--mode-summary)', excerpt: 'var(--mode-excerpt)', raw: 'var(--mode-raw)' };
      sourcesHtml = `
        <div class="chat-sources-inline">
          <div class="chat-sources-label">แหล่งข้อมูลที่ใช้</div>
          <div class="chat-source-chips">
            ${sourceData.profile_used ? `<span class="chat-source-chip"><span class="source-dot" style="background: var(--layer-profile)"></span>Profile</span>` : ''}
            ${(sourceData.context_packs_used || []).map(p =>
              `<span class="chat-source-chip"><span class="source-dot" style="background: var(--layer-packs)"></span>${escapeHtml(p.title)}</span>`
            ).join('')}
            ${sourceData.files_used.map(f => {
              const mode = sourceData.retrieval_modes[f.id] || 'summary';
              return `<span class="chat-source-chip">
                <span class="source-dot" style="background: ${modeColors[mode] || modeColors.summary}"></span>
                ${escapeHtml(f.filename)}
                <span style="color: var(--text-tertiary);">(${mode})</span>
              </span>`;
            }).join('')}
          </div>
        </div>
      `;
    }

    bubble.innerHTML = `
      <div class="chat-avatar ai">AI</div>
      <div class="chat-bubble-content">${injectionHtml}<p>${formatted}</p>${sourcesHtml}</div>
    `;
  }

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function showThinking() {
  const container = $('#chat-messages');
  const id = 'thinking-' + Date.now();
  const el = document.createElement('div');
  el.className = 'chat-bubble assistant';
  el.id = id;
  el.innerHTML = `
    <div class="chat-avatar ai">AI</div>
    <div class="chat-thinking">
      <div class="thinking-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeThinking(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// ════════════════════════════════════════════════════════════
// SOURCES PANEL (v2 — layered transparency)
// ════════════════════════════════════════════════════════════

function updateSourcesPanel(data) {
  const empty = $('#sources-empty');
  const active = $('#sources-active');
  empty.style.display = 'none';
  active.style.display = 'block';

  // Injection Summary
  $('#injection-summary-text').textContent = data.injection_summary || '—';

  // Layer: Profile
  const profileSection = $('#source-layer-profile');
  const profileStatus = $('#source-profile-status');
  if (data.profile_used) {
    profileSection.style.display = 'block';
    profileStatus.innerHTML = `<span style="color: var(--status-success);">✓</span> โปรไฟล์ถูกใช้ในการตอบคำถามนี้`;
  } else {
    profileSection.style.display = 'block';
    profileStatus.innerHTML = `<span style="color: var(--text-muted);">—</span> ไม่ได้ใช้โปรไฟล์`;
  }

  // Layer: Context Packs
  const packsSection = $('#source-layer-packs');
  const packsList = $('#source-packs-list');
  const packsUsed = data.context_packs_used || [];
  if (packsUsed.length > 0) {
    packsSection.style.display = 'block';
    packsList.innerHTML = packsUsed.map(p => `
      <div class="source-pack-item">
        <span class="pack-type-emoji">${p.type === 'study' ? '📚' : p.type === 'work' ? '💼' : p.type === 'project' ? '🎯' : '👤'}</span>
        <span>${escapeHtml(p.title)}</span>
      </div>
    `).join('');
  } else {
    packsSection.style.display = 'block';
    packsList.innerHTML = '<div style="font-size: 12px; color: var(--text-muted);">ไม่มี Context Pack ที่เกี่ยวข้อง</div>';
  }

  // Layer: Collection
  if (data.cluster) {
    $('#source-cluster-card').innerHTML = `
      <div class="source-cluster-name">${escapeHtml(data.cluster.title)}</div>
      <div class="source-cluster-desc">${escapeHtml(data.cluster.summary || '')}</div>
    `;
  } else {
    $('#source-cluster-card').innerHTML = '<div class="source-cluster-name">หลาย Collections</div>';
  }

  // Layer: Files
  const filesList = $('#source-files-list');
  filesList.innerHTML = (data.files_used || []).map(f => {
    const mode = data.retrieval_modes[f.id] || 'summary';
    return `
      <div class="source-file-item">
        <div class="source-file-icon" style="${getFileIconStyle(f.filetype)}">${f.filetype}</div>
        <span class="source-file-name">${escapeHtml(f.filename)}</span>
        <span class="source-file-mode ${mode}">${mode}</span>
      </div>
    `;
  }).join('');

  // Retrieval Mode
  const modes = [...new Set(Object.values(data.retrieval_modes || {}))];
  const allModes = ['summary', 'excerpt', 'raw'];
  $('#retrieval-mode').innerHTML = allModes.map(m =>
    `<span class="retrieval-mode-tag ${modes.includes(m) ? 'active' : ''}">${cap(m)}</span>`
  ).join('');

  // Reasoning
  $('#source-reasoning').textContent = data.reasoning || '';
}

// ════════════════════════════════════════════════════════════
// UTILITIES
// ════════════════════════════════════════════════════════════

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function cap(s) {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function translateImportance(label) {
  const map = { high: 'High', medium: 'Medium', low: 'Low' };
  return map[label] || label;
}

function showConfirm(title, message) {
  return new Promise((resolve) => {
    const overlay = $('#confirm-overlay');
    $('#confirm-title').textContent = title;
    $('#confirm-message').textContent = message;
    overlay.classList.add('active');

    const cleanup = (result) => {
      overlay.classList.remove('active');
      cancelBtn.removeEventListener('click', onCancel);
      okBtn.removeEventListener('click', onOk);
      overlay.removeEventListener('click', onOverlay);
      resolve(result);
    };

    const onCancel = () => cleanup(false);
    const onOk = () => cleanup(true);
    const onOverlay = (e) => { if (e.target === overlay) cleanup(false); };

    const cancelBtn = $('#confirm-cancel');
    const okBtn = $('#confirm-ok');
    cancelBtn.addEventListener('click', onCancel);
    okBtn.addEventListener('click', onOk);
    overlay.addEventListener('click', onOverlay);
  });
}

function showToast(message, type = 'success') {
  const container = $('#toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success'
    ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#69f0ae" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
    : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef5350" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
  toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s var(--ease-out) forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
