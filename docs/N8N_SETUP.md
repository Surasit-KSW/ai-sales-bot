# N8N Setup Guide — AI Sales Bot

คู่มือติดตั้งและตั้งค่า N8N เป็น orchestration layer สำหรับ AI Sales Bot

---

## สถาปัตยกรรมโดยรวม

```
Facebook / LINE
      │
      ▼
  N8N Webhook          ← รับ event จากแต่ละช่องทาง
      │
      ▼
POST /process/comment  ← FastAPI (Python + Ollama)
      │
      ├── Lead Capture → Google Sheets
      ├── Owner Notify → LINE Notify
      └── Error Handler → LINE Notify + Sheets
```

**Workflow ทั้ง 5 ไฟล์:**

| ไฟล์ | ชื่อ | หน้าที่ |
|------|------|---------|
| `01_facebook_router.json` | Facebook Comment Router | รับ FB event → AI → ตอบกลับ |
| `02_line_router.json` | LINE Message Router | รับ LINE message → AI → ตอบกลับ |
| `03_lead_capture.json` | Lead Capture | บันทึก leads ลง Google Sheets |
| `04_owner_notify.json` | Owner Notification | แจ้งเจ้าของร้านทาง LINE Notify |
| `05_error_handler.json` | Error Handler | จัดการ errors ทั้งระบบ |

---

## ขั้นตอนที่ 1 — ติดตั้งด้วย Docker Compose

### 1.1 เตรียม environment file

```bash
cp .env.example .env
```

แก้ไข `.env` ให้ครบ:

```env
# Facebook
FB_VERIFY_TOKEN=your_verify_token
FB_PAGE_ACCESS_TOKEN=your_page_access_token

# LINE Bot
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token

# LINE Notify (สำหรับแจ้งเจ้าของร้าน)
LINE_NOTIFY_TOKEN=your_line_notify_token

# N8N
N8N_HOST=localhost
N8N_PORT=5678
N8N_WEBHOOK_URL=http://localhost:5678

# Google Sheets (optional)
GOOGLE_SHEET_ID=your_sheet_id
```

### 1.2 รัน Docker Compose

```bash
docker-compose up -d
```

รอประมาณ 30 วินาที แล้วตรวจสอบว่า services ทำงาน:

```bash
docker-compose ps
```

ผลที่ถูกต้อง:
```
NAME                 STATUS
ai-sales-n8n        Up (healthy)
ai-sales-api        Up (healthy)
ai-sales-dashboard  Up (healthy)
```

### 1.3 ตรวจสอบ health

```bash
# FastAPI health check
curl http://localhost:8000/health

# N8N health check
curl http://localhost:5678/healthz
```

> **หมายเหตุ:** Ollama รันบนเครื่อง host ไม่ได้อยู่ใน Docker  
> ตรวจสอบว่า `ollama serve` ทำงานอยู่ก่อนใช้งาน

---

## ขั้นตอนที่ 2 — เปิด N8N และตั้งค่าเบื้องต้น

1. เปิดเบราว์เซอร์ → `http://localhost:5678`
2. สร้าง account ครั้งแรก (เก็บ email + password ไว้)
3. เข้าสู่ระบบ N8N

---

## ขั้นตอนที่ 3 — Import Workflow JSON

ทำซ้ำสำหรับทุกไฟล์ใน `n8n/workflows/`:

1. คลิก **Workflows** ในเมนูซ้าย
2. คลิกปุ่ม **Import** (มุมบนขวา) → **Import from file**
3. เลือกไฟล์ตามลำดับ:
   - `01_facebook_router.json`
   - `02_line_router.json`
   - `03_lead_capture.json`
   - `04_owner_notify.json`
   - `05_error_handler.json`
4. คลิก **Save** หลัง import แต่ละไฟล์

> **สำคัญ:** Import ตามลำดับ เพราะ workflow 01/02 เรียก webhook ของ 03/04/05

---

## ขั้นตอนที่ 4 — ตั้งค่า Credentials

### 4.1 Google Sheets (สำหรับ Lead Capture)

1. ไปที่ **Settings → Credentials → Add Credential**
2. เลือก **Google Sheets OAuth2 API**
3. ทำ OAuth2 flow ตามขั้นตอน
4. ตั้งชื่อว่า `Google Sheets Account` (ต้องตรงกับที่ใน workflow)

สร้าง Google Sheet มีชื่อ sheet ดังนี้:
- Sheet 1: `Leads` — คอลัมน์: `timestamp, channel, user_name, user_id, comment_text, intent, confidence, sentiment, reply_sent, should_escalate, shop_name`
- Sheet 2: `ErrorLog` — คอลัมน์: `timestamp, severity, source, message`

### 4.2 LINE Notify Token

1. ไปที่ https://notify-bot.line.me/my/
2. คลิก **Generate token**
3. เลือก Group หรือ 1:1 ที่ต้องการรับแจ้งเตือน
4. คัดลอก token ใส่ใน `.env` → `LINE_NOTIFY_TOKEN`

### 4.3 N8N Environment Variables

N8N อ่าน env vars จาก `docker-compose.yml` โดยอัตโนมัติ  
ตัวแปรที่ใช้ใน workflows:
- `$env.FASTAPI_INTERNAL_URL` → `http://fastapi:8000`
- `$env.N8N_WEBHOOK_URL` → `http://localhost:5678`
- `$env.FB_PAGE_ACCESS_TOKEN`
- `$env.LINE_CHANNEL_ACCESS_TOKEN`
- `$env.LINE_NOTIFY_TOKEN`
- `$env.GOOGLE_SHEET_ID`

---

## ขั้นตอนที่ 5 — เปิด Workflow ทีละตัว

เปิดตามลำดับนี้:

1. **05 Error Handler** — เปิดก่อนเพื่อรับ errors จาก workflow อื่น
2. **04 Owner Notify** — เปิดก่อนใช้งาน 01/02
3. **03 Lead Capture** — เปิดก่อนใช้งาน 01/02
4. **02 LINE Router** — เปิดเมื่อ LINE Bot พร้อม
5. **01 Facebook Router** — เปิดเมื่อ Facebook Webhook พร้อม

วิธีเปิด workflow:
1. เปิด workflow ที่ต้องการ
2. Toggle **Inactive → Active** มุมบนขวา
3. ตรวจสอบว่า Webhook URL ปรากฏขึ้น

---

## ขั้นตอนที่ 6 — ทดสอบด้วย Test Webhook

### ทดสอบ /process/comment โดยตรง

```bash
curl -X POST http://localhost:8000/process/comment \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "facebook",
    "text": "ราคาเท่าไหร่คะ มีโปรไหม",
    "user_name": "ทดสอบ",
    "comment_id": "test-001"
  }'
```

ผลที่ถูกต้อง:
```json
{
  "success": true,
  "intent": "POTENTIAL_BUYER",
  "confidence": 0.95,
  "reply": "สวัสดีค่ะ...",
  "should_escalate": false,
  "processing_time_ms": 3200
}
```

### ทดสอบ N8N Webhook (Workflow 01)

1. เปิด Workflow 01 ใน N8N
2. คลิก **Test Webhook** (ปุ่มบน Webhook node)
3. ส่ง test payload:

```bash
curl -X POST http://localhost:5678/webhook-test/facebook-comment \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "verb": "add",
          "comment_id": "123456",
          "post_id": "post_001",
          "from": {"id": "user_001", "name": "ทดสอบ"},
          "message": "สนใจสินค้าค่ะ ราคาเท่าไหร่",
          "created_time": 1713139200
        }
      }]
    }]
  }'
```

4. ดูผลใน **Execution Log** ของ N8N

### ทดสอบ Escalation

```bash
curl -X POST http://localhost:8000/process/comment \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "line",
    "text": "โกงชัดๆ สินค้าไม่ตรงปก อยากคืนเงิน",
    "user_name": "ลูกค้าทดสอบ"
  }'
```

ผลที่ถูกต้อง: `"should_escalate": true`, `"reply": ""`

---

## Webhook URLs สำหรับ Facebook / LINE

เมื่อ activate workflows แล้ว ให้นำ URL เหล่านี้ไปกรอกใน Dashboard:

| Platform | URL |
|----------|-----|
| Facebook (Meta Developer Console) | `https://your-domain/webhook/facebook-comment` |
| LINE (LINE Developers Console) | `https://your-domain/webhook/line-message` |

> **Production:** ต้องใช้ HTTPS — ใช้ reverse proxy เช่น nginx + Let's Encrypt  
> หรือ ngrok สำหรับทดสอบ: `ngrok http 5678`

---

## Troubleshooting

| ปัญหา | วิธีแก้ |
|-------|---------|
| N8N ไม่ตอบสนอง | `docker-compose restart n8n` |
| FastAPI 422 error | ตรวจสอบ JSON body ให้ตรงกับ `CommentRequest` schema |
| Ollama timeout | เพิ่ม `request_timeout_seconds` ใน `config.py`, หรือใช้ model เล็กกว่า |
| Google Sheets error | ตรวจสอบ OAuth2 credentials + Sheet ID + ชื่อ sheet ต้องตรง |
| LINE Notify ไม่ส่ง | ตรวจสอบ `LINE_NOTIFY_TOKEN` ใน `.env` |
| Workflow ไม่ trigger | ตรวจสอบว่า workflow status = **Active** |

---

## ดู Logs

```bash
# N8N logs
docker-compose logs n8n --tail=50

# FastAPI logs
docker-compose logs fastapi --tail=50

# ดู Execution history ใน N8N
# http://localhost:5678 → Executions (เมนูซ้าย)
```
