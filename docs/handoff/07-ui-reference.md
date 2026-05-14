# 07 — UI Reference Pack

> **Purpose:** Visual reference + DOM structure per page สำหรับ developer ที่จะ rebuild UI
> **Approach:** Vanilla HTML/CSS — ห้ามใช้ framework (per ADR-002 + FE-001)
> **Coverage:** 8 pages + landing + modals + existing screenshots inventory

---

## 1. Page Inventory

### Public (Landing)
| File | URL | Lines | Purpose |
|---|---|---|---|
| [landing.html](../../legacy-frontend/landing.html) | `/` | 523 | Marketing + login modal |
| [pricing.html](../../legacy-frontend/pricing.html) | `/pricing` | - | Static pricing page |
| [shared_pack.html](../../legacy-frontend/shared_pack.html) | `/p/{token}` | - | Public pack share view |

### Authenticated (App)
| File | URL | Lines | Purpose |
|---|---|---|---|
| [app.html](../../legacy-frontend/app.html) | `/app` | 1,528 | All 8 pages via `.page` toggle |
| [admin.html](../../legacy-frontend/admin.html) | `/admin` | - | Admin panel (admin-only) |
| [auth-line.html](../../legacy-frontend/auth-line.html) | `/auth/line` | - | LINE account link confirm |

### Pages within app.html (class-toggle routing)
| Page ID | Title (TH/EN) | Function loader |
|---|---|---|
| `page-my-data` | ข้อมูลของฉัน / My Data | `loadFiles()` |
| `page-knowledge` | มุมมองความรู้ / Knowledge View | `loadKnowledge()` |
| `page-graph` | กราฟ / Graph | `loadGraph()` |
| `page-chat` | AI แชท / AI Chat | (lazy load on input) |
| `page-context-memory` | (built into other pages) | - |
| `page-mcp-setup` | ตั้งค่า MCP / MCP Setup | `loadMcpInfo()` |
| `page-tokens` | โทเค็น / Tokens | `loadTokens()` |
| `page-mcp-logs` | บันทึก MCP / MCP Logs | `loadMcpLogs()` |

### Slide-in Panel (not a .page)
- **Profile panel** — `.slide-panel.slide-panel-sm#profile-modal`
- Triggered by `#profile-trigger` click
- Contains: Identity / Goals / Style / Personality / BYOS Drive / LINE Bot sections

---

## 2. Existing Screenshots Inventory

จาก `d:/PDB/` root และ `d:/PDB/v9.3.0-live-shots/`:

### Landing & Auth
| File | Showing |
|---|---|
| [login-step-01-google-signin.png](../../login-step-01-google-signin.png) | Google sign-in step 1 |
| [login-verify-google.png](../../login-verify-google.png) | Google consent screen |
| [profile-test-google.png](../../profile-test-google.png) | Profile after Google login |

### App UI
| File | Showing |
|---|---|
| [v9.3.0-live-shots/01-root-full.png](../../v9.3.0-live-shots/01-root-full.png) | Landing page full |
| [v9.3.0-live-shots/04-app-explicit.png](../../v9.3.0-live-shots/04-app-explicit.png) | App shell post-login |
| [ui-test-tray-during-upload.png](../../ui-test-tray-during-upload.png) | UploadTray with file in progress |
| [smoke-mcp-01-modal-typed.png](../../smoke-mcp-01-modal-typed.png) | MCP setup modal |
| [pdb-mobile-iphone-se.png](../../pdb-mobile-iphone-se.png) | Mobile responsive (iPhone SE) |

### Drive BYOS
| File | Showing |
|---|---|
| [drive_bug_evidence_storage_mode_modal.png](../../drive_bug_evidence_storage_mode_modal.png) | Storage mode toggle modal |
| [drive_bug_storage_mode_section.png](../../drive_bug_storage_mode_section.png) | Drive section in profile |
| [v9_3_5_PROD_LIVE_banner.png](../../v9_3_5_PROD_LIVE_banner.png) | Drive reconnect banner (TH) |
| [v9_3_5_en_banner_final.png](../../v9_3_5_en_banner_final.png) | Drive reconnect banner (EN) |

**⚠️ Missing screenshots that should be captured before handoff:**
- [ ] Empty state ของแต่ละ page (My Data / Knowledge / Graph / Chat / Tokens)
- [ ] File detail panel เปิดอยู่
- [ ] Knowledge Graph full view (D3 force layout)
- [ ] Local subgraph view
- [ ] Chat with sources sidebar
- [ ] Duplicate detection modal
- [ ] Context Pack builder modal (AI builder 2-step)
- [ ] Admin panel
- [ ] All toast types (success / error / info)

→ ใช้ Playwright `npx playwright test` + screenshot script

---

## 3. App Shell Structure (app.html)

```html
<body>
  <!-- Sidebar (220px width) -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">PDB</div>
      <span class="logo-version">v9.4.8</span>
    </div>
    
    <nav class="sidebar-nav">
      <!-- Section 1: Workspace -->
      <a class="nav-item active" data-page="my-data">
        <svg class="nav-icon"><!-- icon --></svg>
        <span data-i18n="nav.myData">My Data</span>
      </a>
      <a class="nav-item" data-page="knowledge">...</a>
      <a class="nav-item" data-page="graph">...</a>
      <a class="nav-item" data-page="chat">...</a>
      
      <!-- Section 2: Connector -->
      <div class="nav-section">
        <span data-i18n="nav.connectorSection">Connector</span>
      </div>
      <a class="nav-item" data-page="mcp-setup">...</a>
      <a class="nav-item" data-page="tokens">...</a>
      <a class="nav-item" data-page="mcp-logs">...</a>
    </nav>
    
    <div class="sidebar-footer">
      <button id="profile-trigger" class="btn-ghost">
        <svg><!-- avatar --></svg>
        <span class="user-name">{name}</span>
      </button>
      <button id="lang-toggle">TH / EN</button>
    </div>
  </aside>
  
  <!-- Main content -->
  <main class="main-content">
    <section class="page active" id="page-my-data"><!-- ... --></section>
    <section class="page" id="page-knowledge"><!-- ... --></section>
    <section class="page" id="page-graph"><!-- ... --></section>
    <section class="page" id="page-chat"><!-- ... --></section>
    <section class="page" id="page-mcp-setup"><!-- ... --></section>
    <section class="page" id="page-tokens"><!-- ... --></section>
    <section class="page" id="page-mcp-logs"><!-- ... --></section>
  </main>
  
  <!-- Profile slide-in (not a .page) -->
  <div class="slide-panel slide-panel-sm" id="profile-modal">
    <!-- ... -->
  </div>
  
  <!-- Modals (overlay) -->
  <div class="modal-overlay" id="confirm-modal" hidden><!-- ... --></div>
  <div class="modal-overlay dup-modal-overlay" hidden><!-- duplicate detection --></div>
  
  <!-- Upload Tray (bottom-right floating) -->
  <div id="upload-tray" class="upload-tray" hidden><!-- ... --></div>
  
  <!-- Toast container -->
  <div id="toast-container"></div>
  
  <!-- Detail panel (right slide) -->
  <aside class="detail-panel" id="file-detail-panel" hidden><!-- ... --></aside>
</body>
```

---

## 4. Per-Page Structure

### 4.1 My Data (`#page-my-data`)

```html
<section class="page active" id="page-my-data">
  <div class="page-header">
    <div>
      <h1 class="page-title" data-i18n="myData.title">My Data</h1>
      <p class="page-subtitle" data-i18n="myData.subtitle">Your personal data space</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-outline" data-action="organize-new" data-i18n="myData.organizeNew">Organize New Files</button>
      <button class="btn btn-primary" data-action="organize-all" data-i18n="myData.organizeAll">Organize All</button>
    </div>
  </div>
  
  <!-- Upload zone -->
  <div class="upload-zone" id="upload-zone">
    <svg class="upload-icon"><!-- ... --></svg>
    <p data-i18n="myData.uploadText">Drag files here or click to select</p>
    <p class="upload-hint" data-i18n="myData.uploadHint">Supports docs / images...</p>
    <input type="file" id="file-input" multiple hidden>
  </div>
  
  <!-- Stats row -->
  <div class="stats-row">
    <div class="stat-card">
      <span class="stat-value tabular-nums">{count}</span>
      <span class="stat-label" data-i18n="stat.files">Files</span>
    </div>
    <!-- ... 5 more stat cards -->
  </div>
  
  <!-- Filters -->
  <div class="filter-row">
    <h2 data-i18n="myData.allFiles">All Files</h2>
    <div class="chip-group">
      <button class="chip is-active" data-filter="all" data-i18n="myData.filterAll">All</button>
      <button class="chip" data-filter="processed" data-i18n="myData.filterProcessed">Processed</button>
      <button class="chip" data-filter="vault" data-i18n="myData.filterVault">📦 Vault</button>
    </div>
  </div>
  
  <!-- File list -->
  <div class="file-list" id="file-list">
    <!-- Rendered by loadFiles() -->
    <!-- Each item: -->
    <div class="file-item card" data-file-id="{id}">
      <div class="file-item-head">
        <span class="file-icon">{ext-icon}</span>
        <span class="file-name">{filename}</span>
        <span class="status-pill is-active">{status}</span>
      </div>
      <div class="file-item-meta">
        <span class="tabular-nums">{size}</span> · <span>{date}</span>
      </div>
      <p class="file-summary-snippet">{summary preview...}</p>
      <div class="file-item-actions">
        <button class="btn-icon" data-action="open"><svg/></button>
        <button class="btn-icon" data-action="delete"><svg/></button>
      </div>
    </div>
  </div>
  
  <!-- Empty state (if no files) -->
  <div class="empty-state" hidden>
    <div class="empty-state-icon">📁</div>
    <h3 class="empty-state-title" data-i18n="myData.noFiles">No files yet</h3>
  </div>
</section>
```

### 4.2 Knowledge View (`#page-knowledge`)

```html
<section class="page" id="page-knowledge">
  <div class="page-header"><!-- title + subtitle --></div>
  
  <!-- Tab navigation -->
  <div class="tab-group">
    <button class="tab-btn is-active" data-tab="collections" data-i18n="knowledge.collections">Collections</button>
    <button class="tab-btn" data-tab="notes" data-i18n="knowledge.notes">Notes & Summaries</button>
    <button class="tab-btn" data-tab="packs" data-i18n="knowledge.packs">Context Packs</button>
  </div>
  
  <!-- Tab panels (only one visible) -->
  <div class="tab-panel" data-panel="collections"><!-- cluster cards --></div>
  <div class="tab-panel" data-panel="notes" hidden><!-- notes grid --></div>
  <div class="tab-panel" data-panel="packs" hidden>
    <button class="btn btn-primary">+ New Pack</button>
    <!-- pack cards -->
  </div>
</section>
```

### 4.3 Graph (`#page-graph`)

```html
<section class="page" id="page-graph">
  <div class="page-header">
    <div>
      <h1 data-i18n="graph.globalTitle">Global Graph</h1>
      <p data-i18n="graph.globalSubtitle">Overview of all connections</p>
    </div>
    <div class="header-actions">
      <input type="text" id="graph-search-input" placeholder="Search nodes..." class="form-input">
      <button class="btn btn-outline" data-action="rebuild-graph">Rebuild</button>
    </div>
  </div>
  
  <!-- Family filter chips -->
  <div class="chip-group" id="graph-filters">
    <button class="chip is-active" data-filter="source_file" style="--chip-color: var(--color-file);">File</button>
    <button class="chip is-active" data-filter="entity" style="--chip-color: var(--color-entity);">Entity</button>
    <!-- ... 5 more for tag, project, pack, person, note -->
  </div>
  
  <!-- D3 SVG container -->
  <div class="graph-container" id="graph-svg-container">
    <!-- D3 force simulation renders here -->
  </div>
  
  <!-- Mode toggle (Global / Local) -->
  <div class="graph-mode-toggle">
    <button class="btn-sm is-active" data-mode="global">Global</button>
    <button class="btn-sm" data-mode="local">Local</button>
  </div>
</section>
```

**D3 setup:**
- Force simulation with `forceLink()`, `forceManyBody()`, `forceCenter()`
- Node radius: 8-16px based on `importance_score`
- Node color: from `node_family` (gold/orange/cyan/green/teal/purple/light-green)
- Edge thickness: based on `weight` (0-1)
- Cached in `state.graphData = { nodes, edges }`

### 4.4 AI Chat (`#page-chat`)

```html
<section class="page" id="page-chat">
  <div class="chat-container">
    <!-- Messages -->
    <div class="chat-messages" id="chat-messages">
      <!-- Welcome (if empty) -->
      <div class="chat-welcome">
        <h2 data-i18n="chat.welcome">Hi! Ask anything about your data</h2>
        <p data-i18n="chat.welcomeSub">AI uses Profile, Context Packs, Files, Knowledge Graph...</p>
      </div>
      
      <!-- Each message: -->
      <div class="chat-msg chat-msg-user">{question}</div>
      <div class="chat-msg chat-msg-ai">
        <div class="chat-msg-body">{answer markdown rendered}</div>
        <button class="btn-ghost btn-sm" data-action="show-sources">Show sources</button>
      </div>
    </div>
    
    <!-- Input -->
    <div class="chat-input-row">
      <textarea id="chat-input" class="form-input" placeholder="Ask about your data..." rows="2"></textarea>
      <button class="btn btn-send"><svg><!-- send icon --></svg></button>
    </div>
    
    <!-- Profile status pill -->
    <div class="chat-status-bar">
      <span class="status-pill" id="chat-profile-status">Profile: Active</span>
      <span class="tabular-nums">{n} files in context</span>
    </div>
  </div>
  
  <!-- Sources panel (right sidebar, toggleable) -->
  <aside class="sources-panel" id="sources-panel" hidden>
    <h3 data-i18n="sources.title">Evidence Used</h3>
    <div class="sources-section">
      <h4 data-i18n="sources.profile">Profile</h4>
      <!-- profile summary -->
    </div>
    <div class="sources-section">
      <h4 data-i18n="sources.packs">Context Packs</h4>
      <!-- pack list -->
    </div>
    <div class="sources-section">
      <h4 data-i18n="sources.files">Files Used</h4>
      <!-- file cards with mode badge -->
    </div>
    <div class="sources-section">
      <h4 data-i18n="sources.graph">Nodes & Edges</h4>
      <!-- graph evidence -->
    </div>
    <div class="sources-section">
      <h4 data-i18n="sources.reasoning">Reasoning</h4>
      <p>{LLM-generated reasoning in Thai}</p>
    </div>
  </aside>
</section>
```

### 4.5 MCP Setup (`#page-mcp-setup`)

4-step wizard with copy-paste config:

```html
<section class="page" id="page-mcp-setup">
  <div class="page-header"><!-- title + subtitle --></div>
  
  <!-- Step 1: Connector URL -->
  <div class="setup-step">
    <h3 data-i18n="mcp.step1Title">Connector URL</h3>
    <p data-i18n="mcp.step1Desc">Copy URL to Claude...</p>
    <div class="code-block">
      <code id="connector-url">https://yourdomain.com/mcp/{mcp_secret}</code>
      <button class="btn-icon" data-action="copy" data-target="connector-url"><svg/></button>
    </div>
  </div>
  
  <!-- Step 2: Generate Token -->
  <div class="setup-step">
    <h3 data-i18n="mcp.step2Title">Generate Access Token</h3>
    <button class="btn btn-primary" data-action="generate-token">Generate Token</button>
    <div class="token-display" hidden>
      <code>{pk_...}</code>
      <p class="warning">{tokenWarning}</p>
    </div>
  </div>
  
  <!-- Step 3: Configure AI Client (tabs) -->
  <div class="setup-step">
    <h3 data-i18n="mcp.step3Title">Configure AI Client</h3>
    <div class="tab-group">
      <button class="tab-btn is-active" data-tab="claude">Claude Desktop</button>
      <button class="tab-btn" data-tab="chatgpt">ChatGPT</button>
      <button class="tab-btn" data-tab="antigravity">Antigravity</button>
    </div>
    <div class="tab-panel">
      <pre class="config-snippet">{platform-specific JSON config}</pre>
    </div>
  </div>
  
  <!-- Step 4: Test -->
  <div class="setup-step">
    <h3 data-i18n="mcp.step4Title">Test Connection</h3>
    <button class="btn btn-primary" data-action="test-mcp">Test</button>
    <div class="test-result"><!-- success or error --></div>
  </div>
  
  <!-- Tool list (22 tools) -->
  <div class="setup-step">
    <h3 data-i18n="mcp.availableTools">Available Tools</h3>
    <div class="tool-grid">
      <!-- For each tool: -->
      <div class="tool-card">
        <div class="tool-name">{tool_name}</div>
        <p class="tool-desc">{description}</p>
        <label class="toggle-switch">
          <input type="checkbox" data-tool="{name}" checked>
          <span class="slider"></span>
        </label>
      </div>
    </div>
  </div>
</section>
```

---

## 5. Profile Slide-in Panel

```html
<div class="slide-panel slide-panel-sm" id="profile-modal" hidden>
  <header class="slide-panel-header">
    <h2 data-i18n="profile.title">My Profile</h2>
    <button class="btn-close" data-action="close-profile"><svg/></button>
  </header>
  
  <div class="slide-panel-body">
    <!-- Section 1: Identity -->
    <section class="profile-section">
      <label data-i18n="profile.identity">Who am I</label>
      <textarea class="form-input" id="profile-identity" placeholder="e.g. Graduate student..."></textarea>
    </section>
    
    <!-- Section 2: Goals + Style + Output + Background (same pattern) -->
    
    <!-- Section 3: Personality (v6.0) -->
    <section class="profile-section">
      <h3 data-i18n="personality.title">Personality</h3>
      <p class="text-muted" data-i18n="personality.pdpa">External test links...</p>
      
      <!-- MBTI -->
      <div class="personality-card">
        <h4>MBTI</h4>
        <select id="mbti-type">
          <option value="">{notSet}</option>
          <!-- 16 options -->
        </select>
        <select id="mbti-source">
          <option value="official">Official</option>
          <option value="neris">NERIS (16personalities)</option>
          <option value="self_report">Self-report</option>
        </select>
        <a href="https://16personalities.com" target="_blank">Take it at 16personalities</a>
      </div>
      
      <!-- Enneagram -->
      <div class="personality-card">
        <h4>Enneagram</h4>
        <select id="enneagram-core">
          <option value="">{notSet}</option>
          <!-- 9 options with TH + EN labels -->
        </select>
        <select id="enneagram-wing">
          <!-- Populated by JS based on core selection -->
        </select>
      </div>
      
      <!-- CliftonStrengths Top 5 -->
      <div class="personality-card">
        <h4>CliftonStrengths Top 5</h4>
        <!-- 5 select dropdowns OR multi-select chip picker -->
      </div>
      
      <!-- VIA Top 5 -->
      <div class="personality-card">
        <h4>VIA Top 5</h4>
        <!-- 5 select dropdowns -->
      </div>
    </section>
    
    <!-- Section 4: BYOS Drive (conditional) -->
    <section class="profile-section" id="byos-section">
      <h3>Google Drive (BYOS)</h3>
      <!-- Rendered by storage_mode.js -->
    </section>
    
    <!-- Section 5: LINE Bot -->
    <section class="profile-section" id="line-section">
      <h3 data-i18n="line.title">LINE Bot</h3>
      <!-- Rendered by line_ui.js -->
    </section>
    
    <button class="btn btn-primary btn-block" data-action="save-profile" data-i18n="profile.save">Save Profile</button>
  </div>
</div>
```

---

## 6. UploadTray (Floating Bottom-Right)

```html
<div id="upload-tray" class="upload-tray is-open" hidden>
  <header class="upload-tray-header">
    <h3 data-i18n="upload.tray.title">Upload Queue</h3>
    <button class="btn-icon" data-action="close-tray"><svg/></button>
  </header>
  
  <!-- Status summary -->
  <div class="upload-tray-summary">
    <span class="status-pill is-warning">{n} queued</span>
    <span class="status-pill is-active">{n} working</span>
    <span class="status-pill is-error">{n} failed</span>
  </div>
  
  <!-- System status banner (if degraded) -->
  <div class="upload-tray-system-banner is-warning" hidden>
    <svg/> <span data-i18n="upload.tray.system_degraded">Processing slower than usual</span>
  </div>
  
  <!-- Items list -->
  <ul class="upload-tray-list">
    <li class="upload-tray-item" data-file-id="{id}">
      <div class="upload-tray-item-head">
        <span class="upload-tray-filename">{filename}</span>
        <span class="status-pill is-active">Working</span>
      </div>
      
      <div class="upload-tray-meta">
        <span class="upload-tray-ext">PDF</span>
        <span class="upload-tray-elapsed tabular-nums">Elapsed 45s</span>
        <button class="upload-tray-toggle">Details</button>
      </div>
      
      <!-- Progress -->
      <div class="upload-tray-step">{progress_step text}</div>
      <div class="meter">
        <div class="meter-fill" style="width: {pct}%"></div>
      </div>
      
      <!-- Why slow (if applicable) -->
      <div class="upload-tray-whyslow">{why_slow text}</div>
      
      <!-- Expanded details (collapsed by default) -->
      <div class="upload-tray-stages" hidden>
        <div>Queued: 12:00:01</div>
        <div>Started: 12:00:03</div>
        <div>Attempt: 1/3</div>
      </div>
      
      <!-- Actions -->
      <div class="upload-tray-actions">
        <!-- For queued/extracting: -->
        <button class="btn-sm btn-outline" data-action="cancel">Cancel</button>
        
        <!-- For error: -->
        <button class="btn-sm btn-primary" data-action="retry">Retry</button>
        <button class="btn-sm btn-ghost" data-action="dismiss">Dismiss</button>
      </div>
    </li>
  </ul>
</div>
```

---

## 7. Modal Patterns

### 7.1 Confirm Modal

```html
<div class="modal-overlay" id="confirm-modal" hidden>
  <div class="modal">
    <div class="modal-header">
      <h2 id="confirm-title">{title}</h2>
      <button class="btn-close"><svg/></button>
    </div>
    <div class="modal-body">
      <p id="confirm-message">{message}</p>
    </div>
    <div class="modal-footer">
      <button class="btn btn-outline" id="confirm-cancel" data-i18n="confirm.cancel">Cancel</button>
      <button class="btn btn-primary" id="confirm-ok" data-i18n="confirm.ok">Confirm</button>
    </div>
  </div>
</div>
```

### 7.2 Duplicate Detection Modal

```html
<div class="modal-overlay dup-modal-overlay" hidden>
  <div class="modal modal-lg">
    <div class="modal-header">
      <h2 id="dup-title">Found {count} similar files</h2>
    </div>
    <div class="modal-body">
      <p id="dup-subtitle">{subtitle}</p>
      
      <!-- Quick actions -->
      <div class="dup-quick-actions">
        <button class="btn-sm btn-outline" data-action="keep-all">Keep all</button>
        <button class="btn-sm btn-outline" data-action="skip-all">Skip all</button>
      </div>
      
      <!-- Per-file rows -->
      <ul class="dup-list">
        <li class="dup-row">
          <div class="dup-new">
            {filename} <span class="dup-label">(new)</span>
          </div>
          <div class="dup-match">
            similar to <strong>{matched_filename}</strong>
            <span class="dup-similarity">98%</span>
          </div>
          <div class="dup-actions">
            <label><input type="radio" name="dup-{id}" value="keep" checked> Keep both</label>
            <label><input type="radio" name="dup-{id}" value="skip"> Skip new</label>
          </div>
        </li>
      </ul>
    </div>
    <div class="modal-footer">
      <button class="btn btn-primary" data-action="confirm-dup">Confirm</button>
    </div>
  </div>
</div>

<!-- Undo toast (10s window) -->
<div class="toast toast-undo">
  <span>Skipping 3 new files in 10s</span>
  <button data-action="undo-skip">Undo</button>
</div>
```

### 7.3 Pack AI Builder (2-step modal)

```html
<div class="modal-overlay pack-modal-overlay" hidden>
  <div class="modal modal-lg">
    <!-- Step 1: User prompt -->
    <div class="pack-step" data-step="prompt">
      <h2>Create with AI</h2>
      <textarea class="form-input" placeholder="Describe what pack you want..."></textarea>
      <button class="btn btn-primary" data-action="clarify">Next</button>
    </div>
    
    <!-- Step 2: Clarify (4 options + freetext) -->
    <div class="pack-step" data-step="clarify" hidden>
      <h2>{LLM question}</h2>
      <div class="option-grid">
        <button class="option-card" data-option-id="1">
          <h3>{title}</h3>
          <p>{summary 25-60 words}</p>
        </button>
        <!-- ... 4 options -->
      </div>
      <textarea class="form-input" placeholder="{freetext_hint}"></textarea>
      <button class="btn btn-outline" data-action="skip-clarify">Skip</button>
    </div>
    
    <!-- Step 3: Propose (preview draft) -->
    <div class="pack-step" data-step="propose" hidden>
      <h2>Pack Preview</h2>
      <div class="pack-draft">
        <h3>{suggested_title}</h3>
        <span class="status-pill">{suggested_type}</span>
        <p><strong>Intent:</strong> {intent}</p>
        <p><strong>Scope:</strong> {scope}</p>
        <h4>Sources ({n_files} files + {n_clusters} clusters)</h4>
        <ul><!-- selected items --></ul>
      </div>
      <button class="btn btn-outline" data-action="discard">Discard</button>
      <button class="btn btn-primary" data-action="confirm-pack">Create Pack</button>
    </div>
  </div>
</div>
```

---

## 8. Toast System

```html
<div id="toast-container">
  <!-- Generated dynamically -->
  <div class="toast toast-success">
    <svg class="toast-icon"><!-- check --></svg>
    <div class="toast-msg">Upload complete</div>
    <button class="toast-close"><svg/></button>
  </div>
  
  <div class="toast toast-error">
    <svg/>
    <div class="toast-msg">Connection failed</div>
    <button class="toast-close"><svg/></button>
  </div>
  
  <div class="toast toast-info">
    <svg/>
    <div class="toast-msg">{info message}</div>
  </div>
</div>
```

**Behavior:**
- Auto-dismiss after **4 seconds**
- Stack vertically bottom-right
- Click to dismiss immediately
- Border-left accent color (green / red / indigo)

---

## 9. Layout & Responsive Behavior

### Desktop (≥ 900px)
```
┌──────┬─────────────────────────────────────────┬────────────┐
│      │                                          │            │
│ Side │              Main content                │  Detail    │
│ bar  │              (page system)               │  panel     │
│ 220px│                                          │  320px     │
│      │                                          │  (slide)   │
└──────┴─────────────────────────────────────────┴────────────┘
                                                              ↑
                                            UploadTray fixed bottom-right
```

### Tablet (768-900px)
- Sidebar: same 220px
- Detail panel: overlay (not docked)

### Mobile (< 768px)
- Sidebar: fixed overlay (hamburger toggle)
- Main: full width
- Touch targets: min 44px (WCAG 2.5.5)
- Detail panel: full-screen modal
- UploadTray: full-width sticky at bottom

### Sub-breakpoints
- 700px: narrow phone tweaks
- 600px: very narrow
- 480px: iPhone SE / small phones

---

## 10. Component Spec Sheet Reference

ดู [SDD-blueprint.md §12](00-SDD-blueprint.md) สำหรับ:
- All CSS tokens (`--space-*`, `--radius-*`, `--accent`, etc.)
- 8 canonical atoms (.btn, .card, .status-pill, .chip, .meter, .skeleton, .slide-panel, .form-input)
- Required patterns (page-header, empty-state, modal)
- Trust signals (tabular-nums, focus rings, etc.)
- Anti-AI-slop guards (no teal, no purple gradient, no uppercase labels)

หรืออ่าน [shared.css](../../legacy-frontend/shared.css) ตรงๆ — 718 lines + verbatim source

---

## 11. Screenshot Capture Script (Playwright)

สำหรับ regenerate UI reference screenshots:

```javascript
// tests/screenshots.spec.js
const { test } = require('@playwright/test');

test.describe('UI Reference Screenshots', () => {
  test.use({ viewport: { width: 1366, height: 768 } });
  
  test('Landing page', async ({ page }) => {
    await page.goto('/');
    await page.screenshot({ path: 'docs/handoff/screenshots/01-landing.png', fullPage: true });
  });
  
  test('App my-data empty', async ({ page }) => {
    // Login flow first
    await page.screenshot({ path: 'docs/handoff/screenshots/02-my-data-empty.png', fullPage: true });
  });
  
  // ... per page + mobile viewport (375x667)
});
```

รัน: `npx playwright test screenshots.spec.js`

---

**End — UI reference for PDB v9.4.8**

⚠️ **TODO ก่อน handoff:**
- [ ] รัน screenshot script ครอบคลุมทุก page + mobile
- [ ] Capture: empty states, modals, error states, full-data states
- [ ] เก็บไว้ใน `docs/handoff/screenshots/`
