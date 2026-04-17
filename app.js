/* ════════════════════════════════════════════════════════════
   PROJECT KEY — Application Logic (Real Backend)
   MVP v0.1 — พื้นที่ข้อมูลส่วนตัว
   ════════════════════════════════════════════════════════════ */

const API_BASE = '';  // Same origin since FastAPI serves frontend

// ─── APP STATE ───
const state = {
  currentPage: 'my-data',
  files: [],
  clusters: [],
  chatMessages: [],
  isOrganizing: false
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
  loadFiles();
  loadStats();
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

  // Reload data when switching pages
  if (page === 'my-data') loadFiles();
  if (page === 'organized') loadClusters();
}

// ════════════════════════════════════════════════════════════
// DATA LOADING (REAL API)
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
    $('#total-files-count').textContent = `${data.total_files} ไฟล์`;
    $('#total-clusters-count').textContent = `${data.total_clusters} คอลเลกชัน`;
    $('#processed-count').textContent = `${data.processed} ประมวลผลแล้ว`;
  } catch (e) {
    console.error('Failed to load stats:', e);
  }
}

// ════════════════════════════════════════════════════════════
// FILE UPLOAD (REAL)
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
      showToast(`อัปโหลดและดึงข้อความสำเร็จ ${data.uploaded.length} ไฟล์!`, 'success');
      // Retry loadFiles with small delay to handle DB write latency
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
// ORGANIZE (REAL — calls LLM)
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
      showToast('จัดระเบียบไม่สำเร็จ: ' + (data.detail || 'ข้อผิดพลาดไม่ทราบสาเหตุ'), 'error');
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
  countBadge.textContent = `${state.files.length} ไฟล์`;

  if (state.files.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <polyline points="13 2 13 9 20 9"/>
          </svg>
        </div>
        <p class="empty-state-title">ยังไม่มีไฟล์</p>
        <p class="empty-state-text">อัปโหลดไฟล์สำคัญของคุณเพื่อเริ่มต้น ระบบจะจัดระเบียบและสรุปให้คุณอัตโนมัติ</p>
      </div>
    `;
    return;
  }

  // Show organize button if there are uploaded but unorganized files
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
    uploaded: 'อัปโหลดแล้ว',
    processing: 'กำลังประมวลผล…',
    organized: 'จัดระเบียบแล้ว',
    ready: 'สรุปพร้อม',
    error: 'ผิดพลาด — ลองจัดใหม่'
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
  if (len > 10000) return `${Math.round(len / 1000)}K ตัวอักษร`;
  return `${len.toLocaleString()} ตัวอักษร`;
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
        <p class="empty-state-title">ยังไม่มีคอลเลกชัน</p>
        <p class="empty-state-text">อัปโหลดไฟล์ในหน้าข้อมูลของฉัน แล้วคลิก "จัดระเบียบด้วย AI" เพื่อจัดกลุ่มไฟล์อย่างมีความหมาย</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.clusters.map((cluster, idx) => {
    const color = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];
    const files = cluster.files || [];

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
          <span class="cluster-file-count">${files.length} ไฟล์</span>
        </div>
        <div class="cluster-files">
          ${files.map(file => `
            <div class="cluster-file" onclick="openSummary('${file.id}')">
              <div class="cluster-file-icon" style="${getFileIconStyle(file.filetype)}">${file.filetype}</div>
              <div class="cluster-file-info">
                <div class="cluster-file-name">
                  ${escapeHtml(file.filename)}
                  ${file.is_primary ? `<span class="primary-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                    ไฟล์หลัก
                  </span>` : ''}
                </div>
                <div class="cluster-file-snippet">${escapeHtml(file.snippet || '')}</div>
              </div>
              <div class="cluster-file-badges">
                ${file.importance_label ? `<span class="importance-badge ${file.importance_label}">${translateImportance(file.importance_label)}</span>` : ''}
                ${file.has_summary ? `<button class="btn-view-summary" onclick="event.stopPropagation(); openSummary('${file.id}')">ดูสรุป</button>` : ''}
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
// SUMMARY PANEL (REAL DATA)
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

  // Show loading state
  title.textContent = 'กำลังโหลด...';
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
      <span class="summary-meta-tag">ความสำคัญ: ${translateImportance(data.importance_label)} (${data.importance_score})</span>
      ${data.is_primary ? `<span class="summary-meta-tag" style="color: var(--accent-primary);">★ ไฟล์หลัก</span>` : ''}
      <span class="summary-meta-tag">คอลเลกชัน: ${escapeHtml(data.cluster)}</span>
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
// AI CHAT (REAL — calls backend → LLM)
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

  // Add user bubble
  addChatBubble('user', question);
  input.value = '';
  input.style.height = 'auto';

  // Show thinking
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
    // Format markdown-like content
    let formatted = escapeHtml(content)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n- /g, '<br>• ')
      .replace(/\n• /g, '<br>• ')
      .replace(/\n\* /g, '<br>• ')
      .replace(/\n/g, '<br>');

    let sourcesHtml = '';
    if (sourceData && sourceData.files_used && sourceData.files_used.length > 0) {
      const modeColors = { summary: 'var(--mode-summary)', excerpt: 'var(--mode-excerpt)', raw: 'var(--mode-raw)' };
      sourcesHtml = `
        <div class="chat-sources-inline">
          <div class="chat-sources-label">แหล่งข้อมูลที่ใช้</div>
          <div class="chat-source-chips">
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
      <div class="chat-bubble-content"><p>${formatted}</p>${sourcesHtml}</div>
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

function updateSourcesPanel(data) {
  const empty = $('#sources-empty');
  const active = $('#sources-active');
  empty.style.display = 'none';
  active.style.display = 'block';

  // Cluster
  if (data.cluster) {
    $('#source-cluster-card').innerHTML = `
      <div class="source-cluster-name">${escapeHtml(data.cluster.title)}</div>
      <div class="source-cluster-desc">${escapeHtml(data.cluster.summary || '')}</div>
    `;
  } else {
    $('#source-cluster-card').innerHTML = '<div class="source-cluster-name">หลายคอลเลกชัน</div>';
  }

  // Files
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

  // Retrieval modes
  const modes = [...new Set(Object.values(data.retrieval_modes || {}))];
  const allModes = ['summary', 'excerpt', 'raw'];
  $('#retrieval-mode').innerHTML = allModes.map(m => `
    <span class="retrieval-mode-tag ${modes.includes(m) ? 'active' : ''}">${cap(m)}</span>
  `).join('');

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
  const map = { high: 'สูง', medium: 'กลาง', low: 'ต่ำ' };
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
