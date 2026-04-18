/**
 * Project KEY v3 — Frontend Logic
 * Knowledge Workspace with Graph Visualization
 */

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
const state = {
  currentPage: 'my-data',
  graphMode: 'global',  // global | local
  localNodeId: null,
  graphData: { nodes: [], edges: [] },
  simulation: null,
  selectedNodeId: null,
  filters: {
    source_file: true, entity: true, tag: true,
    project: true, context_pack: true, person: true,
  },
  knowledgeTab: 'collections',
};

// Node family color map
const NODE_COLORS = {
  source_file: '#ffd54f', entity: '#ff8a65', tag: '#4fc3f7',
  project: '#81c784', context_pack: '#4dd0e1', person: '#b39ddb',
  note: '#aed581', cluster: '#81c784',
};

// ═══════════════════════════════════════════
// i18n — BILINGUAL SYSTEM (TH / EN)
// ═══════════════════════════════════════════
const I18N = {
  th: {
    // Navigation
    'nav.myData': 'ข้อมูลของฉัน',
    'nav.knowledge': 'มุมมองความรู้',
    'nav.graph': 'กราฟ',
    'nav.chat': 'AI แชท',
    'nav.profile': 'โปรไฟล์',

    // Stats
    'stat.files': 'ไฟล์',
    'stat.collections': 'Collections',
    'stat.nodes': 'Nodes',
    'stat.relations': 'Relations',
    'stat.packs': 'Packs',

    // My Data page
    'myData.title': 'ข้อมูลของฉัน',
    'myData.subtitle': 'พื้นที่ข้อมูลส่วนตัวของคุณ',
    'myData.enrich': 'Enrich Metadata',
    'myData.organize': 'จัดระเบียบด้วย AI',
    'myData.uploadText': 'ลากไฟล์มาวาง หรือ คลิกเพื่อเลือกไฟล์',
    'myData.uploadHint': 'รองรับ PDF, TXT, MD, DOCX (สูงสุด 20 MB)',
    'myData.allFiles': 'ไฟล์ทั้งหมด',
    'myData.noFiles': 'ยังไม่มีไฟล์ — เพิ่มไฟล์เข้าพื้นที่ส่วนตัวของคุณ',
    'myData.delete': 'ลบ',

    // Knowledge page
    'knowledge.title': 'มุมมองความรู้',
    'knowledge.subtitle': 'ข้อมูลที่ถูกจัดเป็นระบบความรู้แล้ว',
    'knowledge.collections': 'Collections',
    'knowledge.notes': 'Notes & สรุป',
    'knowledge.packs': 'Context Packs',
    'knowledge.emptyCollections': 'ยังไม่มี Collections — จัดระเบียบไฟล์ก่อน',
    'knowledge.emptyPacks': 'ยังไม่มี Context Packs',
    'knowledge.emptyNotes': 'ยังไม่มี Notes & Entities — สร้างกราฟก่อน',
    'knowledge.loadFailed': 'โหลดข้อมูลล้มเหลว',
    'knowledge.organize': 'จัดระเบียบไฟล์ก่อนเพื่อสร้างระบบความรู้',

    // Graph page
    'graph.globalTitle': 'Global Graph',
    'graph.globalSubtitle': 'มุมมองความเชื่อมโยงภาพรวม',
    'graph.localTitle': 'Local Graph',
    'graph.localSubtitle': 'มุมมองแบบเฉพาะจุด',
    'graph.searchPlaceholder': 'ค้นหา node...',
    'graph.filterFile': 'ไฟล์',
    'graph.rebuild': 'สร้างกราฟใหม่',
    'graph.emptyTitle': 'ยังไม่มี Knowledge Graph',
    'graph.emptyHint': 'จัดระเบียบไฟล์ก่อนเพื่อสร้างกราฟ',
    'graph.selectLocal': 'เลือก node จาก Global Graph ก่อน',

    // Detail panel
    'detail.summary': 'สรุป',
    'detail.metadata': 'Metadata',
    'detail.relations': 'ความสัมพันธ์',
    'detail.showLocal': 'แสดงกราฟเฉพาะจุด',
    'detail.askAi': 'ถาม AI เกี่ยวกับสิ่งนี้',
    'detail.noSummary': 'ไม่มีสรุป',

    // Chat page
    'chat.title': 'AI แชท',
    'chat.subtitle': 'AI ใช้ข้อมูล ความสัมพันธ์ และบริบทของคุณในการตอบ',
    'chat.welcome': 'สวัสดี! ถามอะไรก็ได้เกี่ยวกับข้อมูลของคุณ',
    'chat.welcomeSub': 'AI จะใช้ Profile, Context Packs, Files, และ Knowledge Graph ในการตอบ',
    'chat.placeholder': 'ถามเกี่ยวกับข้อมูลของคุณ...',
    'chat.profileNotSet': 'ยังไม่ตั้งค่า',
    'chat.profileActive': 'เปิดใช้งาน',

    // Sources panel
    'sources.title': 'หลักฐานที่ใช้',
    'sources.profile': '👤 โปรไฟล์',
    'sources.packs': '📦 Context Packs',
    'sources.files': '📄 ไฟล์ที่ใช้',
    'sources.graph': '🔗 Nodes & Edges',
    'sources.reasoning': '🧠 เหตุผลในการเลือก',
    'sources.evidence': '📊 Evidence Graph',

    // Profile modal
    'profile.title': '👤 โปรไฟล์ของฉัน',
    'profile.identity': 'ฉันเป็นใคร',
    'profile.goals': 'เป้าหมายของฉัน',
    'profile.style': 'สไตล์การทำงาน',
    'profile.output': 'ต้องการคำตอบแบบไหน',
    'profile.background': 'บริบทสำคัญ',
    'profile.save': 'บันทึกโปรไฟล์',
    'profile.identityPh': 'เช่น นักศึกษาปริญญาโท สาขาวิทยาศาสตร์...',
    'profile.goalsPh': 'เช่น ทำวิจัยเกี่ยวกับ...',
    'profile.stylePh': 'เช่น ชอบข้อมูลที่เป็นระบบ...',
    'profile.outputPh': 'เช่น สรุปสั้นๆ ตรงประเด็น...',
    'profile.backgroundPh': 'เช่น กำลังทำโปรเจกต์...',

    // Confirm modal
    'confirm.cancel': 'ยกเลิก',
    'confirm.ok': 'ยืนยัน',

    // Toasts / dynamic
    'toast.uploaded': 'อัปโหลดเรียบร้อย',
    'toast.deleted': 'ลบเรียบร้อย',
    'toast.profileSaved': 'บันทึกโปรไฟล์เรียบร้อย',
    'toast.organized': 'จัดระเบียบเรียบร้อย',
    'toast.enriched': 'Enrich metadata เรียบร้อย',
    'toast.graphBuilt': 'สร้างกราฟเรียบร้อย',
    'toast.error': 'เกิดข้อผิดพลาด',
  },

  en: {
    // Navigation
    'nav.myData': 'My Data',
    'nav.knowledge': 'Knowledge View',
    'nav.graph': 'Graph',
    'nav.chat': 'AI Chat',
    'nav.profile': 'My Profile',

    // Stats
    'stat.files': 'Files',
    'stat.collections': 'Collections',
    'stat.nodes': 'Nodes',
    'stat.relations': 'Relations',
    'stat.packs': 'Packs',

    // My Data page
    'myData.title': 'My Data',
    'myData.subtitle': 'Your personal data space',
    'myData.enrich': 'Enrich Metadata',
    'myData.organize': 'Organize with AI',
    'myData.uploadText': 'Drag files here or click to select',
    'myData.uploadHint': 'Supports PDF, TXT, MD, DOCX (max 20 MB)',
    'myData.allFiles': 'All Files',
    'myData.noFiles': 'No files yet — add files to your personal space',
    'myData.delete': 'Delete',

    // Knowledge page
    'knowledge.title': 'Knowledge View',
    'knowledge.subtitle': 'Your organized knowledge system',
    'knowledge.collections': 'Collections',
    'knowledge.notes': 'Notes & Summaries',
    'knowledge.packs': 'Context Packs',
    'knowledge.emptyCollections': 'No Collections yet — organize files first',
    'knowledge.emptyPacks': 'No Context Packs yet',
    'knowledge.emptyNotes': 'No Notes & Entities — build graph first',
    'knowledge.loadFailed': 'Failed to load data',
    'knowledge.organize': 'Organize files first to build knowledge system',

    // Graph page
    'graph.globalTitle': 'Global Graph',
    'graph.globalSubtitle': 'Overview of all connections',
    'graph.localTitle': 'Local Graph',
    'graph.localSubtitle': 'Node-focused neighborhood view',
    'graph.searchPlaceholder': 'Search nodes...',
    'graph.filterFile': 'File',
    'graph.rebuild': 'Rebuild Graph',
    'graph.emptyTitle': 'No Knowledge Graph yet',
    'graph.emptyHint': 'Organize files first to build graph',
    'graph.selectLocal': 'Select a node from Global Graph first',

    // Detail panel
    'detail.summary': 'Summary',
    'detail.metadata': 'Metadata',
    'detail.relations': 'Relations',
    'detail.showLocal': 'Show Local Graph',
    'detail.askAi': 'Ask AI about this',
    'detail.noSummary': 'No summary',

    // Chat page
    'chat.title': 'AI Chat',
    'chat.subtitle': 'AI uses your data, relations, and context to respond',
    'chat.welcome': 'Hi! Ask anything about your data',
    'chat.welcomeSub': 'AI uses Profile, Context Packs, Files, and Knowledge Graph to answer',
    'chat.placeholder': 'Ask about your data...',
    'chat.profileNotSet': 'Not set',
    'chat.profileActive': 'Active',

    // Sources panel
    'sources.title': 'Evidence Used',
    'sources.profile': '👤 Profile',
    'sources.packs': '📦 Context Packs',
    'sources.files': '📄 Files Used',
    'sources.graph': '🔗 Nodes & Edges',
    'sources.reasoning': '🧠 Reasoning',
    'sources.evidence': '📊 Evidence Graph',

    // Profile modal
    'profile.title': '👤 My Profile',
    'profile.identity': 'Who am I',
    'profile.goals': 'My Goals',
    'profile.style': 'Work Style',
    'profile.output': 'Answer Preference',
    'profile.background': 'Important Context',
    'profile.save': 'Save Profile',
    'profile.identityPh': 'e.g. Graduate student in Science...',
    'profile.goalsPh': 'e.g. Researching about...',
    'profile.stylePh': 'e.g. Prefer structured data...',
    'profile.outputPh': 'e.g. Short and to the point...',
    'profile.backgroundPh': 'e.g. Working on a project...',

    // Confirm modal
    'confirm.cancel': 'Cancel',
    'confirm.ok': 'Confirm',

    // Toasts / dynamic
    'toast.uploaded': 'Upload complete',
    'toast.deleted': 'Deleted successfully',
    'toast.profileSaved': 'Profile saved',
    'toast.organized': 'Organization complete',
    'toast.enriched': 'Metadata enriched',
    'toast.graphBuilt': 'Graph built successfully',
    'toast.error': 'An error occurred',
  }
};

// Get current language — default TH
function getLang() {
  return localStorage.getItem('projectkey_lang') || 'th';
}

// Get translation string
function t(key) {
  const lang = getLang();
  return I18N[lang]?.[key] || I18N['en']?.[key] || key;
}

// Apply translations to all [data-i18n] elements
function applyLanguage(lang) {
  localStorage.setItem('projectkey_lang', lang);
  document.documentElement.lang = lang;

  // Update all data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const translated = I18N[lang]?.[key] || I18N['en']?.[key] || el.textContent;
    el.textContent = translated;
  });

  // Update placeholders
  const searchInput = document.getElementById('graph-search-input');
  if (searchInput) searchInput.placeholder = t('graph.searchPlaceholder');

  const chatInput = document.getElementById('chat-input');
  if (chatInput) chatInput.placeholder = t('chat.placeholder');

  // Update profile placeholders
  const phMap = {
    'profile-identity': 'profile.identityPh',
    'profile-goals': 'profile.goalsPh',
    'profile-style': 'profile.stylePh',
    'profile-output': 'profile.outputPh',
    'profile-background': 'profile.backgroundPh',
  };
  for (const [id, key] of Object.entries(phMap)) {
    const el = document.getElementById(id);
    if (el) el.placeholder = t(key);
  }

  // Update toggle button labels
  const labelEl = document.getElementById('lang-label');
  const altEl = document.getElementById('lang-alt');
  if (labelEl) labelEl.textContent = lang === 'th' ? 'TH' : 'EN';
  if (altEl) altEl.textContent = lang === 'th' ? 'EN' : 'TH';
}

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  // Apply saved language immediately
  applyLanguage(getLang());

  // Language toggle button
  document.getElementById('lang-toggle')?.addEventListener('click', () => {
    const newLang = getLang() === 'th' ? 'en' : 'th';
    applyLanguage(newLang);
    // Re-render dynamic content with new language
    loadFiles();
  });

  initNavigation();
  initUpload();
  initProfile();
  initChat();
  initGraphControls();
  initKnowledgeTabs();
  loadStats();
  loadFiles();
});

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
function initNavigation() {
  document.querySelectorAll('.nav-item[data-page]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      switchPage(link.dataset.page);
    });
  });
}

function switchPage(page) {
  state.currentPage = page;
  document.querySelectorAll('.nav-item[data-page]').forEach(el => el.classList.remove('active'));
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');

  if (page === 'knowledge') loadKnowledge();
  if (page === 'graph') loadGraph();
  if (page === 'chat') loadProfile();
}

// ═══════════════════════════════════════════
// STATS
// ═══════════════════════════════════════════
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('stat-files').textContent = data.total_files;
    document.getElementById('stat-clusters').textContent = data.total_clusters;
    document.getElementById('stat-nodes').textContent = data.total_nodes || 0;
    document.getElementById('stat-edges').textContent = data.total_edges || 0;
    document.getElementById('stat-packs').textContent = data.total_context_packs;
    const dot = document.getElementById('profile-dot');
    if (dot) dot.className = `profile-status-dot ${data.profile_set ? 'active' : ''}`;
  } catch (e) { console.error('Stats error:', e); }
}

// ═══════════════════════════════════════════
// FILE UPLOAD & LIST
// ═══════════════════════════════════════════
function initUpload() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    uploadFiles(e.dataTransfer.files);
  });
  input.addEventListener('change', () => { uploadFiles(input.files); input.value = ''; });

  document.getElementById('btn-organize')?.addEventListener('click', runOrganize);
  document.getElementById('btn-enrich')?.addEventListener('click', runEnrich);
}

async function uploadFiles(fileList) {
  const form = new FormData();
  for (const f of fileList) form.append('files', f);
  try {
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    showToast(`${t('toast.uploaded')} ${data.count} ${t('stat.files').toLowerCase()}`, 'success');
    loadFiles();
    loadStats();
  } catch (e) { showToast(t('toast.error'), 'error'); }
}

async function loadFiles() {
  try {
    const res = await fetch('/api/files');
    const data = await res.json();
    renderFileList(data.files);
    document.getElementById('file-count-badge').textContent = data.files.length;
  } catch (e) { console.error('Load files error:', e); }
}

function renderFileList(files) {
  const container = document.getElementById('file-list');
  if (!files.length) {
    container.innerHTML = `<div class="empty-state"><p>${t('myData.noFiles')}</p></div>`;
    return;
  }
  container.innerHTML = files.map(f => {
    const tags = (f.tags || []).map(tag => `<span class="tag-chip">${tag}</span>`).join('');
    const freshness = f.freshness && f.freshness !== 'current' ? `<span class="freshness-badge ${f.freshness}">${f.freshness}</span>` : '';
    const sot = f.source_of_truth ? '<span class="sot-badge">📌 Source of Truth</span>' : '';
    return `
      <div class="file-item" data-id="${f.id}">
        <div class="file-icon ${f.filetype}">${f.filetype.toUpperCase()}</div>
        <div class="file-info">
          <div class="file-name">${f.filename}</div>
          <div class="file-meta">
            <span>${f.text_length?.toLocaleString() || 0} chars</span>
            <span class="status-dot ${f.processing_status}"></span>
            ${freshness} ${sot}
          </div>
          ${tags ? `<div class="file-tags">${tags}</div>` : ''}
        </div>
        <div class="file-actions">
          <button class="btn-sm" onclick="deleteFile('${f.id}')">${t('myData.delete')}</button>
        </div>
      </div>`;
  }).join('');
}

async function deleteFile(id) {
  if (!await showConfirm(getLang() === 'th' ? 'ต้องการลบไฟล์นี้?' : 'Delete this file?')) return;
  try {
    await fetch(`/api/files/${id}`, { method: 'DELETE' });
    showToast(t('toast.deleted'), 'success');
    loadFiles();
    loadStats();
  } catch (e) { showToast(t('toast.error'), 'error'); }
}

async function runOrganize() {
  const btn = document.getElementById('btn-organize');
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังจัดระเบียบ...' : 'Organizing...'}`;
  try {
    const res = await fetch('/api/organize', { method: 'POST' });
    const data = await res.json();
    showToast(`${t('toast.organized')} (${data.graph?.nodes || 0} nodes, ${data.graph?.edges || 0} edges)`, 'success');
    loadFiles();
    loadStats();
  } catch (e) { showToast(t('toast.error'), 'error'); }
  btn.disabled = false;
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M2 12h20"/></svg> <span data-i18n="myData.organize">${t('myData.organize')}</span>`;
}

async function runEnrich() {
  const btn = document.getElementById('btn-enrich');
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลัง Enrich...' : 'Enriching...'}`;
  try {
    const res = await fetch('/api/metadata/enrich', { method: 'POST' });
    const data = await res.json();
    showToast(`${t('toast.enriched')} ${data.enriched}/${data.total}`, 'success');
    loadFiles();
  } catch (e) { showToast(t('toast.error'), 'error'); }
  btn.disabled = false;
  btn.innerHTML = `<span data-i18n="myData.enrich">${t('myData.enrich')}</span>`;
}

// ═══════════════════════════════════════════
// KNOWLEDGE VIEW
// ═══════════════════════════════════════════
function initKnowledgeTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.knowledgeTab = btn.dataset.tab;
      loadKnowledge();
    });
  });
}

async function loadKnowledge() {
  const container = document.getElementById('knowledge-content');
  if (state.knowledgeTab === 'collections') {
    try {
      const res = await fetch('/api/clusters');
      const data = await res.json();
      if (!data.clusters.length) {
        container.innerHTML = `<div class="empty-state"><p>${t('knowledge.emptyCollections')}</p></div>`;
        return;
      }
      container.innerHTML = data.clusters.map(c => `
        <div class="cluster-card">
          <div class="cluster-title">📁 ${c.title} <span class="badge">${c.file_count}</span></div>
          <div class="cluster-summary">${c.summary || ''}</div>
          <div class="cluster-files">
            ${c.files.map(f => `<span class="cluster-file-chip">${f.filename}</span>`).join('')}
          </div>
        </div>`).join('');
    } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
  } else if (state.knowledgeTab === 'packs') {
    try {
      const res = await fetch('/api/context-packs');
      const data = await res.json();
      if (!data.packs.length) {
        container.innerHTML = `<div class="empty-state"><p>${t('knowledge.emptyPacks')}</p></div>`;
        return;
      }
      container.innerHTML = data.packs.map(p => `
        <div class="cluster-card">
          <div class="cluster-title">📦 ${p.title} <span class="badge">${p.type}</span></div>
          <div class="cluster-summary">${p.summary_text?.substring(0, 200) || ''}...</div>
        </div>`).join('');
    } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
  } else if (state.knowledgeTab === 'notes') {
    try {
      const res = await fetch('/api/graph/nodes?family=entity');
      const data = await res.json();
      if (!data.nodes.length) {
        container.innerHTML = `<div class="empty-state"><p>${t('knowledge.emptyNotes')}</p></div>`;
        return;
      }
      container.innerHTML = data.nodes.map(n => `
        <div class="cluster-card" style="cursor:pointer" onclick="showNodeInGraph('${n.id}')">
          <div class="cluster-title">
            <span class="dot" style="background:${NODE_COLORS[n.node_family] || '#888'}"></span>
            ${n.label}
            <span class="badge">${n.object_type}</span>
          </div>
        </div>`).join('');
    } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
  }
}

function showNodeInGraph(nodeId) {
  state.localNodeId = nodeId;
  state.graphMode = 'local';
  switchPage('graph');
}

// ═══════════════════════════════════════════
// GRAPH (Obsidian-style)
// ═══════════════════════════════════════════
let _zoomBehavior = null;

function getNodeRadius(d) {
  return 5 + (d.importance || 0.5) * 12;
}

function initGraphControls() {
  document.getElementById('graph-global-btn')?.addEventListener('click', () => {
    state.graphMode = 'global';
    document.getElementById('graph-global-btn').classList.add('active');
    document.getElementById('graph-local-btn').classList.remove('active');
    document.getElementById('local-controls').classList.add('hidden');
    document.getElementById('graph-page-title').textContent = t('graph.globalTitle');
    document.getElementById('graph-page-subtitle').textContent = t('graph.globalSubtitle');
    loadGraph();
  });

  document.getElementById('graph-local-btn')?.addEventListener('click', () => {
    state.graphMode = 'local';
    document.getElementById('graph-local-btn').classList.add('active');
    document.getElementById('graph-global-btn').classList.remove('active');
    document.getElementById('local-controls').classList.remove('hidden');
    document.getElementById('graph-page-title').textContent = t('graph.localTitle');
    document.getElementById('graph-page-subtitle').textContent = t('graph.localSubtitle');
    loadGraph();
  });

  document.getElementById('btn-rebuild-graph')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-rebuild-graph');
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังสร้าง...' : 'Building...'}`;
    try {
      await fetch('/api/graph/build', { method: 'POST' });
      showToast(t('toast.graphBuilt'), 'success');
      loadGraph();
      loadStats();
    } catch (e) { showToast(t('toast.error'), 'error'); }
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> <span data-i18n="graph.rebuild">${t('graph.rebuild')}</span>`;
  });

  document.querySelectorAll('.filter-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      const family = chip.dataset.family;
      state.filters[family] = chip.classList.contains('active');
      renderGraph();
    });
  });

  // Debounced search with zoom-to-node
  let searchTimeout;
  document.getElementById('graph-search-input')?.addEventListener('input', e => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        // Clear search — restore all
        d3.selectAll('.graph-node').classed('dimmed', false).classed('neighbor', false);
        d3.selectAll('.graph-edge-line').classed('dimmed', false).classed('highlighted', false);
        return;
      }
      // Find matching nodes
      const matchIds = new Set();
      d3.selectAll('.graph-node').each(function(d) {
        if (d.label.toLowerCase().includes(q)) matchIds.add(d.id);
      });
      // Dim non-matching, highlight matching
      d3.selectAll('.graph-node')
        .classed('dimmed', d => !matchIds.has(d.id))
        .classed('neighbor', d => matchIds.has(d.id));
      d3.selectAll('.graph-edge-line')
        .classed('dimmed', d => !matchIds.has(d.source.id) && !matchIds.has(d.target.id))
        .classed('highlighted', d => matchIds.has(d.source.id) || matchIds.has(d.target.id));
      // Zoom to first match
      if (matchIds.size && _zoomBehavior) {
        const firstMatch = state.graphData.nodes.find(n => matchIds.has(n.id));
        if (firstMatch && firstMatch.x !== undefined) {
          const svg = d3.select('#graph-svg');
          const container = document.getElementById('graph-canvas');
          const w = container.clientWidth, h = container.clientHeight;
          svg.transition().duration(500).call(
            _zoomBehavior.transform,
            d3.zoomIdentity.translate(w/2 - firstMatch.x * 1.5, h/2 - firstMatch.y * 1.5).scale(1.5)
          );
        }
      }
    }, 250);
  });

  document.getElementById('depth-slider')?.addEventListener('input', e => {
    document.getElementById('depth-value').textContent = e.target.value;
    if (state.graphMode === 'local' && state.localNodeId) loadGraph();
  });

  document.getElementById('close-detail')?.addEventListener('click', () => {
    document.getElementById('detail-panel').classList.add('hidden');
    state.selectedNodeId = null;
    d3.selectAll('.graph-node').classed('selected', false);
  });

  document.getElementById('detail-open-local')?.addEventListener('click', () => {
    if (state.selectedNodeId) {
      state.localNodeId = state.selectedNodeId;
      state.graphMode = 'local';
      document.getElementById('graph-local-btn').click();
    }
  });

  document.getElementById('detail-ask-ai')?.addEventListener('click', () => {
    const label = document.getElementById('detail-label').textContent;
    switchPage('chat');
    document.getElementById('chat-input').value = getLang() === 'th' ? `อธิบายเกี่ยวกับ "${label}" ให้หน่อย` : `Tell me about "${label}"`;
    document.getElementById('chat-input').focus();
  });

  // Zoom controls
  document.getElementById('zoom-in-btn')?.addEventListener('click', () => {
    const svg = d3.select('#graph-svg');
    if (_zoomBehavior) svg.transition().duration(300).call(_zoomBehavior.scaleBy, 1.4);
  });
  document.getElementById('zoom-out-btn')?.addEventListener('click', () => {
    const svg = d3.select('#graph-svg');
    if (_zoomBehavior) svg.transition().duration(300).call(_zoomBehavior.scaleBy, 0.7);
  });
  document.getElementById('zoom-fit-btn')?.addEventListener('click', fitGraphToView);
}

function fitGraphToView() {
  if (!state.graphData.nodes.length || !_zoomBehavior) return;
  const svg = d3.select('#graph-svg');
  const container = document.getElementById('graph-canvas');
  const w = container.clientWidth, h = container.clientHeight;
  const nodes = state.graphData.nodes.filter(n => n.x !== undefined);
  if (!nodes.length) return;

  const xExtent = d3.extent(nodes, d => d.x);
  const yExtent = d3.extent(nodes, d => d.y);
  const dx = (xExtent[1] - xExtent[0]) || 100;
  const dy = (yExtent[1] - yExtent[0]) || 100;
  const cx = (xExtent[0] + xExtent[1]) / 2;
  const cy = (yExtent[0] + yExtent[1]) / 2;
  const scale = Math.min(0.85 * w / dx, 0.85 * h / dy, 2);

  svg.transition().duration(500).ease(d3.easeCubicOut).call(
    _zoomBehavior.transform,
    d3.zoomIdentity.translate(w/2 - cx * scale, h/2 - cy * scale).scale(scale)
  );
}

async function loadGraph() {
  let url = '/api/graph/global';
  if (state.graphMode === 'local' && state.localNodeId) {
    const depth = document.getElementById('depth-slider')?.value || 1;
    url = `/api/graph/neighborhood/${state.localNodeId}?depth=${depth}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();
    state.graphData = { nodes: data.nodes || [], edges: data.edges || [] };

    const empty = document.getElementById('graph-empty');
    if (!state.graphData.nodes.length) {
      empty?.classList.remove('hidden');
      d3.select('#graph-svg').selectAll('*').remove();
      return;
    }
    empty?.classList.add('hidden');
    renderGraph();
  } catch (e) {
    console.error('Graph load error:', e);
  }
}

function renderGraph() {
  const svg = d3.select('#graph-svg');
  svg.selectAll('*').remove();

  const container = document.getElementById('graph-canvas');
  const width = container.clientWidth;
  const height = container.clientHeight;

  // ── Filter nodes by family
  const visibleFamilies = Object.keys(state.filters).filter(k => state.filters[k]);
  const nodes = state.graphData.nodes.filter(n =>
    visibleFamilies.includes(n.node_family) || visibleFamilies.includes(n.object_type)
  );
  const nodeIds = new Set(nodes.map(n => n.id));
  const edges = state.graphData.edges.filter(e => nodeIds.has(e.source?.id || e.source) && nodeIds.has(e.target?.id || e.target));

  // Update info overlay
  const ncEl = document.getElementById('graph-node-count');
  const ecEl = document.getElementById('graph-edge-count');
  if (ncEl) ncEl.textContent = nodes.length;
  if (ecEl) ecEl.textContent = edges.length;

  // ── Build adjacency map (for neighbor highlight)
  const adjacency = new Map();
  nodes.forEach(n => adjacency.set(n.id, new Set()));
  edges.forEach(e => {
    const sid = e.source?.id || e.source;
    const tid = e.target?.id || e.target;
    if (adjacency.has(sid)) adjacency.get(sid).add(tid);
    if (adjacency.has(tid)) adjacency.get(tid).add(sid);
  });

  // ── Count connections per node (for force strength)
  const linkCount = new Map();
  edges.forEach(e => {
    const sid = e.source?.id || e.source;
    const tid = e.target?.id || e.target;
    linkCount.set(sid, (linkCount.get(sid) || 0) + 1);
    linkCount.set(tid, (linkCount.get(tid) || 0) + 1);
  });

  // ── Zoom behavior
  let currentZoom = 1;
  const zoom = d3.zoom()
    .scaleExtent([0.15, 5])
    .on('zoom', e => {
      g.attr('transform', e.transform);
      currentZoom = e.transform.k;
      // Label culling based on zoom level (Obsidian-style)
      nodeGroup.selectAll('.graph-node').classed('hide-label', d => {
        if (currentZoom > 1.0) return false; // Show all at high zoom
        if (currentZoom > 0.5) return (d.importance || 0.5) < 0.6; // Only important at mid zoom
        return true; // Hide all labels at low zoom
      });
    });

  svg.call(zoom);
  _zoomBehavior = zoom;

  const g = svg.append('g');

  // ── SVG Defs: Glow filter
  const defs = svg.append('defs');
  const glowFilter = defs.append('filter').attr('id', 'nodeGlow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
  glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
  const merge = glowFilter.append('feMerge');
  merge.append('feMergeNode').attr('in', 'blur');
  merge.append('feMergeNode').attr('in', 'SourceGraphic');

  // ── Simulation (tuned for stability)
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id)
      .distance(d => 55 + (d.weight || 0.5) * 45)
      .strength(d => {
        const sc = linkCount.get(d.source?.id || d.source) || 1;
        const tc = linkCount.get(d.target?.id || d.target) || 1;
        return 1 / Math.min(sc, tc);
      })
    )
    .force('charge', d3.forceManyBody()
      .strength(d => -60 - (d.importance || 0.5) * 100)
      .distanceMax(350)
    )
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.04))
    .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 5).iterations(2))
    .force('x', d3.forceX(width / 2).strength(0.025))
    .force('y', d3.forceY(height / 2).strength(0.025))
    .alphaDecay(0.03)
    .velocityDecay(0.45);

  state.simulation = simulation;

  // ── PRE-COMPUTE: Run 120 ticks for instant stability (Obsidian pattern)
  simulation.stop();
  for (let i = 0; i < 120; i++) simulation.tick();

  // ── Draw edges
  const linkGroup = g.append('g');
  const link = linkGroup.selectAll('line')
    .data(edges)
    .join('line')
    .attr('class', 'graph-edge-line')
    .attr('stroke', 'rgba(255,255,255,0.05)')
    .attr('stroke-width', d => Math.max(0.5, (d.weight || 0.5) * 1.5))
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  // ── Draw nodes
  const nodeGroup = g.append('g');
  const node = nodeGroup.selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'graph-node')
    .attr('transform', d => `translate(${d.x},${d.y})`)
    .call(d3.drag()
      .on('start', (e, d) => {
        if (!e.active) simulation.alphaTarget(0.15).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => {
        if (!e.active) simulation.alphaTarget(0);
        // Sticky drag — keep pinned (Obsidian behavior)
        // Node stays where user dropped it
      })
    )
    .on('click', (e, d) => { e.stopPropagation(); selectNode(d); })
    .on('mouseenter', (e, d) => handleNodeHover(d, true, adjacency))
    .on('mouseleave', (e, d) => handleNodeHover(d, false, adjacency));

  // Glow circle (outer, colored, blurred)
  node.append('circle')
    .attr('class', 'node-glow')
    .attr('r', d => getNodeRadius(d) + 8)
    .attr('fill', d => NODE_COLORS[d.node_family] || '#888')
    .attr('filter', 'url(#nodeGlow)');

  // Core circle
  node.append('circle')
    .attr('class', 'node-core')
    .attr('r', d => getNodeRadius(d))
    .attr('fill', d => NODE_COLORS[d.node_family] || '#888')
    .attr('fill-opacity', 0.85)
    .attr('stroke', d => NODE_COLORS[d.node_family] || '#888')
    .attr('stroke-opacity', 0.3)
    .attr('stroke-width', 1.5);

  // Label
  node.append('text')
    .text(d => d.label.length > 16 ? d.label.substring(0, 16) + '…' : d.label)
    .attr('dy', d => getNodeRadius(d) + 14)
    .attr('font-size', '9px');

  // Center node highlight for local graph
  if (state.graphMode === 'local' && state.localNodeId) {
    node.filter(d => d.id === state.localNodeId)
      .select('.node-core')
      .attr('stroke', 'white')
      .attr('stroke-width', 3)
      .attr('stroke-opacity', 1);
  }

  // Apply initial label culling
  node.classed('hide-label', d => (d.importance || 0.5) < 0.6);

  // ── Continue simulation at low alpha for minor micro-adjustments
  simulation.alpha(0.08).restart();

  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });

  // Click on empty space → deselect
  svg.on('click', () => {
    state.selectedNodeId = null;
    document.getElementById('detail-panel').classList.add('hidden');
    d3.selectAll('.graph-node').classed('selected', false);
  });

  // Fit to view after a short delay
  setTimeout(fitGraphToView, 200);
}

// ── Hover: Dim All + Highlight Neighbors (Obsidian behavior)
function handleNodeHover(d, isEntering, adjacency) {
  const tooltip = document.getElementById('graph-tooltip');

  if (isEntering) {
    const neighbors = adjacency.get(d.id) || new Set();

    // Dim all nodes except hovered + neighbors
    d3.selectAll('.graph-node')
      .classed('dimmed', n => n.id !== d.id && !neighbors.has(n.id))
      .classed('neighbor', n => neighbors.has(n.id));

    // Dim all edges except those connecting to hovered node
    d3.selectAll('.graph-edge-line')
      .classed('dimmed', e => e.source.id !== d.id && e.target.id !== d.id)
      .classed('highlighted', e => e.source.id === d.id || e.target.id === d.id)
      .attr('stroke', e => {
        if (e.source.id === d.id || e.target.id === d.id) {
          return NODE_COLORS[d.node_family] || '#888';
        }
        return 'rgba(255,255,255,0.05)';
      });

    // Show tooltip
    if (tooltip) {
      document.getElementById('tooltip-label').textContent = d.label;
      document.getElementById('tooltip-type').textContent = `${d.object_type} · ${((d.importance || 0.5) * 100).toFixed(0)}%`;
      tooltip.classList.remove('hidden');
      // Position near mouse
      const container = document.getElementById('graph-canvas');
      const rect = container.getBoundingClientRect();
      const svgEl = document.getElementById('graph-svg');
      const pt = svgEl.createSVGPoint();
      pt.x = d.x; pt.y = d.y;
      const ctm = svgEl.querySelector('g')?.getCTM();
      if (ctm) {
        const transformed = pt.matrixTransform(ctm);
        tooltip.style.left = Math.min(transformed.x + 15, rect.width - 260) + 'px';
        tooltip.style.top = Math.min(transformed.y - 10, rect.height - 60) + 'px';
      }
    }
  } else {
    // Restore all
    d3.selectAll('.graph-node').classed('dimmed', false).classed('neighbor', false);
    d3.selectAll('.graph-edge-line')
      .classed('dimmed', false)
      .classed('highlighted', false)
      .attr('stroke', 'rgba(255,255,255,0.05)');

    // Hide tooltip
    if (tooltip) tooltip.classList.add('hidden');
  }
}

async function selectNode(d) {
  state.selectedNodeId = d.id;

  // Highlight
  d3.selectAll('.graph-node').classed('selected', false);
  d3.selectAll('.graph-node').filter(n => n.id === d.id).classed('selected', true);

  // Show detail panel
  const panel = document.getElementById('detail-panel');
  panel.classList.remove('hidden');

  document.getElementById('detail-label').textContent = d.label;

  const badge = document.getElementById('detail-type');
  badge.textContent = d.object_type;
  badge.style.background = (NODE_COLORS[d.node_family] || '#888') + '20';
  badge.style.color = NODE_COLORS[d.node_family] || '#888';

  // Fetch detail
  try {
    const res = await fetch(`/api/graph/nodes/${d.id}`);
    const detail = await res.json();

    document.getElementById('detail-summary').textContent = detail.summary || t('detail.noSummary');

    // Metadata
    const metaGrid = document.getElementById('detail-metadata');
    metaGrid.innerHTML = `
      <span class="meta-key">Type</span><span class="meta-value">${detail.object_type}</span>
      <span class="meta-key">Importance</span><span class="meta-value">${(detail.importance * 100).toFixed(0)}%</span>
      <span class="meta-key">Freshness</span><span class="meta-value">${(detail.freshness * 100).toFixed(0)}%</span>
    `;

    // Relations
    const relDiv = document.getElementById('detail-relations');
    const allRels = [
      ...detail.outgoing.map(r => ({ ...r, dir: '→', label: r.target_label, type: r.edge_type })),
      ...detail.incoming.map(r => ({ ...r, dir: '←', label: r.source_label, type: r.edge_type })),
    ];

    if (allRels.length) {
      relDiv.innerHTML = allRels.slice(0, 10).map(r => `
        <div class="relation-item">
          <span>${r.dir}</span>
          <span style="flex:1">${r.label}</span>
          <span class="relation-type-label">${r.type}</span>
        </div>`).join('');
    } else {
      relDiv.innerHTML = `<span style="font-size:12px;color:var(--text-muted)">${getLang() === 'th' ? 'ไม่มีความสัมพันธ์' : 'No relations'}</span>`;
    }
  } catch (e) {
    console.error('Node detail error:', e);
  }
}

// ═══════════════════════════════════════════
// AI CHAT
// ═══════════════════════════════════════════
function initChat() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('btn-send');

  sendBtn?.addEventListener('click', sendMessage);
  input?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;
  input.value = '';

  // Add user message
  addMessage(question, 'user');

  // Show loading
  const loadingId = addMessage(`<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังคิด...' : 'Thinking...'}`, 'assistant', true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();

    // Replace loading with answer
    removeMessage(loadingId);
    const msgHtml = `${data.answer}
      <div class="injection-badge">🧠 ${data.injection_summary || 'Context injected'}</div>`;
    addMessage(msgHtml, 'assistant', true);

    // Update sources panel
    updateSourcesPanel(data);
  } catch (e) {
    removeMessage(loadingId);
    addMessage(getLang() === 'th' ? 'เกิดข้อผิดพลาดในการเชื่อมต่อ AI' : 'Error connecting to AI', 'assistant', true);
  }
}

let msgCounter = 0;
function addMessage(content, role, isHtml = false) {
  const id = `msg-${++msgCounter}`;
  const container = document.getElementById('chat-messages');
  const welcome = container.querySelector('.welcome-message');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.id = id;
  div.innerHTML = `<div class="message-bubble">${isHtml ? content : escapeHtml(content)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeMessage(id) {
  document.getElementById(id)?.remove();
}

function updateSourcesPanel(data) {
  // Profile
  document.getElementById('src-profile').innerHTML = data.profile_used
    ? `<span class="source-chip">✅ ${getLang() === 'th' ? 'โปรไฟล์ถูกใช้' : 'Profile used'}</span>`
    : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

  // Packs
  const packs = data.context_packs_used || [];
  document.getElementById('src-packs').innerHTML = packs.length
    ? packs.map(p => `<span class="source-chip">📦 ${p.title}</span>`).join('')
    : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

  // Files
  const files = data.files_used || [];
  document.getElementById('src-files').innerHTML = files.length
    ? files.map(f => `<span class="source-chip">📄 ${f.filename}</span>`).join('')
    : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

  // Graph (v3)
  const nodesUsed = data.nodes_used || [];
  const edgesUsed = data.edges_used || [];
  if (nodesUsed.length || edgesUsed.length) {
    document.getElementById('src-graph').innerHTML =
      nodesUsed.map(n => `<span class="source-chip" style="border-color:${NODE_COLORS[n.type] || '#888'}33;color:${NODE_COLORS[n.type] || '#888'}">🔗 ${n.label}</span>`).join('') +
      edgesUsed.map(e => `<span class="source-chip">↔ ${e.source} → ${e.target} (${e.type})</span>`).join('');
  } else {
    document.getElementById('src-graph').innerHTML = `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;
  }

  // Reasoning
  document.getElementById('src-reasoning').textContent = data.reasoning || '—';

  // Evidence Graph
  renderEvidenceGraph(data);
}

function renderEvidenceGraph(data) {
  const svg = d3.select('#evidence-graph-svg');
  svg.selectAll('*').remove();

  const files = data.files_used || [];
  const packs = data.context_packs_used || [];
  if (!files.length && !packs.length) return;

  const nodes = [];
  const edges = [];

  // Center: question
  nodes.push({ id: 'q', label: 'Question', family: 'entity', x: 140, y: 100 });

  files.forEach((f, i) => {
    const id = `f${i}`;
    nodes.push({ id, label: f.filename?.substring(0, 15) || f.id, family: 'source_file' });
    edges.push({ source: 'q', target: id });
  });

  packs.forEach((p, i) => {
    const id = `p${i}`;
    nodes.push({ id, label: p.title?.substring(0, 15) || p.id, family: 'context_pack' });
    edges.push({ source: 'q', target: id });
  });

  if (data.profile_used) {
    nodes.push({ id: 'prof', label: 'Profile', family: 'person' });
    edges.push({ source: 'q', target: 'prof' });
  }

  // Simple force simulation
  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(50))
    .force('charge', d3.forceManyBody().strength(-60))
    .force('center', d3.forceCenter(140, 100))
    .stop();

  for (let i = 0; i < 100; i++) sim.tick();

  svg.selectAll('line')
    .data(edges)
    .join('line')
    .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
    .attr('stroke', 'rgba(255,255,255,0.15)')
    .attr('stroke-width', 1);

  const nodeG = svg.selectAll('g')
    .data(nodes)
    .join('g')
    .attr('transform', d => `translate(${d.x},${d.y})`);

  nodeG.append('circle')
    .attr('r', 6)
    .attr('fill', d => NODE_COLORS[d.family] || '#888')
    .attr('fill-opacity', 0.8);

  nodeG.append('text')
    .text(d => d.label)
    .attr('dy', 16)
    .attr('text-anchor', 'middle')
    .attr('fill', 'rgba(255,255,255,0.5)')
    .attr('font-size', '8px');
}

// ═══════════════════════════════════════════
// PROFILE
// ═══════════════════════════════════════════
function initProfile() {
  document.getElementById('profile-trigger')?.addEventListener('click', e => {
    e.preventDefault();
    document.getElementById('profile-modal').classList.remove('hidden');
    loadProfile();
  });

  document.getElementById('close-profile-modal')?.addEventListener('click', () => {
    document.getElementById('profile-modal').classList.add('hidden');
  });

  document.getElementById('btn-save-profile')?.addEventListener('click', saveProfile);
}

async function loadProfile() {
  try {
    const res = await fetch('/api/profile');
    const p = await res.json();
    document.getElementById('profile-identity').value = p.identity_summary || '';
    document.getElementById('profile-goals').value = p.goals || '';
    document.getElementById('profile-style').value = p.working_style || '';
    document.getElementById('profile-output').value = p.preferred_output_style || '';
    document.getElementById('profile-background').value = p.background_context || '';

    const isSet = !!(p.identity_summary || p.goals);
    const indicator = document.getElementById('chat-profile-status');
    if (indicator) indicator.textContent = isSet ? 'Active' : 'Not set';
    const dot = document.querySelector('.chat-header .profile-dot');
    if (dot) dot.className = `profile-dot ${isSet ? 'active' : ''}`;
  } catch (e) { console.error('Profile load error:', e); }
}

async function saveProfile() {
  const data = {
    identity_summary: document.getElementById('profile-identity').value,
    goals: document.getElementById('profile-goals').value,
    working_style: document.getElementById('profile-style').value,
    preferred_output_style: document.getElementById('profile-output').value,
    background_context: document.getElementById('profile-background').value,
  };
  try {
    await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    showToast(t('toast.profileSaved'), 'success');
    document.getElementById('profile-modal').classList.add('hidden');
    loadStats();
  } catch (e) { showToast(t('toast.error'), 'error'); }
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function showConfirm(message) {
  return new Promise(resolve => {
    const modal = document.getElementById('confirm-modal');
    document.getElementById('confirm-message').textContent = message;
    modal.classList.remove('hidden');

    const ok = document.getElementById('confirm-ok');
    const cancel = document.getElementById('confirm-cancel');

    const cleanup = (result) => {
      modal.classList.add('hidden');
      ok.removeEventListener('click', onOk);
      cancel.removeEventListener('click', onCancel);
      resolve(result);
    };

    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);

    ok.addEventListener('click', onOk);
    cancel.addEventListener('click', onCancel);
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
