# สรุปบทเรียน: Machine Learning for Knowledge Graphs

## Chapter 1: Introduction to Knowledge Graphs
Knowledge Graph คือกราฟที่แสดงความสัมพันธ์ระหว่าง entities
ประกอบด้วย nodes (entities) และ edges (relationships)

## Chapter 2: Node Embedding
- TransE: แปลง entities เป็น vectors
- Node2Vec: Random walk based embedding
- GCN: Graph Convolutional Networks

## Chapter 3: Link Prediction
ใช้ embedding เพื่อทำนายว่า nodes ไหนน่าจะมีความสัมพันธ์กัน
- Scoring function: f(h, r, t)
- Training: minimize loss function
- Evaluation: Mean Reciprocal Rank (MRR)

## Chapter 4: Applications
1. Google Knowledge Panel
2. Facebook Social Graph
3. Amazon Product Graph
4. Personal Knowledge Management (PKM)

## บันทึกเพิ่มเติม
- ดร.สมชาย แนะนำให้ศึกษา Neo4j สำหรับ production
- วิภา เคยทำงานวิจัยเรื่อง Knowledge Graph ที่ MIT
- สัปดาห์หน้ามีสัมมนาเรื่อง Graph Neural Networks ที่จุฬาฯ
