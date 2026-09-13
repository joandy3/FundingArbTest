# Binance Futures Viewer

แอป Flask ไฟล์เดียว (`app.py`) สำหรับดู **Funding Fee** และ **Order** (open orders +
ประวัติตาม symbol) จาก Binance Futures API โดยใช้ API Key/Secret ของคุณเอง

## ติดตั้งและรัน

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

เปิดเบราว์เซอร์ไปที่ `http://127.0.0.1:5000`

## ⚠️ ความปลอดภัย — อ่านก่อนใช้งาน

1. **สร้าง Binance API key แบบ Read-Only เท่านั้น**
   ตอนสร้างคีย์บน Binance ให้ปิดสิทธิ์ "Enable Withdrawals" และ "Enable Trading"
   ไว้เสมอ ถ้าคีย์หลุดจะได้ไม่มีใครถอนเงินหรือสั่งเทรดแทนคุณได้
   แนะนำให้ตั้งค่า **IP whitelist** ผูกกับ IP เครื่องที่รันแอปนี้ด้วย

2. **อย่า commit คีย์จริงลงโค้ด**
   แอปนี้ให้คุณกรอกคีย์ผ่านหน้าเว็บตอนรัน ไม่มีคีย์ใดๆ อยู่ในซอร์สโค้ด —
   อย่าไปแก้โค้ดแล้วใส่คีย์ตรงๆ ลงไฟล์ ถ้าต้องการค่าคงที่ระหว่างพัฒนา
   ให้ใช้ไฟล์ `.env` (ซึ่งอยู่ใน `.gitignore` แล้ว ไม่มีทาง commit ขึ้นไปโดยไม่ตั้งใจ)

3. **`FLASK_SECRET_KEY`**
   ค่านี้ใช้ sign session cookie ของตัวแอปเอง (คนละอย่างกับ Binance API secret)
   ถ้าไม่ตั้งค่า จะสุ่มใหม่ทุกครั้งที่รัน (แปลว่า session จะหลุดทุกครั้งที่รีสตาร์ท
   ซึ่งโอเคสำหรับใช้คนเดียว) หากต้องการค่าคงที่:
   ```bash
   export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

4. **Debug mode ปิดอยู่โดย default**
   เปิดเฉพาะตอนพัฒนาบนเครื่องตัวเองเท่านั้นด้วย `FLASK_DEBUG=1 python app.py`
   ห้ามเปิดถ้าแอปสามารถเข้าถึงได้จากเครื่องอื่นหรือจากอินเทอร์เน็ต

5. **การเก็บคีย์ระหว่างรัน**
   API Key/Secret ที่คุณกรอกจะถูกเก็บไว้ใน **หน่วยความจำฝั่งเซิร์ฟเวอร์เท่านั้น**
   (ไม่เขียนลงไฟล์ ไม่ log ออกมา) ส่วน cookie ในเบราว์เซอร์จะเก็บแค่ token
   สุ่มที่ใช้ค้นหาคีย์ในหน่วยความจำ — ไม่ใช่ตัวคีย์จริง รีสตาร์ทแอปแล้วต้อง
   ล็อกอินใหม่ทุกครั้ง

6. **อย่า deploy ขึ้นเซิร์ฟเวอร์สาธารณะแบบตรงๆ**
   โค้ดนี้ออกแบบมาให้รันบนเครื่องตัวเอง (`127.0.0.1`) ถ้าต้องการเปิดให้เข้าถึง
   จากที่อื่น ควรเพิ่ม HTTPS, authentication ชั้นเพิ่มเติม, และพิจารณาใช้
   session store แบบถาวร (เช่น Redis) แทนหน่วยความจำในโปรเซส

## โครงสร้างไฟล์

```
.
├── app.py            # แอปหลัก (routes + Binance API calls + templates)
├── requirements.txt  # Flask, requests
├── .gitignore
└── README.md
```
