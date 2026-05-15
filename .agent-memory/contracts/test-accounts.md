# 🧪 Test Accounts — สำหรับทดสอบบน Local Dev

> ⚠️ **ใช้สำหรับ local dev เท่านั้น** (http://127.0.0.1:8000)
> ห้ามใช้บน production · ห้าม commit credentials เข้า source code
> ทุก agent ใช้ account เหล่านี้ในการทดสอบ

---

## 👑 Admin Account

| วิธี Login | ข้อมูล |
|---|---|
| **Google Sign-In** | `bossok25462546@gmail.com` |
| **Email/Password** | Email: `bossok2546@gmail.com` · Password: `0898661896za` |

- มีสิทธิ์ admin ทั้งหมด (จัดการ users, ดู billing, upload ไม่จำกัด)
- ใช้ทดสอบ: admin panel, BYOS Drive, plan limits (admin tier)

---

## 👤 Regular User Account

| วิธี Login | ข้อมูล |
|---|---|
| **Email/Password** | Email: `test1@gmail.com` · Password: `0898661896za` |

- เป็น Free tier user
- ใช้ทดสอบ: upload limits, plan restrictions, multi-user scenarios

---

## 📋 วิธีใช้

1. **เทส Happy Path** → login ด้วย admin account
2. **เทส Plan Limits** → login ด้วย regular user (Free tier)
3. **เทส Multi-tenant** → login ทั้ง 2 accounts สลับกัน
4. **เทส Google OAuth** → ใช้ Google Sign-In ของ admin account
5. **เทส Auth Errors** → ส่ง request โดยไม่ login / ใช้ token หมดอายุ

## 🔒 Security Notes

- Password เหมือนกันทั้ง 2 accounts — ตั้งใจให้จำง่ายสำหรับ dev
- ถ้าจะ test production → ต้องถาม user ก่อน (อาจใช้ account อื่น)
- ห้าม hardcode credentials ใน test scripts — อ้างอิงไฟล์นี้แทน
