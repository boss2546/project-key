# 📡 API Specification

> Source of truth สำหรับ API contracts ระหว่าง frontend ↔ backend
> **เปลี่ยน API → update ไฟล์นี้ก่อนเขียนโค้ดเสมอ**

---

## Base URL
- Local: `http://localhost:8000`
- Production: `https://project-key.fly.dev`
- API prefix: `/api`

## Authentication
- Header: `Authorization: Bearer <jwt_token>`
- Token ได้จาก POST `/api/auth/login`
- Endpoint ที่ต้อง auth: ทุกตัวยกเว้น `/api/auth/*` และ public pages

## Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE_UPPER_SNAKE",
    "message": "ข้อความภาษาไทยสำหรับผู้ใช้"
  }
}
```

---

## Endpoints

> ⚠️ **หมายเหตุ:** ส่วนนี้เป็น template — agents ต้อง verify endpoints จริงโดยอ่าน `backend/main.py`
> เมื่อเพิ่ม / แก้ / ลบ endpoint → update ไฟล์นี้ทันที

### 🔐 Auth
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register` | สมัครสมาชิก | ❌ |
| POST | `/api/auth/login` | เข้าสู่ระบบ | ❌ |
| POST | `/api/auth/logout` | ออกจากระบบ | ✅ |
| GET  | `/api/auth/me` | ดู profile ตัวเอง | ✅ |

### 📁 Files / Data
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/upload` | Upload file | ✅ |
| GET  | `/api/files` | List files | ✅ |
| GET  | `/api/files/{id}` | ดูรายละเอียดไฟล์ | ✅ |
| DELETE | `/api/files/{id}` | ลบไฟล์ | ✅ |

### 🤖 AI / Organize
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/organize` | จัดระเบียบด้วย AI | ✅ |
| GET  | `/api/collections` | ดู collections | ✅ |
| GET  | `/api/graph` | ดู knowledge graph | ✅ |

### 👤 Profile / Personality (v6.0)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET  | `/api/profile` | get profile + 4 personality systems | ✅ |
| PUT  | `/api/profile` | partial update (`exclude_unset` — null = clear) | ✅ |
| GET  | `/api/personality/reference` | reference data for 4 systems + test links | ❌ public |
| GET  | `/api/profile/personality/history` | append-only history (filter `?system=`, `?limit=` ≤200) | ✅ |

PUT /api/profile body adds 4 optional fields (Pydantic v2):
- `mbti`: `{"type": "INTJ" | "INTJ-A" | "INTJ-T", "source": "official"|"neris"|"self_report"} | null`
- `enneagram`: `{"core": 1-9, "wing": int|null}` (wing must be ±1 of core, wrap-around 9↔1)
- `clifton_top5`: `list[str]` (1-5 items, ห้ามซ้ำ, must match 34 canonical themes)
- `via_top5`: `list[str]` (1-5 items, ห้ามซ้ำ, must match 24 canonical strengths)

Pydantic raises 422 for invalid type/source/core/wing. Service raises 400 for INVALID_CLIFTON_THEME / INVALID_VIA_STRENGTH / DUPLICATE_THEMES.

### 💳 Billing (Stripe)
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/billing/checkout` | สร้าง Stripe Checkout session | ✅ |
| POST | `/api/billing/webhook` | Stripe webhook (signed) | ❌ |
| GET  | `/api/billing/subscription` | ดู subscription ปัจจุบัน | ✅ |

### 🔌 MCP
| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/mcp/tools/list` | List tools | MCP Token |
| POST | `/api/mcp/tools/call` | Execute tool | MCP Token |

---

## Common Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `UNAUTHORIZED` | 401 | ไม่ได้ login / token หมดอายุ |
| `FORBIDDEN` | 403 | login แล้วแต่ไม่มีสิทธิ์ |
| `NOT_FOUND` | 404 | ไม่พบ resource |
| `VALIDATION_ERROR` | 400 | input ไม่ถูกต้อง |
| `PLAN_LIMIT_EXCEEDED` | 403 | เกิน limit ของ plan |
| `LOCKED_DATA` | 423 | ข้อมูลถูก lock (v5.9.3) |
| `INTERNAL_ERROR` | 500 | server error |
| `STRIPE_ERROR` | 502 | Stripe API error |

---

## วิธี update ไฟล์นี้

เมื่อ agent เพิ่ม / แก้ / ลบ endpoint:

1. แก้ table ด้านบนให้สะท้อนความจริง
2. ถ้า request/response complex → สร้าง section แยกด้านล่างพร้อม example
3. Commit พร้อม code change ใน commit เดียวกัน
4. แจ้ง agent อื่นผ่าน `/communication/from-[ชื่อคุณ].md`
