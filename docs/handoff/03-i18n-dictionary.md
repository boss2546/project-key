# 03 — i18n Dictionary (TH/EN Verbatim)

> **Purpose:** Bilingual translation strings ที่ PDB ใช้ใน frontend — copy verbatim จาก `legacy-frontend/app.js:595-1196`
> **Total keys:** TH = 260, EN = 239 (Tool descriptions = Thai-only, 21 keys)
> **Why:** ถ้าไม่มี dict นี้ UI จะแสดง raw key strings (`upload.tray.title`) แทน text จริง
> **Source:** [legacy-frontend/app.js](../../legacy-frontend/app.js)

---

## Schema Pattern

```javascript
const I18N = {
  th: { 'key.subkey': 'Thai text', ... },
  en: { 'key.subkey': 'English text', ... }
};

function t(key, vars) {
  const lang = getLang();  // localStorage.pdb_lang || 'th'
  const tr = I18N[lang]?.[key] || I18N['en']?.[key] || key;
  if (!vars) return tr;
  return tr.replace(/\{(\w+)\}/g, (_, k) => vars[k] != null ? vars[k] : `{${k}}`);
}
```

**Usage:**
- HTML: `<h1 data-i18n="myData.title">My Data</h1>` → `applyLanguage()` swaps textContent
- JS: `t('upload.tray.position', { n: 5 })` → "อันดับ 5" or "Position 5"

---

## TH Dictionary (Verbatim, Order Preserved)

```javascript
{
  'drive.errorBanner.title': 'Google Drive ของคุณหมดอายุการเชื่อมต่อ',
  'drive.errorBanner.detail': 'ไฟล์ใหม่ยังไม่ได้ขึ้น Drive — กดเพื่อเชื่อมต่อใหม่',
  'drive.errorBanner.reconnect': 'เชื่อมต่อใหม่',
  'drive.errorBanner.dismiss': 'ภายหลัง',
  'drive.testingNotice': 'ขณะนี้ระบบเชื่อมต่อ Drive แบบ Beta — การเชื่อมต่อจะหมดอายุทุก 7 วัน · กรุณาเชื่อมต่อใหม่เมื่อแอพแจ้งเตือน',

  // ─── Upload Tray ───
  'upload.queuedToast': 'เพิ่ม {n} ไฟล์เข้าคิว ✓',
  'upload.tray.title': 'คิว Upload',
  'upload.tray.title_n': 'คิว Upload ({n})',
  'upload.tray.minimize': 'ย่อ',
  'upload.tray.queued': 'รอคิว',
  'upload.tray.working': 'กำลังทำ',
  'upload.tray.failed': 'ล้มเหลว',
  'upload.tray.done': 'เสร็จแล้ว',
  'upload.tray.retry': 'ลองใหม่',
  'upload.tray.dismiss': 'ลบออก',
  'upload.tray.cancel': 'ยกเลิก',
  'upload.tray.position': 'อันดับ {n}',
  'upload.tray.position_of': 'อันดับ {n} จาก {total}',
  'upload.tray.elapsed': 'ใช้เวลา {sec} วินาที',
  'upload.tray.elapsed_min': 'ใช้เวลา {min} นาที',
  'upload.tray.summary_queued': '{n} รอคิว',
  'upload.tray.summary_extracting': '{n} กำลังทำ',
  'upload.tray.summary_failed': '{n} ล้มเหลว',
  'upload.tray.system_degraded': 'ระบบประมวลผลล่าช้ากว่าปกติ — เรากำลังตรวจสอบ',
  'upload.tray.system_stopped': 'ระบบประมวลผลหยุด — กรุณาติดต่อแอดมิน',
  'upload.tray.empty_done': 'ทุกไฟล์เสร็จเรียบร้อย',
  'upload.tray.see_details': 'รายละเอียด',
  'upload.tray.stage_queued': 'เข้าคิว',
  'upload.tray.stage_started': 'เริ่มประมวลผล',
  'upload.tray.stage_completed': 'เสร็จ/ผิดพลาด',
  'upload.tray.attempt': 'ครั้งที่ลอง',

  // ─── Auth ───
  'auth.signInWithGoogle': 'เข้าสู่ระบบด้วย Google',
  'auth.signUpWithGoogle': 'สมัครสมาชิกด้วย Google',
  'auth.or': 'หรือ',
  'auth.useGoogleHint': 'บัญชีนี้สมัครด้วย Google',
  'auth.emailNotVerified': 'อีเมล Google ยังไม่ verified',

  // ─── Nav ───
  'nav.myData': 'ข้อมูลของฉัน',
  'nav.knowledge': 'มุมมองความรู้',
  'nav.graph': 'กราฟ',
  'nav.chat': 'AI แชท',
  'nav.profile': 'โปรไฟล์',
  'nav.connectorSection': 'Connector',
  'nav.mcpSetup': 'ตั้งค่า MCP',
  'nav.tokens': 'โทเค็น',
  'nav.mcpLogs': 'บันทึกการใช้งาน',

  // ─── Stats ───
  'stat.files': 'ไฟล์',
  'stat.collections': 'คอลเลกชัน',
  'stat.nodes': 'โหนด',
  'stat.relations': 'ความสัมพันธ์',
  'stat.packs': 'แพ็ก',
  'stat.tokens': 'โทเค็น',

  // ─── My Data Page ───
  'myData.title': 'ข้อมูลของฉัน',
  'myData.subtitle': 'พื้นที่ข้อมูลส่วนตัวของคุณ',
  'myData.organizeAll': 'จัดระเบียบทั้งหมด',
  'myData.organizeNew': 'จัดระเบียบไฟล์ใหม่',
  'myData.uploadText': 'ลากไฟล์มาวาง หรือ คลิกเพื่อเลือกไฟล์',
  'myData.uploadHint': 'รองรับ เอกสาร / รูปภาพ (OCR ไทย) / Spreadsheet / เสียง + วิดีโอ (AI) / Code · 50+ formats · สูงสุด 200 MB · ครั้งละ 20 ไฟล์',
  'myData.allFiles': 'ไฟล์ทั้งหมด',
  'myData.filterAll': 'ทั้งหมด',
  'myData.filterProcessed': 'ประมวลผลแล้ว',
  'myData.filterVault': '📦 คลัง',
  'myData.noFiles': 'ยังไม่มีไฟล์ — เพิ่มไฟล์เข้าพื้นที่ส่วนตัวของคุณ',
  'myData.delete': 'ลบ',

  // ─── Vault ───
  'vault.badge': 'คลัง',
  'vault.toastUpload': 'เก็บใน "คลัง" — AI ค้นหาด้วยชื่อไฟล์ได้ แต่อ่านเนื้อหาไม่ได้',
  'vault.tryAnalyze': 'ลองวิเคราะห์',
  'vault.promoteSuccess': 'วิเคราะห์สำเร็จ — ย้ายไป "ประมวลผลแล้ว"',
  'vault.promoteStillVault': 'ยังวิเคราะห์ไม่ได้ — เก็บในคลังต่อไป',

  // ─── Knowledge Page ───
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

  // ─── Graph Page ───
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

  // ─── Detail Panel ───
  'detail.summary': 'สรุป',
  'detail.metadata': 'Metadata',
  'detail.relations': 'ความสัมพันธ์',
  'detail.showLocal': 'แสดงกราฟเฉพาะจุด',
  'detail.askAi': 'ถาม AI เกี่ยวกับสิ่งนี้',
  'detail.noSummary': 'ไม่มีสรุป',

  // ─── Chat Page ───
  'chat.title': 'AI แชท',
  'chat.subtitle': 'AI ใช้ข้อมูล ความสัมพันธ์ และบริบทของคุณในการตอบ',
  'chat.welcome': 'สวัสดี! ถามอะไรก็ได้เกี่ยวกับข้อมูลของคุณ',
  'chat.welcomeSub': 'AI จะใช้ Profile, Context Packs, Files, และ Knowledge Graph ในการตอบ',
  'chat.placeholder': 'ถามเกี่ยวกับข้อมูลของคุณ...',
  'chat.profileNotSet': 'ยังไม่ตั้งค่า',
  'chat.profileActive': 'เปิดใช้งาน',
  'chat.thinking': 'AI กำลังคิด...',

  // ─── Sources Panel ───
  'sources.title': 'หลักฐานที่ใช้',
  'sources.profile': ' โปรไฟล์',
  'sources.packs': ' Context Packs',
  'sources.files': ' ไฟล์ที่ใช้',
  'sources.graph': ' Nodes & Edges',
  'sources.reasoning': ' เหตุผลในการเลือก',
  'sources.evidence': ' Evidence Graph',

  // ─── Profile Panel ───
  'profile.title': ' โปรไฟล์ของฉัน',
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

  // ─── Personality Panel ───
  'personality.title': 'บุคลิกภาพ',
  'personality.optional': '(ไม่บังคับ)',
  'personality.pdpa': ' ลิงก์ "ทำที่..." จะพาคุณไปยังเว็บไซต์ภายนอก — โปรดดูนโยบายความเป็นส่วนตัวของเว็บนั้นๆ',
  'personality.history': 'ประวัติ',
  'personality.viewHistory': 'ดูประวัติการอัปเดต',
  'personality.notSet': 'ไม่ระบุ',
  'personality.mbti.type': 'ประเภท',
  'personality.mbti.identity': 'Identity',
  'personality.mbti.identityHint': 'สำหรับ NERIS เท่านั้น',
  'personality.mbti.source': 'ที่มาของผล',
  'personality.mbti.selfReport': 'ฉันเดาเอง',
  'personality.enneagram.core': 'Core',
  'personality.enneagram.wing': 'Wing',
  'personality.enneagram.wingHint': 'เลือก Core ก่อน',

  // ─── Confirm Modal ───
  'confirm.cancel': 'ยกเลิก',
  'confirm.ok': 'ยืนยัน',

  // ─── Upload Result Modal ───
  'upload.resultTitle': 'ผลการอัปโหลด',
  'upload.successCount': 'อัปโหลดสำเร็จ {count} ไฟล์',
  'upload.skippedCount': 'ข้าม {count} ไฟล์',
  'upload.understand': 'เข้าใจแล้ว',
  'upload.skipUnsupported': 'ไฟล์ไม่รองรับ',
  'upload.skipTooLarge': 'ไฟล์ใหญ่เกิน',
  'upload.skipQuota': 'เกินจำนวนที่เก็บได้',
  'upload.skipEmpty': 'ไฟล์ว่างเปล่า',
  'upload.suggestionLabel': 'คำแนะนำ',
  'upload.batchTooManyTitle': 'อัปครั้งเดียว {count} ไฟล์ — เกินที่แนะนำ',
  'upload.batchRiskyMsg': 'ระบบรองรับครั้งละ 20 ไฟล์ ที่จำนวนนี้อาจช้าหรือ timeout — แบ่งเป็นรอบย่อยจะเสถียรกว่า',
  'upload.batchHardMsg': 'ระบบไม่รองรับการอัปเกิน 50 ไฟล์ในครั้งเดียว — กรุณาแบ่งเป็นรอบย่อย ครั้งละไม่เกิน 20 ไฟล์',
  'upload.batchProceedRisky': 'ดำเนินการต่อ (เสี่ยง)',
  'upload.batchSplit': 'ยกเลิก แบ่งเป็นรอบย่อย',

  // ─── Toasts ───
  'toast.uploaded': 'อัปโหลดเรียบร้อย',
  'toast.deleted': 'ลบเรียบร้อย',
  'toast.deletedCleaningDrive': 'ลบเรียบร้อย · กำลังเคลียร์ Google Drive',
  'toast.deletedDrivePicked': 'ลบจากระบบแล้ว · ไฟล์ต้นฉบับใน Drive ของคุณยังอยู่',
  'toast.profileSaved': 'บันทึกโปรไฟล์เรียบร้อย',
  'toast.organized': 'จัดระเบียบเรียบร้อย',
  'toast.organizedNew': 'จัดระเบียบไฟล์ใหม่เรียบร้อย',
  'toast.noNewFiles': 'ไม่มีไฟล์ใหม่ที่ต้องจัดระเบียบ',
  'toast.graphBuilt': 'สร้างกราฟเรียบร้อย',
  'toast.error': 'เกิดข้อผิดพลาด',
  'toast.tokenGenerated': 'สร้าง Token เรียบร้อย',
  'toast.tokenRevoked': 'ยกเลิก Token เรียบร้อย',
  'toast.copied': 'คัดลอกแล้ว',
  'toast.testSuccess': 'เชื่อมต่อสำเร็จ!',
  'toast.testFailed': 'เชื่อมต่อล้มเหลว',

  // ─── LINE Bot ───
  'line.title': 'LINE Bot',
  'line.desc': 'เข้าถึง PDB ผ่าน LINE — อัปโหลดไฟล์ ถาม AI ค้นข้อมูลจากมือถือ',
  'line.connect': 'เชื่อม LINE',
  'line.disconnect': 'เลิกเชื่อม',
  'line.openChat': 'เปิดใน LINE',
  'line.notConfigured': 'ระบบ LINE bot ยังไม่ถูกตั้งค่าบนเซิร์ฟเวอร์',
  'line.notLinked': 'ยังไม่เชื่อม',
  'line.displayName': 'ชื่อ LINE:',
  'line.linkedAt': 'เชื่อมเมื่อ:',
  'line.lastSeen': 'ใช้งานล่าสุด:',

  // ─── MCP Setup Page ───
  'mcp.setupTitle': 'ตั้งค่าตัวเชื่อมต่อ Claude',
  'mcp.setupSubtitle': 'เชื่อมต่อข้อมูล Personal Data Bank ของคุณไปยัง Claude ผ่าน Remote MCP',
  'mcp.notConfigured': 'ยังไม่ได้ตั้งค่า',
  'mcp.configured': 'เชื่อมต่อแล้ว',
  'mcp.noActiveToken': 'ยังไม่มี Token ที่เปิดใช้งาน',
  'mcp.step1Title': 'Connector URL (มี Key ในตัว)',
  'mcp.step1Desc': 'คัดลอก URL นี้ไปวางใน Claude — URL มี Secret Key ฝังอยู่แล้ว',
  'mcp.step2Title': 'สร้าง Access Token',
  'mcp.step2Desc': 'สร้าง Bearer token สำหรับ REST API',
  'mcp.step3Title': 'ตั้งค่าใน AI Client',
  'mcp.step3Desc': 'เลือกแพลตฟอร์มแล้วคัดลอก config',
  'mcp.antigravityDesc': 'เพิ่มในไฟล์ mcp_config.json (ใช้ mcp-remote bridge)',
  'mcp.step4Title': 'ทดสอบการเชื่อมต่อ',
  'mcp.step4Desc': 'ตรวจสอบว่า connector ทำงานถูกต้อง',
  'mcp.generateToken': 'สร้าง Token',
  'mcp.tokenWarning': 'บันทึก token นี้ตอนนี้ — จะไม่แสดงอีกครั้ง',
  'mcp.testConnection': 'ทดสอบการเชื่อมต่อ',
  'mcp.availableTools': 'เครื่องมือทั้งหมด',
  'mcp.scope': 'อ่าน+เขียน',
  'mcp.toolEnabled': 'เปิดใช้งาน',
  'mcp.toolDisabled': 'ปิดใช้งาน',

  // ─── MCP Tool Descriptions (TH only — 21 keys) ───
  'tool.get_profile': 'ดูโปรไฟล์ผู้ใช้ รวมถึงตัวตน เป้าหมาย สไตล์การทำงาน และความชอบ',
  'tool.list_files': 'แสดงรายการไฟล์ทั้งหมดในฐานความรู้ พร้อมข้อมูล แท็ก และสรุปย่อ',
  'tool.get_file_content': 'ดูเนื้อหาข้อความของไฟล์ (สูงสุด 5000 ตัวอักษร)',
  'tool.get_file_summary': 'ดูสรุปที่ AI สร้าง หัวข้อหลัก และข้อเท็จจริงสำคัญของไฟล์',
  'tool.list_collections': 'แสดงคอลเลกชันที่ AI จัดกลุ่ม พร้อมไฟล์และสรุป',
  'tool.list_context_packs': 'แสดงรายการ Context Pack (กลุ่มความรู้ที่สกัดแล้ว)',
  'tool.get_context_pack': 'ดู Context Pack ตาม ID พร้อมเนื้อหาทั้งหมด',
  'tool.search_knowledge': 'ค้นหาฐานความรู้แบบ Semantic + Keyword ผสม ได้ไฟล์ แพ็ก และโหนดกราฟ',
  'tool.explore_graph': 'สำรวจกราฟความรู้ ดูภาพรวมโหนดทั้งหมด หรือดูความเชื่อมโยงของโหนดเฉพาะ',
  'tool.get_overview': 'ดูภาพรวมระบบ จำนวนไฟล์ คอลเลกชัน แพ็ก โหนด และเส้นเชื่อม',
  'tool.create_context_pack': 'สร้าง Context Pack ใหม่จากไฟล์ที่เลือก ประเภท: profile, study, work, project',
  'tool.add_note': 'อัพเดทสรุปของไฟล์ ใช้เพิ่มโน้ตหรือปรับปรุงสรุปที่ AI สร้าง',
  'tool.update_file_tags': 'อัพเดทแท็กของไฟล์ ใช้จัดระเบียบและจำแนกหมวดหมู่',
  'tool.upload_text': 'อัพโหลดข้อความเป็นไฟล์ใหม่ (Claude สามารถสร้างไฟล์ความรู้ได้)',
  'tool.update_profile': 'อัพเดทโปรไฟล์ผู้ใช้ (ตัวตน เป้าหมาย สไตล์ ความชอบ)',
  'tool.delete_file': 'ลบไฟล์และข้อมูลที่เกี่ยวข้องทั้งหมด (สรุป ข้อมูลเชิงลึก คลัสเตอร์)',
  'tool.delete_pack': 'ลบ Context Pack',
  'tool.run_organize': 'รันไปป์ไลน์ AI แบบเต็ม: สรุป จัดกลุ่ม สร้างกราฟ',
  'tool.build_graph': 'สร้างกราฟความรู้ใหม่จากข้อมูลทั้งหมด',
  'tool.enrich_metadata': 'รัน AI เสริมข้อมูลเมตา (แท็ก ความละเอียดอ่อน ความสด)',
  'tool.admin_login': 'ยืนยันรหัสผ่านแอดมิน เพื่อเข้าถึงเครื่องมือที่ปิดอยู่',

  // ─── Tokens Page ───
  'tokens.title': 'จัดการ Token',
  'tokens.subtitle': 'จัดการ access tokens สำหรับ AI connectors ภายนอก',
  'tokens.newToken': 'สร้าง Token ใหม่',
  'tokens.empty': 'ยังไม่มี token — สร้างได้จากหน้า MCP Setup',
  'tokens.revoke': 'ยกเลิก',
  'tokens.active': 'ใช้งาน',
  'tokens.revoked': 'ยกเลิกแล้ว',
  'tokens.created': 'สร้างเมื่อ',
  'tokens.lastUsed': 'ใช้ล่าสุด',
  'tokens.never': 'ยังไม่เคยใช้',
  'tokens.confirmRevoke': 'ต้องการยกเลิก token นี้?',

  // ─── MCP Logs Page ───
  'logs.title': 'บันทึก MCP',
  'logs.subtitle': 'ติดตามการใช้งาน connector และแก้ไขปัญหา',
  'logs.allTools': 'ทุกเครื่องมือ',
  'logs.allStatus': 'ทุกสถานะ',
  'logs.refresh': 'รีเฟรช',
  'logs.colTime': 'เวลา',
  'logs.colTool': 'เครื่องมือ',
  'logs.colStatus': 'สถานะ',
  'logs.colLatency': 'เวลาตอบ',
  'logs.colDetails': 'รายละเอียด',
  'logs.empty': 'ยังไม่มีบันทึก — การใช้งาน connector จะแสดงที่นี่',

  // ─── Duplicate Detection Modal ───
  'dup.title': 'พบไฟล์คล้ายกัน {count} ไฟล์',
  'dup.subtitle': 'ไฟล์ที่อัปโหลดใหม่บางไฟล์มีเนื้อหาคล้ายกับไฟล์ที่มีอยู่แล้ว — เลือกทีละไฟล์ว่าจะเก็บหรือข้าม',
  'dup.labelNew': '(ใหม่)',
  'dup.labelSimilar': 'คล้าย',
  'dup.labelExact': '(ตรงเป๊ะ)',
  'dup.labelMatched': 'ตรงกัน',
  'dup.actionKeep': 'เก็บทั้งคู่',
  'dup.actionSkip': 'ข้ามไฟล์ใหม่',
  'dup.quickKeep': 'เก็บทั้งหมด',
  'dup.quickSkip': 'ข้ามทั้งหมด',
  'dup.cancel': 'ไว้ทีหลัง',
  'dup.confirmKeepAll': 'เก็บทั้งหมด',
  'dup.confirmSkip': 'ข้ามไฟล์ใหม่ {count} ไฟล์',
  'dup.undoTitle': 'จะข้ามไฟล์ใหม่ {count} ไฟล์ใน 10 วิ',
  'dup.undoBtn': 'เลิกทำ',
  'dup.undoNow': 'ข้ามทันที',
  'dup.toastKeptAll': 'เก็บไฟล์ทั้งหมดแล้ว',
  'dup.toastUndone': 'ยกเลิกการข้าม — ไฟล์ทั้งหมดยังอยู่',
  'dup.toastSkipped': 'ข้ามไฟล์ที่ซ้ำ {count} ไฟล์แล้ว',
  'dup.toastError': 'ไม่สามารถข้ามไฟล์ได้ ลองใหม่อีกครั้ง',
}
```

---

## EN Dictionary (Verbatim, Order Preserved)

```javascript
{
  // ─── Drive Error Banner ───
  'drive.errorBanner.title': 'Google Drive connection expired',
  'drive.errorBanner.detail': "New files haven't been uploaded to Drive — click to reconnect",
  'drive.errorBanner.reconnect': 'Reconnect',
  'drive.errorBanner.dismiss': 'Later',
  'drive.testingNotice': 'Drive connection is in Beta mode — expires every 7 days · please reconnect when prompted',

  // ─── Upload Tray ───
  'upload.queuedToast': '{n} files queued ✓',
  'upload.tray.title': 'Upload Queue',
  'upload.tray.title_n': 'Upload Queue ({n})',
  'upload.tray.minimize': 'Minimize',
  'upload.tray.queued': 'Queued',
  'upload.tray.working': 'Working',
  'upload.tray.failed': 'Failed',
  'upload.tray.done': 'Done',
  'upload.tray.retry': 'Retry',
  'upload.tray.dismiss': 'Dismiss',
  'upload.tray.cancel': 'Cancel',
  'upload.tray.position': 'Position {n}',
  'upload.tray.position_of': 'Position {n} of {total}',
  'upload.tray.elapsed': 'Elapsed {sec}s',
  'upload.tray.elapsed_min': 'Elapsed {min} min',
  'upload.tray.summary_queued': '{n} queued',
  'upload.tray.summary_extracting': '{n} working',
  'upload.tray.summary_failed': '{n} failed',
  'upload.tray.system_degraded': 'Processing slower than usual — investigating',
  'upload.tray.system_stopped': 'Processing system stopped — please contact admin',
  'upload.tray.empty_done': 'All files done',
  'upload.tray.see_details': 'Details',
  'upload.tray.stage_queued': 'Queued',
  'upload.tray.stage_started': 'Started',
  'upload.tray.stage_completed': 'Completed',
  'upload.tray.attempt': 'Attempt',

  // ─── Auth ───
  'auth.signInWithGoogle': 'Sign in with Google',
  'auth.signUpWithGoogle': 'Sign up with Google',
  'auth.or': 'OR',
  'auth.useGoogleHint': 'This account uses Google sign-in',
  'auth.emailNotVerified': 'Google email is not verified',

  // ─── Nav ───
  'nav.myData': 'My Data',
  'nav.knowledge': 'Knowledge View',
  'nav.graph': 'Graph',
  'nav.chat': 'AI Chat',
  'nav.profile': 'My Profile',
  'nav.connectorSection': 'Connector',
  'nav.mcpSetup': 'MCP Setup',
  'nav.tokens': 'Tokens',
  'nav.mcpLogs': 'MCP Logs',

  // ─── Stats ───
  'stat.files': 'Files',
  'stat.collections': 'Collections',
  'stat.nodes': 'Nodes',
  'stat.relations': 'Relations',
  'stat.packs': 'Packs',
  'stat.tokens': 'Tokens',

  // ─── My Data Page ───
  'myData.title': 'My Data',
  'myData.subtitle': 'Your personal data space',
  'myData.organizeAll': 'Organize All',
  'myData.organizeNew': 'Organize New Files',
  'myData.uploadText': 'Drag files here or click to select',
  'myData.uploadHint': 'Supports docs / images (OCR) / spreadsheets / audio + video (AI) / code · 50+ formats · max 200 MB · up to 20 files at once',
  'myData.allFiles': 'All Files',
  'myData.filterAll': 'All',
  'myData.filterProcessed': 'Processed',
  'myData.filterVault': '📦 Vault',
  'myData.noFiles': 'No files yet — add files to your personal space',
  'myData.delete': 'Delete',

  // ─── Vault ───
  'vault.badge': 'Vault',
  'vault.toastUpload': 'Stored in "Vault" — AI can search by filename but cannot read content',
  'vault.tryAnalyze': 'Try analyze',
  'vault.promoteSuccess': 'Analyzed successfully — moved to Processed',
  'vault.promoteStillVault': 'Cannot analyze yet — kept in vault',

  // ─── Knowledge Page ───
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

  // ─── Graph Page ───
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

  // ─── Detail Panel ───
  'detail.summary': 'Summary',
  'detail.metadata': 'Metadata',
  'detail.relations': 'Relations',
  'detail.showLocal': 'Show Local Graph',
  'detail.askAi': 'Ask AI about this',
  'detail.noSummary': 'No summary',

  // ─── Chat Page ───
  'chat.title': 'AI Chat',
  'chat.subtitle': 'AI uses your data, relations, and context to respond',
  'chat.welcome': 'Hi! Ask anything about your data',
  'chat.welcomeSub': 'AI uses Profile, Context Packs, Files, and Knowledge Graph to answer',
  'chat.placeholder': 'Ask about your data...',
  'chat.profileNotSet': 'Not set',
  'chat.profileActive': 'Active',
  'chat.thinking': 'AI is thinking...',

  // ─── Sources Panel ───
  'sources.title': 'Evidence Used',
  'sources.profile': ' Profile',
  'sources.packs': ' Context Packs',
  'sources.files': ' Files Used',
  'sources.graph': ' Nodes & Edges',
  'sources.reasoning': ' Reasoning',
  'sources.evidence': ' Evidence Graph',

  // ─── Profile Panel ───
  'profile.title': ' My Profile',
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

  // ─── Personality Panel ───
  'personality.title': 'Personality',
  'personality.optional': '(optional)',
  'personality.pdpa': ' "Take it at..." links will open external sites — please review their privacy policies.',
  'personality.history': 'History',
  'personality.viewHistory': 'View update history',
  'personality.notSet': 'Not set',
  'personality.mbti.type': 'Type',
  'personality.mbti.identity': 'Identity',
  'personality.mbti.identityHint': 'NERIS only',
  'personality.mbti.source': 'Source',
  'personality.mbti.selfReport': 'Self-report',
  'personality.enneagram.core': 'Core',
  'personality.enneagram.wing': 'Wing',
  'personality.enneagram.wingHint': 'Pick Core first',

  // ─── Confirm Modal ───
  'confirm.cancel': 'Cancel',
  'confirm.ok': 'Confirm',

  // ─── Upload Result Modal ───
  'upload.resultTitle': 'Upload Result',
  'upload.successCount': '{count} file(s) uploaded',
  'upload.skippedCount': '{count} file(s) skipped',
  'upload.understand': 'Got it',
  'upload.skipUnsupported': 'Unsupported file',
  'upload.skipTooLarge': 'File too large',
  'upload.skipQuota': 'Quota exceeded',
  'upload.skipEmpty': 'Empty file',
  'upload.suggestionLabel': 'Suggestion',
  'upload.batchTooManyTitle': 'Uploading {count} files at once — over recommended limit',
  'upload.batchRiskyMsg': 'System recommends max 20 files per batch. Larger batches may be slow or time out — splitting into smaller batches is more reliable.',
  'upload.batchHardMsg': 'System does not support uploading more than 50 files at once — please split into smaller batches of up to 20 files.',
  'upload.batchProceedRisky': 'Proceed anyway (risky)',
  'upload.batchSplit': 'Cancel & split',

  // ─── Toasts ───
  'toast.uploaded': 'Upload complete',
  'toast.deleted': 'Deleted successfully',
  'toast.deletedCleaningDrive': 'Deleted · cleaning Google Drive',
  'toast.deletedDrivePicked': 'Removed from system · original Drive file preserved',
  'toast.profileSaved': 'Profile saved',
  'toast.organized': 'Organization complete',
  'toast.organizedNew': 'New files organized',
  'toast.noNewFiles': 'No new files to organize',
  'toast.graphBuilt': 'Graph built successfully',
  'toast.error': 'An error occurred',
  'toast.tokenGenerated': 'Token generated successfully',
  'toast.tokenRevoked': 'Token revoked',
  'toast.copied': 'Copied to clipboard',
  'toast.testSuccess': 'Connection successful!',
  'toast.testFailed': 'Connection failed',

  // ─── LINE Bot ───
  'line.title': 'LINE Bot',
  'line.desc': 'Access PDB through LINE — upload files, ask AI, search knowledge from your phone',
  'line.connect': 'Connect LINE',
  'line.disconnect': 'Disconnect',
  'line.openChat': 'Open in LINE',
  'line.notConfigured': 'LINE bot is not configured on this server yet.',
  'line.notLinked': 'Not linked',
  'line.displayName': 'LINE name:',
  'line.linkedAt': 'Linked:',
  'line.lastSeen': 'Last seen:',

  // ─── MCP Setup Page ───
  'mcp.setupTitle': 'Claude Connector Setup',
  'mcp.setupSubtitle': 'Connect your Personal Data Bank data to Claude via remote MCP',
  'mcp.notConfigured': 'Not configured',
  'mcp.configured': 'Connected',
  'mcp.noActiveToken': 'No active token',
  'mcp.step1Title': 'Connector URL (Key included)',
  'mcp.step1Desc': 'Copy this URL to Claude — it contains your Secret Key',
  'mcp.step2Title': 'Generate Access Token',
  'mcp.step2Desc': 'Create a Bearer token for REST API access',
  'mcp.step3Title': 'Configure AI Client',
  'mcp.step3Desc': 'Choose your platform and copy the config',
  'mcp.antigravityDesc': 'Add to mcp_config.json (uses mcp-remote bridge)',
  'mcp.step4Title': 'Test Connection',
  'mcp.step4Desc': 'Verify your connector setup is working',
  'mcp.generateToken': 'Generate Token',
  'mcp.tokenWarning': "Save this token now — it won't be shown again",
  'mcp.testConnection': 'Test Connection',
  'mcp.availableTools': 'Available Tools',
  'mcp.scope': 'read+write',
  'mcp.toolEnabled': 'Enabled',
  'mcp.toolDisabled': 'Disabled',

  // ⚠️ Note: 21 'tool.*' keys are TH-only in source — EN dict skips them

  // ─── Tokens Page ───
  'tokens.title': 'Token Management',
  'tokens.subtitle': 'Manage access tokens for external AI connectors',
  'tokens.newToken': 'New Token',
  'tokens.empty': 'No tokens yet — generate one from MCP Setup',
  'tokens.revoke': 'Revoke',
  'tokens.active': 'Active',
  'tokens.revoked': 'Revoked',
  'tokens.created': 'Created',
  'tokens.lastUsed': 'Last used',
  'tokens.never': 'Never used',
  'tokens.confirmRevoke': 'Revoke this token?',

  // ─── MCP Logs Page ───
  'logs.title': 'MCP Logs',
  'logs.subtitle': 'Track connector tool usage and debug issues',
  'logs.allTools': 'All Tools',
  'logs.allStatus': 'All Status',
  'logs.refresh': 'Refresh',
  'logs.colTime': 'Time',
  'logs.colTool': 'Tool',
  'logs.colStatus': 'Status',
  'logs.colLatency': 'Latency',
  'logs.colDetails': 'Details',
  'logs.empty': 'No logs yet — connector usage will appear here',

  // ─── Duplicate Detection Modal ───
  'dup.title': 'Found {count} similar files',
  'dup.subtitle': 'Some uploaded files are similar to existing ones — choose per file what to do',
  'dup.labelNew': '(new)',
  'dup.labelSimilar': 'similar to',
  'dup.labelExact': '(exact)',
  'dup.labelMatched': 'matched',
  'dup.actionKeep': 'Keep both',
  'dup.actionSkip': 'Skip new',
  'dup.quickKeep': 'Keep all',
  'dup.quickSkip': 'Skip all',
  'dup.cancel': 'Later',
  'dup.confirmKeepAll': 'Keep all',
  'dup.confirmSkip': 'Skip {count} new files',
  'dup.undoTitle': 'Skipping {count} new files in 10s',
  'dup.undoBtn': 'Undo',
  'dup.undoNow': 'Skip now',
  'dup.toastKeptAll': 'All files kept',
  'dup.toastUndone': 'Cancelled — all files kept',
  'dup.toastSkipped': 'Skipped {count} duplicate files',
  'dup.toastError': 'Failed to skip — try again',
}
```

---

## Variable Substitution Patterns

Keys ที่ใช้ `{placeholder}` syntax:

| Key | TH | EN |
|---|---|---|
| `upload.queuedToast` | `เพิ่ม {n} ไฟล์เข้าคิว ✓` | `{n} files queued ✓` |
| `upload.tray.title_n` | `คิว Upload ({n})` | `Upload Queue ({n})` |
| `upload.tray.position` | `อันดับ {n}` | `Position {n}` |
| `upload.tray.position_of` | `อันดับ {n} จาก {total}` | `Position {n} of {total}` |
| `upload.tray.elapsed` | `ใช้เวลา {sec} วินาที` | `Elapsed {sec}s` |
| `upload.tray.elapsed_min` | `ใช้เวลา {min} นาที` | `Elapsed {min} min` |
| `upload.tray.summary_queued` | `{n} รอคิว` | `{n} queued` |
| `upload.tray.summary_extracting` | `{n} กำลังทำ` | `{n} working` |
| `upload.tray.summary_failed` | `{n} ล้มเหลว` | `{n} failed` |
| `upload.successCount` | `อัปโหลดสำเร็จ {count} ไฟล์` | `{count} file(s) uploaded` |
| `upload.skippedCount` | `ข้าม {count} ไฟล์` | `{count} file(s) skipped` |
| `upload.batchTooManyTitle` | `อัปครั้งเดียว {count} ไฟล์ — เกินที่แนะนำ` | `Uploading {count} files at once — over recommended limit` |
| `dup.title` | `พบไฟล์คล้ายกัน {count} ไฟล์` | `Found {count} similar files` |
| `dup.confirmSkip` | `ข้ามไฟล์ใหม่ {count} ไฟล์` | `Skip {count} new files` |
| `dup.undoTitle` | `จะข้ามไฟล์ใหม่ {count} ไฟล์ใน 10 วิ` | `Skipping {count} new files in 10s` |
| `dup.toastSkipped` | `ข้ามไฟล์ที่ซ้ำ {count} ไฟล์แล้ว` | `Skipped {count} duplicate files` |

**Substitution rule:** `t(key, vars)` replaces `{name}` with `vars.name` value; falls back to literal `{name}` if missing.

---

## Backend Step Translation (localizeBackendStep)

Backend ส่ง `progress_step` string เป็นไทยเสมอ ([upload_worker.py](../../backend/upload_worker.py)) — frontend แปลด้วย regex array:

```javascript
// legacy-frontend/app.js:1791-1806
const STEP_TRANSLATIONS_EN = [
  [/^อันดับที่ (\d+) — กำลังรอคิว$/, (m) => `Queue position ${m[1]}`],
  [/^กำลังประมวลผล$/, () => 'Processing'],
  [/^เตรียมประมวลผล$/, () => 'Preparing'],
  [/^อัปโหลด(วิดีโอ|รูป)?ไป Gemini( Files API)?$/, () => 'Uploading to Gemini'],
  [/^Gemini เตรียมไฟล์ \(([A-Z_]+), (\d+)s\)$/, (m) => `Gemini preparing (${m[1]}, ${m[2]}s)`],
  [/^Gemini ถอดเสียง( \(.+\))?$/, () => 'Gemini transcribing'],
  [/^Gemini วิเคราะห์(วิดีโอ|รูป)( \(.+\))?$/, () => 'Gemini analyzing'],
  [/^รับผลลัพธ์จาก Gemini$/, () => 'Receiving from Gemini'],
  [/^บันทึกผลลัพธ์$/, () => 'Saving result'],
  [/^เปิดรูปภาพ$/, () => 'Opening image'],
  [/^OCR รูปภาพ$/, () => 'OCR image'],
  [/^ประมวลผลข้อความ Thai$/, () => 'Post-processing Thai text'],
  [/^ตรวจไฟล์ PDF$/, () => 'Inspecting PDF'],
  [/^กำลังอ่านข้อความในไฟล์$/, () => 'Reading file content'],
];

function localizeBackendStep(step) {
  if (getLang() !== 'en' || !step) return step;
  for (const [pattern, formatter] of STEP_TRANSLATIONS_EN) {
    const match = step.match(pattern);
    if (match) return formatter(match);
  }
  return step;  // fallback: show raw Thai if no pattern matched
}
```

---

## applyLanguage(lang) Function

`legacy-frontend/app.js:1215-1260`

หน้าที่:
1. เก็บ `localStorage.pdb_lang = lang`
2. ตั้ง `document.documentElement.lang = lang`
3. Update ทุก element ที่มี `data-i18n` attribute → `el.textContent = t(el.dataset.i18n)`
4. Update placeholders ของ inputs:
   - `#graph-search-input` → `graph.searchPlaceholder`
   - `#chat-input` → `chat.placeholder`
   - Profile form: identity / goals / style / output / background placeholders
5. Update language toggle button labels (TH/EN)
6. Re-render dynamic content (ternary-based HTML):
   - `renderStorageModeUI()`
   - `renderDriveErrorBanner()`
   - `loadLineStatus()` (LINE badge + notice)

---

**End — All i18n strings verbatim from PDB v9.4.8 ([legacy-frontend/app.js:595-1196](../../legacy-frontend/app.js))**
