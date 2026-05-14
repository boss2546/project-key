# 04 — Architecture Diagrams (Mermaid)

> **Purpose:** Visual diagrams สำหรับ developer ใช้เข้าใจ flow + ความสัมพันธ์
> **Format:** Mermaid (text-based) — render ผ่าน GitHub / VS Code Markdown Preview / Mermaid Live Editor
> **Coverage:** Database ERD + 6 sequence diagrams สำหรับ critical flows

---

## 1. Database ERD

```mermaid
erDiagram
    USERS ||--o{ FILES : owns
    USERS ||--o{ CLUSTERS : owns
    USERS ||--o{ CONTEXT_PACKS : owns
    USERS ||--o{ CONTEXT_MEMORIES : owns
    USERS ||--o| USER_PROFILES : has
    USERS ||--o| DRIVE_CONNECTIONS : has
    USERS ||--o{ MCP_TOKENS : owns
    USERS ||--o{ CHAT_QUERIES : sends
    USERS ||--o{ PERSONALITY_HISTORY : tracks
    USERS ||--o{ USAGE_LOGS : tracks
    USERS ||--o{ AUDIT_LOGS : tracks
    USERS ||--o| LINE_USERS : linked
    USERS ||--o{ GRAPH_NODES : owns
    USERS ||--o{ GRAPH_EDGES : owns
    USERS ||--o{ NOTE_OBJECTS : owns

    FILES ||--o| FILE_SUMMARIES : has
    FILES ||--o| FILE_INSIGHTS : has
    FILES ||--o{ FILE_CLUSTER_MAP : in
    
    CLUSTERS ||--o{ FILE_CLUSTER_MAP : groups
    
    CONTEXT_PACKS ||--o{ PACK_SHARES : sharable
    
    GRAPH_NODES ||--o{ GRAPH_EDGES : source
    GRAPH_NODES ||--o{ GRAPH_EDGES : target
    GRAPH_NODES ||--o{ SUGGESTED_RELATIONS : source
    
    CHAT_QUERIES ||--o| CONTEXT_INJECTION_LOGS : audit
    
    MCP_TOKENS ||--o{ MCP_USAGE_LOGS : produces

    USERS {
        string id PK
        string email UK "nullable"
        string password_hash "nullable"
        string google_sub UK "v8.1"
        boolean is_admin "v8.2"
        string mcp_secret UK "v5.1"
        string plan "free|starter|admin"
        string subscription_status
        string stripe_customer_id
        string storage_mode "managed|byos v7.0"
        boolean is_active
        timestamp created_at
    }
    
    FILES {
        string id PK
        string user_id FK
        string filename "truncated to 255 bytes v9.4.7"
        string filetype
        string raw_path
        text extracted_text
        string processing_status "uploaded|queued|extracting|organized|ready|error"
        string extraction_status "ok|empty|encrypted|ocr_failed|unsupported|partial"
        text tags "JSON array"
        string drive_file_id "v7.0"
        string content_hash "SHA-256 v7.1"
        string file_kind "processed|vault_only v9.1"
        timestamp queued_at "v9.4.0"
        timestamp extract_started_at "v9.4.0"
        timestamp extract_completed_at "v9.4.0"
        string progress_step "v9.4.0"
        int progress_pct "v9.4.0"
        string extract_error "CODE v9.4.0"
        int attempt_count "v9.4.0"
        boolean is_locked
    }
    
    USER_PROFILES {
        int id PK
        string user_id FK UK
        text identity_summary
        text goals
        text working_style
        text preferred_output_style
        string mbti_type "v6.0"
        string mbti_source
        text enneagram_data "JSON v6.0"
        text clifton_top5 "JSON v6.0"
        text via_top5 "JSON v6.0"
    }
    
    DRIVE_CONNECTIONS {
        int id PK
        string user_id FK UK
        string drive_email
        text refresh_token_encrypted "Fernet"
        string drive_root_folder_id
        timestamp last_sync_at
        string last_sync_status "pending|syncing|success|error"
        timestamp revoked_at
    }
    
    MCP_TOKENS {
        string id PK
        string user_id FK
        string token_hash UK "SHA-256"
        string label
        string scope
        boolean is_active
        timestamp last_used_at
        timestamp revoked_at
    }
```

**26 tables total** — see [SDD-blueprint.md §3](00-SDD-blueprint.md) for complete column listings.

---

## 2. Upload Pipeline (Sequence)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend (app.js)
    participant API as FastAPI<br/>/api/upload
    participant DB as SQLite<br/>(WAL mode)
    participant Worker as Async Worker
    participant Tess as Tesseract/Docling
    participant Gemini as Gemini Files API

    User->>FE: Drop file in upload zone
    FE->>FE: Validate (size, count, type)
    FE->>API: POST /api/upload (multipart)
    
    API->>API: Truncate filename to 255 bytes (v9.4.7)
    API->>API: Save raw file to disk
    API->>DB: INSERT files (status=queued, queued_at=now)
    API-->>FE: {file_id, status, estimated_wait_sec} ≤200ms
    
    FE->>FE: UploadTray.notifyEnqueued()
    FE->>FE: Open tray, start polling every 2s
    
    loop Worker loop (every 2s)
        Worker->>DB: SELECT * WHERE status='queued' ORDER BY queued_at
        Worker->>Worker: Rank by (user_pos, priority_class, queued_at)
        Worker->>DB: UPDATE atomic SET status='extracting' WHERE id=X
        DB-->>Worker: rowcount=1 ✓
        
        Worker->>Worker: Capture _main_loop ref (v9.4.6)
        
        alt File ext in [pdf, docx, xlsx, txt]
            Worker->>Tess: asyncio.to_thread(extract_text)
            Tess->>Tess: Progress callback every ≤1.5s
            Tess-->>Worker: extracted text
        else File ext in [mp3, mp4, jpg, ...]
            Worker->>Gemini: client.files.upload()
            Worker->>Gemini: wait_for_active() ≤300s
            Worker->>Gemini: generate_content(file, prompt)
            Gemini-->>Worker: response.text
        end
        
        Worker->>Worker: strip_surrogates(text)
        Worker->>DB: UPDATE files SET extracted_text, status='uploaded', pct=100
        
        Worker->>Worker: Update rolling avg (capped per class)
        
        Note over Worker: Heartbeat task<br/>(separate from main loop)<br/>writes file every 5s (v9.4.5)
    end
    
    loop Frontend polling
        FE->>API: GET /api/upload-status?file_ids=...
        API->>DB: SELECT progress_step, progress_pct, status
        API-->>FE: per-file status array
        FE->>FE: Update UploadTray UI (TC-1..6)
    end
    
    User->>FE: Click "จัดระเบียบใหม่"
    FE->>API: POST /api/organize-new
    API->>API: Background task: cluster→summarize→graph
    API-->>FE: 202 Accepted
```

**Key invariants:**
- Atomic claim SQL prevents race condition
- Progress callback uses `asyncio.run_coroutine_threadsafe(_main_loop)` (v9.4.6 fix)
- Heartbeat task separate from main loop survives long jobs (v9.4.5 fix)
- Rolling avg cap per class prevents outlier pollution (v9.4.8)

---

## 3. Chat Retrieval (7-Layer Sequence)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant Chat as /api/chat
    participant Ret as retriever.py
    participant LLM as OpenRouter<br/>Gemini Flash
    participant DB as SQLite
    participant Vec as TF-IDF<br/>vector_search

    User->>FE: Type question + click send
    FE->>Chat: POST /api/chat {question}
    
    Chat->>Ret: retrieve_and_generate(question, user_id)
    
    Note over Ret: STEP 1: Build inventory
    Ret->>DB: Fetch profile, packs, clusters, files
    Ret->>Vec: hybrid_search(question, user_id, top=5)
    Vec-->>Ret: top 5 matched file_ids
    
    Note over Ret: STEP 2: LLM selects context
    Ret->>LLM: call_llm_json(prompt #5 in catalog)
    LLM-->>Ret: {selected_cluster_id, pack_ids, files: [{file_id, mode}], reasoning}
    
    Note over Ret: STEP 3: Build context (12K char budget)
    loop For each selected source
        Ret->>DB: Fetch summary/excerpt/raw content
        Ret->>Ret: Append to context with header
    end
    
    Note over Ret: STEP 4: Graph injection (v3)
    loop For each file used
        Ret->>DB: Fetch outgoing+incoming edges (max 5/file)
        Ret->>Ret: Append edges_used + nodes_used + evidence_text
    end
    
    Note over Ret: STEP 5: Generate answer
    Ret->>LLM: call_llm(prompt #6 in catalog, context)
    LLM-->>Ret: plain text answer
    
    Note over Ret: STEP 6: Audit
    Ret->>DB: INSERT chat_queries + context_injection_logs
    
    Ret-->>Chat: {answer, sources, context_used, reasoning}
    Chat-->>FE: JSON response
    FE->>FE: Render markdown + Sources panel
```

**7 layers in priority order:**
1. User Profile (identity + goals + style + personality)
2. Context Packs (selected by LLM)
3. Files — Summary mode
4. Files — Excerpt mode (first 2000 chars)
5. Files — Raw mode (first 6000 chars)
6. Graph Nodes & Edges (v3 graph-aware)
7. Hybrid Vector Search (TF-IDF + semantic)

**MAX_CONTEXT_CHARS = 12000** (hard budget)

---

## 4. Google OAuth Flow (Drive BYOS)

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as FastAPI
    participant Google as Google OAuth
    participant Drive as Drive API
    participant DB as SQLite

    User->>FE: Click "Connect Google Drive"
    FE->>API: GET /api/drive/oauth/init
    API->>API: Generate CSRF state token<br/>Store in _STATE_CACHE (TTL 10min)
    API-->>FE: {auth_url}
    
    FE->>Google: Redirect to auth_url
    Note over Google: User consents<br/>(scopes: drive.file + offline_access)
    Google->>API: 302 /api/drive/oauth/callback?code=X&state=Y
    
    API->>API: Verify state matches cache
    API->>Google: Exchange code → tokens
    Google-->>API: {access_token, refresh_token}
    
    API->>API: Fernet.encrypt(refresh_token)
    API->>DB: INSERT drive_connections (encrypted token)
    API->>Drive: Create /Personal Data Bank/ folder
    API->>Drive: Create sub-folders (raw, extracted, summaries, ...)
    Drive-->>API: folder_ids
    API->>DB: UPDATE drive_connections SET drive_root_folder_id, storage_mode='byos'
    
    API->>FE: 302 /app?drive_connected=true
    FE->>FE: Show success toast + render Drive panel
```

**Critical:**
- `_GLOGIN_STATE_CACHE` (login) แยกจาก `_STATE_CACHE` (Drive) — intent isolation
- Refresh token = Fernet encrypted at rest
- `GOOGLE_OAUTH_MODE=testing` → 7-day refresh token expiry
- All push helpers must handle `RefreshError` → mark connection errored (STORAGE-006)

---

## 5. MCP Tool Call (JSON-RPC 2.0)

```mermaid
sequenceDiagram
    participant Claude as Claude Desktop
    participant Bridge as mcp-remote bridge
    participant MCP as /mcp/{secret}
    participant Dispatch as call_tool()
    participant Tool as mcp_tools.py
    participant DB as SQLite
    participant LLM as Gemini

    Claude->>Bridge: Local stdio JSON-RPC
    Bridge->>MCP: POST /mcp/{user_secret}<br/>{"method": "initialize"}
    MCP->>DB: SELECT users WHERE mcp_secret=:s
    MCP-->>Bridge: {protocolVersion, capabilities, serverInfo}
    
    Bridge->>MCP: POST /mcp/{user_secret}<br/>{"method": "tools/list"}
    MCP->>MCP: _build_mcp_tools_list() from TOOL_REGISTRY
    MCP-->>Bridge: 22 tool schemas
    
    Claude->>Bridge: User asks "List my files"
    Bridge->>MCP: POST /mcp/{user_secret}<br/>{"method": "tools/call", "params": {"name": "list_files"}}
    
    MCP->>MCP: Check MCP_PERMISSIONS[user_id]['list_files']
    MCP->>Dispatch: call_tool('list_files', args, user_id)
    Dispatch->>Tool: list_files(user_id)
    Tool->>DB: SELECT * FROM files WHERE user_id
    Tool-->>Dispatch: {files: [...], count: N}
    
    Dispatch->>DB: INSERT mcp_usage_logs<br/>(tool_name, latency_ms, status)
    Dispatch-->>MCP: result JSON
    
    alt Tool returns __mcp_content
        MCP->>MCP: Pass through unchanged (EmbeddedResource)
    else Normal JSON
        MCP->>MCP: Wrap in {content: [{type: "text", text: JSON.stringify(result)}]}
    end
    
    MCP-->>Bridge: {"jsonrpc": "2.0", "id": N, "result": {content: [...]}}
    Bridge-->>Claude: Tool result
```

**Auth pattern:**
- Primary: `/mcp/{secret}` (per-user UUID in URL — Claude Custom Connector ใส่ Bearer ไม่ได้)
- Secondary: `Authorization: Bearer pk_<48hex>` (SHA-256 hash lookup)

---

## 6. LINE Account Link Flow

```mermaid
sequenceDiagram
    actor User
    participant LINE as LINE App
    participant Bot as LINE Bot
    participant WH as /webhook/line
    participant API as PDB API
    participant DB as SQLite
    participant Page as /auth/line

    User->>LINE: Tap "Link Account" in rich menu
    LINE->>Bot: postback event
    Bot->>API: GET userId → linkToken (LINE SDK)
    Bot->>WH: send Flex card with deep link
    WH-->>LINE: Reply: "Tap to link..."
    LINE-->>User: Show flex card
    
    User->>LINE: Tap "Confirm Link"
    LINE->>LINE: Navigate to<br/>https://access.line.me/dialog/bot/accountLink<br/>?linkToken=X&nonce=Y
    
    Note over LINE: User consents
    
    LINE->>WH: POST /webhook/line<br/>(accountLink event with userId)
    WH->>WH: Verify HMAC-SHA256 signature
    WH->>DB: SELECT line_users WHERE link_nonce=Y
    WH->>WH: Check nonce expiry (≤10min)
    WH->>DB: UPDATE line_users SET line_user_id, linked_at
    WH->>Bot: Send "✅ Linked!" message
    Bot-->>LINE: Welcome message
    LINE-->>User: Linked notification
```

**Critical:**
- Nonce = `secrets.token_hex(32)` (64 hex chars, alphanumeric only)
- LINE rejects base64url (has `-`/`_`)
- HMAC-SHA256 signature verify on every webhook
- Server-initiated link not possible per LINE spec — must go via bot follow

---

## 7. Stripe Subscription Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant API as /api/billing/*
    participant Stripe as Stripe API
    participant WH as /api/stripe/webhook
    participant DB as SQLite

    User->>FE: Click "Upgrade to Starter"
    FE->>API: POST /api/billing/create-checkout-session
    API->>Stripe: stripe.checkout.Session.create()
    Stripe-->>API: {checkout_url}
    API-->>FE: {checkout_url}
    FE->>FE: Redirect to checkout_url
    
    User->>Stripe: Complete payment
    Stripe->>WH: POST /api/stripe/webhook<br/>(checkout.session.completed)
    
    WH->>WH: Verify signature (stripe SDK)
    WH->>DB: SELECT webhook_logs WHERE event_id=:id
    
    alt Already processed
        WH-->>Stripe: 200 (idempotent)
    else New event
        WH->>DB: INSERT webhook_logs (event_id, status=processing)
        WH->>DB: UPDATE users SET subscription_status='starter_active',<br/>plan='starter', stripe_customer_id
        WH->>DB: UPDATE webhook_logs status=processed
        WH-->>Stripe: 200
    end
    
    Stripe->>User: Redirect to /billing/success
    User->>FE: Land on /app?billing=success
    FE->>FE: Show success toast, refresh plan info
```

**Idempotency:** Webhook event_id checked in `webhook_logs` table before processing

**Events handled:**
- `checkout.session.completed` → flip to "starter_active"
- `customer.subscription.updated` → update renewal + status
- `customer.subscription.deleted` → downgrade to "free" + lock excess data
- `invoice.payment_succeeded` → audit log

---

## 8. BYOS Drive Sync (Push-then-Pull)

```mermaid
sequenceDiagram
    participant Trigger as Trigger<br/>(manual or 5min poll)
    participant Sync as drive_sync.py
    participant DB as SQLite
    participant Drive as Drive API
    participant FS as Local Disk

    Trigger->>Sync: run_full_sync(user_id)
    Sync->>DB: SELECT drive_connections WHERE user_id
    Sync->>Sync: Fernet.decrypt(refresh_token)
    Sync->>Drive: Refresh access_token
    
    alt refresh_token = invalid_grant
        Sync->>DB: UPDATE drive_connections status='error'<br/>error='INVALID_GRANT'
        Sync-->>Trigger: 200 status='completed_with_errors'
    end
    
    Note over Sync: PHASE 1: PUSH (local → Drive)
    Sync->>DB: SELECT files WHERE storage_source='local' AND drive_file_id IS NULL
    Sync->>Drive: List Drive PDB folder (F24 prevention pre-fetch)
    
    loop For each local-only file
        alt Drive has file with same name+hash
            Sync->>DB: UPDATE files SET drive_file_id (relink)
            Sync->>Sync: duplicate_push_prevented++
        else New
            Sync->>FS: Read raw file
            Sync->>Drive: Upload to /raw/
            Sync->>Drive: Upload extracted to /extracted/
            Sync->>Drive: Upload summary to /summaries/
            Sync->>DB: UPDATE files SET drive_file_id
        end
    end
    
    Note over Sync: PHASE 2: PULL (Drive → local)
    Sync->>Drive: List /raw/
    
    loop For each Drive file
        alt drive_file_id NOT in local DB
            Sync->>FS: Download file
            Sync->>DB: INSERT files (file_kind=vault_only, status=uploaded)
            Sync->>Sync: pulled_new++
        else drive_modified > cache_modified
            Sync->>FS: Re-download
            Sync->>DB: UPDATE files
            Sync->>Sync: pulled_updated++
        end
    end
    
    Note over Sync: PHASE 3: Orphan cleanup
    Sync->>DB: SELECT files WHERE drive_file_id IS NOT NULL
    
    loop Files in DB but missing in Drive
        alt Already retried 3+ times
            Sync->>Sync: orphans_skipped_budget++
        else
            Sync->>DB: Mark deleted (soft)
            Sync->>Sync: orphans_cleaned++
        end
    end
    
    Sync-->>Trigger: SyncStats {pushed_new, pulled_new, conflicts, errors, duration_ms}
```

**Conflict resolution:** Drive wins (last-write-wins on modifiedTime)
**Orphan budget:** 3 retries per file per session (in-memory dict)
**F24 prevention:** Pre-fetch Drive listing → relink if name+hash match (v9.3.5.5)

---

## 9. Frontend Page Routing (No-Hash)

```mermaid
stateDiagram-v2
    [*] --> Landing : Page load
    
    Landing --> Auth_Check : initAuth()
    Auth_Check --> App_MyData : token valid (/api/auth/me 200)
    Auth_Check --> Landing : no token or 401
    
    state App {
        [*] --> MyData
        MyData --> Knowledge : nav click
        MyData --> Graph : nav click
        MyData --> Chat : nav click
        MyData --> ContextMemory : nav click
        MyData --> MCPSetup : nav click
        MyData --> Tokens : nav click
        MyData --> MCPLogs : nav click
        
        Knowledge --> MyData
        Graph --> MyData
        Chat --> MyData
        ContextMemory --> MyData
        MCPSetup --> MyData
        Tokens --> MyData
        MCPLogs --> MyData
        
        state Profile {
            note right of Profile: Slide-in panel<br/>(not a page)
        }
        
        MyData --> Profile : profile icon
        Profile --> MyData : close
    }
    
    App_MyData --> App
    App --> Landing : Logout / 401
```

**Routing pattern:** Class-toggle `.page` + `.page.active` (no URL hash)
**Profile** = slide-in panel `.slide-panel` (not a `.page`)

---

**End — 9 diagrams covering: ERD + Upload + Chat + OAuth + MCP + LINE + Stripe + BYOS Sync + Frontend Routing**
