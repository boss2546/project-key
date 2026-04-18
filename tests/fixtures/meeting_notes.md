# บันทึกการประชุม — Sprint Planning #1

**วันที่:** 15 เมษายน 2026
**ผู้เข้าร่วม:** ทีม Dev 5 คน, Product Owner, Scrum Master
**ระยะเวลา:** 2 ชั่วโมง

---

## สรุปการประชุม

### 1. Review Backlog

ทีมได้ทบทวน Product Backlog ที่เตรียมไว้ทั้งหมด 15 items โดยแบ่งเป็น:

- **Must-have (P0):** 5 items
  - Upload file system
  - Text extraction pipeline
  - Database schema setup
  - Basic file listing UI
  - API endpoints สำหรับ upload/list

- **Should-have (P1):** 6 items
  - Organization engine (grouping)
  - Importance scoring
  - Markdown summary generation
  - Organized View UI
  - Delete file functionality
  - File type detection

- **Nice-to-have (P2):** 4 items
  - Drag & drop upload
  - File preview
  - Batch operations
  - Search files

### 2. Sprint 1 Commitment

ทีมตกลงว่า Sprint 1 จะทำ P0 ทั้งหมด 5 items + P1 อีก 2 items:
- Organization engine
- Delete file functionality

**Sprint Duration:** 2 สัปดาห์
**Sprint Goal:** "ผู้ใช้สามารถอัปโหลดไฟล์ได้ และเห็นไฟล์ในระบบ"

### 3. Technical Decisions

- ใช้ FastAPI เป็น backend framework
- ใช้ SQLite สำหรับ MVP (จะย้ายไป Postgres ภายหลัง)
- Frontend เป็น static HTML/CSS/JS ก่อน
- File storage ใช้ local filesystem
- Docling สำหรับ PDF parsing

### 4. Risks ที่ระบุ

1. **Docling installation complexity** — ต้องทดสอบบน Windows ก่อน
2. **LLM API costs** — ต้องตั้ง rate limit
3. **Large file handling** — กำหนด max file size 10MB

### 5. Action Items

| ผู้รับผิดชอบ | Task | Deadline |
|------------|------|----------|
| Dev A | Setup FastAPI project structure | Day 1 |
| Dev B | Database schema + models | Day 2 |
| Dev C | Upload API + file storage | Day 3 |
| Dev D | Text extraction pipeline | Day 4 |
| Dev E | Frontend - file list UI | Day 5 |

### 6. Next Meeting

Sprint Review: 29 เมษายน 2026, 14:00
Daily Standup: ทุกวัน 09:30
