# คู่มือตั้งค่า Facebook Webhook สำหรับ AI Sales Bot

คู่มือนี้อธิบายขั้นตอนตั้งแต่ต้นจนถึงการรับ webhook event จาก Facebook Page มายัง bot บนเครื่องของคุณ เขียนสำหรับมือใหม่ที่ยังไม่เคยทำ Meta Developer มาก่อน

---

## สารบัญ

1. [สิ่งที่ต้องเตรียม](#1-สิ่งที่ต้องเตรียม)
2. [สมัคร Meta Developer Account](#2-สมัคร-meta-developer-account)
3. [สร้าง Facebook App](#3-สร้าง-facebook-app)
4. [เปิด ngrok รับ public URL](#4-เปิด-ngrok-รับ-public-url)
5. [ตั้งค่า Webhook URL](#5-ตั้งค่า-webhook-url)
6. [ขอ Permission ที่จำเป็น](#6-ขอ-permission-ที่จำเป็น)
7. [Subscribe Page ให้ App](#7-subscribe-page-ให้-app)
8. [ทดสอบ Webhook](#8-ทดสอบ-webhook)
9. [Copy Access Token ใส่ .env](#9-copy-access-token-ใส่-env)
10. [ปัญหาที่พบบ่อย](#10-ปัญหาที่พบบ่อย)

---

## 1. สิ่งที่ต้องเตรียม

| สิ่งที่ต้องมี | รายละเอียด |
|---|---|
| Facebook Account | บัญชี Facebook ส่วนตัวที่ verify แล้ว |
| Facebook Page | Page ที่คุณเป็น Admin (ถ้ายังไม่มีให้สร้างก่อน) |
| ngrok | โปรแกรม tunnel สำหรับ expose port ออกอินเตอร์เน็ต |
| Python + dependencies | `pip install -r requirements.txt` ครบแล้ว |
| Bot รันอยู่ | `scripts/start_dev.bat` หรือ `start_dev.sh` รันได้แล้ว |

### ติดตั้ง ngrok (ถ้ายังไม่มี)

1. ไปที่ [https://ngrok.com/download](https://ngrok.com/download)
2. สมัครบัญชีฟรี แล้ว download ngrok ตาม OS ของคุณ
3. ทำตาม Getting Started เพื่อ authenticate ngrok กับ authtoken ของคุณ:
   ```bash
   ngrok config add-authtoken <your_authtoken>
   ```

---

## 2. สมัคร Meta Developer Account

1. เปิดเบราว์เซอร์ไปที่ **[https://developers.facebook.com](https://developers.facebook.com)**
2. คลิก **Get Started** มุมขวาบน
3. Login ด้วย Facebook Account ส่วนตัว
4. กรอกข้อมูลที่ถาม (ตำแหน่งงาน, วัตถุประสงค์ ฯลฯ) แล้วคลิก **Complete Registration**
5. อาจมีขั้นตอน verify เบอร์โทรศัพท์ ทำให้เสร็จ

> **หมายเหตุ:** Meta Developer Account ใช้บัญชีเดิมกับ Facebook ส่วนตัว ไม่ต้องสมัครใหม่

---

## 3. สร้าง Facebook App

### 3.1 สร้าง App ใหม่

1. ไปที่ **[https://developers.facebook.com/apps](https://developers.facebook.com/apps)**
2. คลิกปุ่ม **Create App** สีเขียว
3. เลือก **App Type** → **Business** แล้วคลิก **Next**
   - ถ้าถามว่าจะทำอะไร เลือก **Other** → **Next** → **Business**
4. กรอก **App Name** เช่น `My Sales Bot`
5. กรอก **App Contact Email** (อีเมลของคุณ)
6. ใต้ **Business Account** ให้เลือก Business ที่เชื่อมกับ Page ของคุณ (หรือปล่อยว่างไว้ก่อนก็ได้)
7. คลิก **Create App**

### 3.2 เพิ่ม Messenger Product

1. ใน dashboard ของ App จะเห็นหน้า **Add products to your app**
2. หา **Messenger** แล้วคลิก **Set up**
3. ระบบจะพาไปหน้า Messenger settings

### 3.3 เก็บ App Secret

1. ไปที่ **Settings → Basic** (เมนูซ้าย)
2. ดูที่ **App Secret** คลิก **Show** แล้ว copy ค่านี้ไว้
3. นี่คือค่า `FB_APP_SECRET` ที่จะใส่ใน `.env`

---

## 4. เปิด ngrok รับ public URL

> Bot ต้องรันอยู่ก่อน และต้องเปิด ngrok ทิ้งไว้ตลอดที่ใช้ webhook

### 4.1 Start bot

```bash
# Windows
scripts\start_dev.bat

# Linux / macOS / WSL
bash scripts/start_dev.sh
```

ตรวจสอบว่า FastAPI รันอยู่:
```bash
curl http://localhost:8000/health
# ควรได้: {"status":"ok"}
```

### 4.2 Start ngrok

เปิด terminal ใหม่ แล้วรัน:

```bash
ngrok http 8000
```

ngrok จะแสดงข้อมูลแบบนี้:

```
Session Status                online
Account                       your@email.com (Plan: Free)
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8000
```

**Copy URL ที่ขึ้นต้นด้วย `https://`** เช่น `https://abc123.ngrok-free.app`

> **สำคัญ:** URL ของ ngrok จะเปลี่ยนทุกครั้งที่ restart (ถ้าใช้ฟรี plan) ต้องไปอัปเดต Webhook URL ใน Meta Console ทุกครั้ง

---

## 5. ตั้งค่า Webhook URL

### 5.1 เตรียม Verify Token

เลือก string ใดก็ได้ที่คุณสร้างขึ้นเอง เช่น `my_secret_verify_token_2024`  
บันทึกค่านี้ไว้ — จะต้องใส่ทั้งใน `.env` และใน Meta Console

เปิดไฟล์ `.env` แล้วแก้ไข:
```env
FB_VERIFY_TOKEN=my_secret_verify_token_2024
```

Restart FastAPI ให้โหลด .env ใหม่:
```bash
# กด Ctrl+C แล้วรัน start_dev อีกครั้ง
```

### 5.2 ตั้งค่าใน Meta Console

1. ไปที่ **App ของคุณ → Messenger → Settings**
2. เลื่อนลงหา **Webhooks** section
3. คลิก **Add Callback URL**
4. กรอกข้อมูล:
   - **Callback URL:** `https://abc123.ngrok-free.app/webhook`  
     *(แทนที่ด้วย ngrok URL จริงของคุณ)*
   - **Verify Token:** `my_secret_verify_token_2024`  
     *(ต้องตรงกับที่ใส่ใน .env)*
5. คลิก **Verify and Save**

ถ้า verify สำเร็จ จะแสดง **"Complete"** สีเขียว

> **Debug:** ถ้า verify ไม่ผ่าน ให้ตรวจสอบว่า
> - FastAPI รันอยู่ และ ngrok tunnel ยังเปิดอยู่
> - Verify Token ตรงกันทั้งสองฝั่ง
> - URL ลงท้ายด้วย `/webhook` (ไม่มี `/` ท้าย)

---

## 6. ขอ Permission ที่จำเป็น

### 6.1 Permission สำหรับอ่าน Comment

ใน **Messenger → Settings → Webhooks** คลิก **Add Subscriptions** แล้วเลือก:

| Permission | ใช้ทำอะไร |
|---|---|
| `messages` | รับ DM ที่ส่งมาหา Page |
| `messaging_postbacks` | รับ postback จาก button |
| `feed` | รับ event เมื่อมีคน post/comment บน Page |
| `mention` | รับ event เมื่อ mention Page |

คลิก **Save**

### 6.2 Permission สำหรับ Reply

Bot ต้องการ permission เหล่านี้เพื่อตอบกลับ:

| Permission | รายละเอียด |
|---|---|
| `pages_messaging` | ส่ง message ผ่าน Messenger API |
| `pages_read_engagement` | อ่าน comment และ reaction |
| `pages_manage_posts` | ตอบ comment บน Page posts |
| `pages_read_user_content` | อ่าน comment ของ user |

### 6.3 วิธีขอ Permission (Development Mode)

ระหว่าง development ไม่ต้อง submit review — App ในโหมด **Development** สามารถทดสอบกับ Admin/Tester ของ App ได้เลย

1. ไปที่ **App Review → Permissions and Features** (เมนูซ้าย)
2. ค้นหา permission แต่ละตัวที่ต้องการ
3. คลิก **Request** ถัดจากแต่ละ permission
4. กรอกคำอธิบายการใช้งาน (สำหรับ Development ไม่ต้องส่ง review)

> ถ้าต้องการ Go Live เพื่อให้คนทั่วไปใช้ได้ ต้องผ่าน App Review ของ Meta ซึ่งใช้เวลา 1–5 วันทำการ

---

## 7. Subscribe Page ให้ App

Bot จะยังไม่รับ event จาก Page จนกว่าจะ subscribe Page เข้ากับ App

### 7.1 Generate Page Access Token

1. ไปที่ **Messenger → Settings**
2. เลื่อนลงหา **Access Tokens** section
3. คลิก **Add or Remove Pages** → เลือก Page ของคุณ → **Next → Done**
4. ตอนนี้จะเห็น Page ของคุณในรายการ คลิก **Generate Token**
5. **Copy Token** นี้ไว้ — นี่คือ `FB_PAGE_ACCESS_TOKEN`

### 7.2 Subscribe Page ผ่าน API

เปิด terminal แล้วรันคำสั่งนี้ (แทนที่ค่าด้วยของจริง):

```bash
PAGE_ID="your_page_id"          # ดูจาก Page → About → Page ID
PAGE_ACCESS_TOKEN="EAAxxxxx..."  # token ที่ generate ไว้
NGROK_URL="https://abc123.ngrok-free.app"

curl -X POST \
  "https://graph.facebook.com/v19.0/${PAGE_ID}/subscribed_apps" \
  -d "subscribed_fields=feed,messages,messaging_postbacks,mention" \
  -d "access_token=${PAGE_ACCESS_TOKEN}"
```

ถ้าสำเร็จจะได้ `{"success": true}`

### 7.3 หา Page ID

1. เปิด Facebook Page ของคุณ
2. คลิก **About** (ข้อมูลเพิ่มเติม)
3. เลื่อนลงล่างสุด จะเห็น **Page ID** เป็นตัวเลข เช่น `123456789012345`

---

## 8. ทดสอบ Webhook

### 8.1 ทดสอบด้วย Meta Webhook Test Tool

1. ไปที่ **Messenger → Settings → Webhooks**
2. คลิก **Test** ถัดจาก Webhook URL ของคุณ
3. เลือก event type เช่น `messages`
4. คลิก **Send to Server**
5. ดู log ใน terminal ที่รัน FastAPI — ควรเห็น log บอกว่าได้รับ event

### 8.2 ทดสอบจริงบน Page

1. เปิด Facebook แล้วไปที่ Page ของคุณ
2. **ทดสอบ DM:** ส่ง message หา Page จาก account อื่น (หรือใช้ Page's Inbox)
3. **ทดสอบ Comment:** โพสต์อะไรก็ได้บน Page แล้วให้คนอื่น comment

ดู log ใน terminal:
```bash
# ควรเห็นบรรทัดแบบนี้
INFO: Facebook webhook received | type=messages | page_id=123...
INFO: Processing comment from user 456... | post_id=789...
```

### 8.3 ทดสอบผ่าน curl โดยตรง

```bash
# ทดสอบ health check
curl http://localhost:8000/health

# ทดสอบ webhook verification
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=my_secret_verify_token_2024&hub.challenge=test123"
# ควรได้: test123
```

---

## 9. Copy Access Token ใส่ .env

เปิดไฟล์ `.env` ในโฟลเดอร์หลักของโปรเจกต์:

```env
# -----------------------------------------------------------------------
# Facebook
# -----------------------------------------------------------------------

# Token ที่คุณตั้งเองใน step 5.1 (ต้องตรงกับที่ใส่ใน Meta Console)
FB_VERIFY_TOKEN=my_secret_verify_token_2024

# Page Access Token จาก step 7.1
FB_PAGE_ACCESS_TOKEN=EAAxxxxx...xxxxxxxxxx

# App Secret จาก step 3.3 (Settings → Basic → App Secret)
FB_APP_SECRET=abc123def456...

# -----------------------------------------------------------------------
# การตอบกลับอัตโนมัติ
# -----------------------------------------------------------------------

# ตอนทดสอบ ตั้งเป็น False ก่อน — bot จะสร้างคำตอบแต่ไม่ส่ง
AUTO_REPLY=False

# เมื่อพร้อม Go Live ให้เปลี่ยนเป็น True
# AUTO_REPLY=True
```

หลังแก้ไข `.env` ต้อง **restart FastAPI** ให้โหลดค่าใหม่:
```bash
# กด Ctrl+C ใน terminal ที่รัน start_dev แล้วรันใหม่
```

---

## 10. ปัญหาที่พบบ่อย

### Webhook Verify ไม่ผ่าน

| อาการ | สาเหตุที่เป็นไปได้ | วิธีแก้ |
|---|---|---|
| `{"error":"Verify token mismatch"}` | Verify token ไม่ตรงกัน | ตรวจสอบให้ `.env` และ Meta Console ใส่ token เดียวกัน |
| `Connection refused` | FastAPI หรือ ngrok ไม่รัน | ตรวจสอบว่า `start_dev` รันอยู่และ ngrok tunnel ยังเปิดอยู่ |
| `404 Not Found` | URL ผิด | ตรวจสอบว่า URL ลงท้ายด้วย `/webhook` |
| Timeout | ngrok URL หมดอายุ | รัน `ngrok http 8000` ใหม่ และอัปเดต URL ใน Meta Console |

### Bot ไม่รับ Event จาก Page

1. ตรวจสอบว่า Page subscribe กับ App แล้ว (step 7.2)
2. ตรวจสอบว่า subscribed fields ครอบคลุม event ที่ต้องการ
3. App ต้องอยู่ใน **Development Mode** และ user ต้องเป็น Admin/Tester ของ App
4. ดู **Webhooks Logs** ใน Meta Developer Console → App → Messenger → Settings → Webhooks → View Logs

### Token หมดอายุ

Page Access Token แบบ **short-lived** หมดอายุใน 1–2 ชั่วโมง  
สำหรับ production ให้สร้าง **long-lived token** โดย:

```bash
# แทนที่ APP_ID, APP_SECRET, SHORT_LIVED_TOKEN ด้วยค่าจริง
curl "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

Token ที่ได้จะมีอายุ ~60 วัน สำหรับ production จริงควรใช้ **System User Token** ที่ไม่หมดอายุ

### ดู Log แบบ Real-time

```bash
# ดู log ของ bot
tail -f logs/app.log

# หรือดูจาก terminal ที่รัน FastAPI โดยตรง
```

---

## สรุปขั้นตอนสั้น ๆ

```
1. สมัคร Meta Developer → developers.facebook.com
2. สร้าง App ประเภท Business → เพิ่ม Messenger product
3. รัน: scripts\start_dev.bat  (หรือ start_dev.sh)
4. รัน: ngrok http 8000  → copy URL ที่ได้
5. ใส่ URL + Verify Token ใน Meta Console → Verify and Save
6. เลือก Webhook subscriptions (feed, messages, ...)
7. Generate Page Access Token → Subscribe Page
8. ใส่ Token ทั้งหมดใน .env → Restart FastAPI
9. ทดสอบ comment บน Page → ดู log ใน terminal
```

---

*อัปเดตล่าสุด: 2026-04-15 | รองรับ Messenger API v19.0*
