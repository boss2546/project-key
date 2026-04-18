# บันทึกประชุม - ทีม NOVA Sprint Review

## วันที่: 15 มีนาคม 2026
## ผู้เข้าร่วม: ดร.สมชาย, วิภา, พัฒน์, เซิร์ฟ, ดีไซน์

## สรุปความก้าวหน้า

### Sprint 5 Results
- Upload system เสร็จ 100%
- Text extraction สำหรับ PDF, DOCX เสร็จ
- ระบบ clustering เบื้องต้นทำงานได้
- AI Chat prototype ทดสอบกับ GPT-4 แล้ว

### ปัญหาที่พบ
1. PDF บางไฟล์ extract ข้อความไม่ได้ → ต้องใช้ OCR
2. Clustering accuracy ยังต่ำ (~60%) → ต้องปรับ algorithm
3. Response time ของ AI Chat ช้า (>5 วินาที) → ต้อง optimize prompt

### Action Items
- [ ] วิภา: ปรับ clustering algorithm ให้แม่นขึ้น
- [ ] พัฒน์: เพิ่ม loading animation ขณะ AI ตอบ
- [ ] เซิร์ฟ: optimize API response time
- [ ] ดร.สมชาย: review Knowledge Graph architecture
- [ ] ดีไซน์: ออกแบบ graph visualization UI

### Next Sprint Goals
1. เริ่มพัฒนา Knowledge Graph layer
2. ทดสอบ entity extraction ด้วย LLM
3. ออกแบบ Graph UI
