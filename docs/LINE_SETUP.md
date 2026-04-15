# คู่มือตั้งค่า LINE Official Account สำหรับ AI Sales Bot

คู่มือนี้พาคุณตั้งค่าตั้งแต่เริ่มต้นจนถึงรับ message จากลูกค้า LINE เข้า bot ได้จริง  
เขียนสำหรับคนที่ไม่เคยใช้ LINE Developers Console มาก่อน ทำตามทีละขั้นได้เลย

---

## สารบัญ

1. [สิ่งที่ต้องเตรียม](#1-สิ่งที่ต้องเตรียม)
2. [สร้าง LINE Official Account](#2-สร้าง-line-official-account)
3. [เปิด Messaging API](#3-เปิด-messaging-api)
4. [สร้าง Provider และ Channel ใน LINE Developers](#4-สร้าง-provider-และ-channel-ใน-line-developers)
5. [เก็บ Credentials ใส่ .env](#5-เก็บ-credentials-ใส่-env)
6. [ตั้งค่า Webhook URL](#6-ตั้งค่า-webhook-url)
7. [ปิด Auto-reply และ Greeting Message](#7-ปิด-auto-reply-และ-greeting-message)
8. [ทดสอบ Bot](#8-ทดสอบ-bot)
9. [ปัญหาที่พบบ่อย](#9-ปัญหาที่พบบ่อย)

---

## 1. สิ่งที่ต้องเตรียม

| สิ่งที่ต้องมี | รายละเอียด |
|---|---|
| LINE Account ส่วนตัว | ใช้ scan QR สมัคร LINE OA และ login ต่าง ๆ |
| อีเมล | ใช้สมัคร LINE Business Account |
| ngrok | expose port 8000 ออก internet (ดูวิธีติดตั้งได้ใน `docs/FACEBOOK_SETUP.md`) |
| Bot รันอยู่ | รัน `scripts/start_dev.bat` หรือ `start_dev.sh` ให้ FastAPI ขึ้นที่ port 8000 แล้ว |

> **ตรวจสอบก่อนเริ่ม:** เปิด terminal แล้วรัน `curl http://localhost:8000/health`  
> ถ้าได้ `{"status":"ok"}` แสดงว่า bot พร้อมแล้ว

---

## 2. สร้าง LINE Official Account

LINE Official Account (LINE OA) คือบัญชีร้านค้าบน LINE ที่ลูกค้า add friend แล้วแชทด้วยได้  
ถ้ามี LINE OA อยู่แล้ว ข้ามไป [ขั้นตอนที่ 3](#3-เปิด-messaging-api) ได้เลย

### 2.1 สมัครผ่าน LINE Official Account Manager

1. เปิดเบราว์เซอร์ไปที่ **[https://manager.line.biz](https://manager.line.biz)**
2. คลิก **"Log in"** มุมขวาบน
3. เลือก **"Log in with LINE"** แล้ว scan QR ด้วยมือถือ  
   *(หรือใส่อีเมล + รหัสผ่านของบัญชี LINE Business ถ้ามีอยู่แล้ว)*

```
┌─────────────────────────────────────────┐
│  LINE Official Account Manager          │
│                                         │
│  [Log in with LINE]                     │
│  [Log in with email]                    │
│                                         │
│  ← ใช้ปุ่มนี้ scan QR ด้วยมือถือ       │
└─────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: หน้า login ของ manager.line.biz]**

4. หลัง login สำเร็จ คลิก **"Create"** หรือ **"สร้างบัญชี"**

### 2.2 กรอกข้อมูล LINE OA

1. เลือกประเภทบัญชี: **"สร้าง LINE Official Account ใหม่"**
2. กรอกข้อมูล:
   - **ชื่อบัญชี:** ชื่อร้านของคุณ (ลูกค้าจะเห็นชื่อนี้)
   - **อีเมล:** อีเมลสำหรับรับการแจ้งเตือน
   - **ประเภทธุรกิจ:** เลือกหมวดหมู่ที่ใกล้เคียงที่สุด
3. คลิก **"ยืนยัน"** แล้วรอ SMS/email OTP

```
┌────────────────────────────────────────────────┐
│  สร้าง LINE Official Account                   │
│                                                │
│  ชื่อบัญชี: [ร้านของคุณ               ]        │
│  อีเมล:    [your@email.com            ]        │
│  ประเภท:   [ค้าปลีก ▼                 ]        │
│                                                │
│             [ยืนยัน]                           │
└────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: ฟอร์มสร้าง LINE OA]**

5. เมื่อสร้างสำเร็จ จะเห็นหน้า Dashboard ของ LINE OA  
   จะมี **LINE ID** (เริ่มด้วย `@`) แสดงอยู่ เก็บไว้ใช้ภายหลัง

> 📸 **[SCREENSHOT: หน้า Dashboard LINE OA หลังสร้างสำเร็จ — ชี้ที่ LINE ID]**

---

## 3. เปิด Messaging API

Messaging API คือระบบที่ทำให้ bot รับ-ส่งข้อความได้ผ่าน code  
LINE OA ที่เพิ่งสร้างยังไม่มี Messaging API — ต้องเปิดเพิ่ม

### 3.1 เข้าเมนู Messaging API ใน LINE OA Manager

1. อยู่ในหน้า Dashboard ของ LINE OA (**[manager.line.biz](https://manager.line.biz)**)
2. คลิกเมนู **"Settings"** (⚙️) ด้านซ้าย
3. เลือก **"Messaging API"**
4. คลิกปุ่ม **"Enable Messaging API"**

```
┌──────────────────────────────────────────────┐
│  Settings > Messaging API                    │
│                                              │
│  Messaging API                               │
│  Allow your LINE Official Account to         │
│  use the Messaging API.                      │
│                                              │
│  [Enable Messaging API]  ← คลิกตรงนี้        │
└──────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: หน้า Messaging API settings — ปุ่ม Enable]**

### 3.2 เลือก Provider

Provider คือ "เจ้าของ" ของ app — ใช้จัดกลุ่ม channel ต่าง ๆ

- ถ้า **มี Provider อยู่แล้ว** (เช่น เคยทำ app อื่น): เลือก Provider นั้น
- ถ้า **ยังไม่มี**: คลิก **"Create a provider"** แล้วตั้งชื่อ เช่น `MyShop Provider`

```
┌──────────────────────────────────────────────┐
│  Select a provider                           │
│                                              │
│  ○ MyShop Provider (มีอยู่แล้ว)              │
│  ● [Create a provider]  ← ถ้ายังไม่มี        │
│                                              │
│  Provider name: [MyShop Provider    ]        │
│                                              │
│  [OK]                                        │
└──────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: หน้าเลือก Provider]**

5. ยืนยันข้อมูล แล้วคลิก **"OK"** → ระบบจะ redirect ไป LINE Developers Console อัตโนมัติ

---

## 4. สร้าง Provider และ Channel ใน LINE Developers

ถ้าขั้นตอนที่ 3 พาไปที่ LINE Developers Console แล้ว ข้ามไป [ขั้นตอน 5](#5-เก็บ-credentials-ใส่-env) ได้เลย  
ถ้าอยากเข้าโดยตรง:

1. เปิด **[https://developers.line.biz](https://developers.line.biz)**
2. คลิก **"Log in"** แล้ว login ด้วยบัญชีเดิม

### 4.1 หน้า Console หลัก

หลัง login จะเห็น Provider ที่สร้างไว้ คลิกเข้าไป จะเห็น Channel ที่เชื่อมกับ LINE OA

```
┌──────────────────────────────────────────────────────┐
│  LINE Developers Console                             │
│                                                      │
│  Providers                                           │
│  ┌─────────────────┐                                 │
│  │ MyShop Provider │                                 │
│  │  ┌───────────────────────────┐                    │
│  │  │ 🟢 ชื่อร้านของคุณ         │ ← Messaging API   │
│  │  │    Channel ID: 1234567890 │    Channel        │
│  │  └───────────────────────────┘                    │
│  └─────────────────┘                                 │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: LINE Developers Console — เห็น Provider และ Channel]**

2. คลิกที่ Channel ของร้านคุณ จะเข้าสู่หน้าจัดการ Channel

---

## 5. เก็บ Credentials ใส่ .env

ต้องการ 2 ค่าหลัก: **Channel Secret** และ **Channel Access Token**

### 5.1 Channel Secret

1. อยู่ในหน้า Channel ของคุณใน LINE Developers Console
2. คลิก tab **"Basic settings"**
3. เลื่อนลงหา **"Channel secret"**
4. คลิก **"Copy"** เพื่อ copy ค่า (เป็น string ยาวประมาณ 32 ตัวอักษร)

```
┌──────────────────────────────────────────────────────┐
│  Basic settings                                      │
│                                                      │
│  Channel secret                                      │
│  ┌───────────────────────────────────────────┐       │
│  │ a1b2c3d4e5f6...                 [Copy] 📋 │       │
│  └───────────────────────────────────────────┘       │
│                                                      │
│  ← copy ค่านี้ไปใส่ใน LINE_CHANNEL_SECRET            │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: tab Basic settings — ชี้ที่ Channel secret]**

### 5.2 Channel Access Token (Long-lived)

1. คลิก tab **"Messaging API"**
2. เลื่อนลงไปส่วน **"Channel access token"**
3. ถ้ายังไม่มี token ให้คลิก **"Issue"**
4. คลิก **"Copy"** เพื่อ copy token

```
┌──────────────────────────────────────────────────────┐
│  Messaging API                                       │
│                                                      │
│  Channel access token (long-lived)                   │
│  ┌───────────────────────────────────────────┐       │
│  │ (ยังไม่มี token)              [Issue]     │       │
│  └───────────────────────────────────────────┘       │
│                                                      │
│  หลังกด Issue:                                       │
│  ┌───────────────────────────────────────────┐       │
│  │ EAAxxxxx...                    [Copy] 📋  │       │
│  └───────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: tab Messaging API — ส่วน Channel access token]**

> ⚠️ **Long-lived token ไม่หมดอายุ** — เหมาะสำหรับใช้งานจริง  
> ถ้ากด "Reissue" จะทำให้ token เดิมใช้ไม่ได้ทันที ระวังอย่ากดโดยไม่ตั้งใจ

### 5.3 ใส่ค่าใน .env

เปิดไฟล์ `.env` ในโฟลเดอร์หลักของโปรเจกต์ แล้วแก้ไข:

```env
# LINE
LINE_CHANNEL_SECRET=a1b2c3d4e5f6...       ← ค่าจากข้อ 5.1
LINE_CHANNEL_ACCESS_TOKEN=EAAxxxxx...     ← ค่าจากข้อ 5.2
LINE_BOT_BASIC_ID=@myshop                 ← LINE ID ของร้าน (มี @ นำหน้า)
```

บันทึกไฟล์แล้ว **restart bot**:
```bash
# กด Ctrl+C แล้วรันใหม่
scripts\start_dev.bat       # Windows
bash scripts/start_dev.sh   # Linux / macOS
```

---

## 6. ตั้งค่า Webhook URL

Webhook คือ URL ที่ LINE จะส่ง message มาหาทุกครั้งที่มีลูกค้าแชท

### 6.1 เปิด ngrok

เปิด terminal ใหม่ (อย่าปิด terminal ที่รัน bot อยู่):

```bash
ngrok http 8000
```

จะเห็นข้อมูลแบบนี้:

```
Session Status                online
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8000
```

**Copy URL** ที่ขึ้นต้นด้วย `https://` ไว้ใช้ขั้นตอนต่อไป

> ⚠️ URL ของ ngrok (แบบฟรี) จะเปลี่ยนทุกครั้งที่ restart  
> ต้องอัปเดต Webhook URL ใน LINE Console ทุกครั้งที่รัน ngrok ใหม่

### 6.2 ใส่ Webhook URL ใน LINE Developers Console

1. กลับไปที่ **LINE Developers Console** → Channel ของคุณ → tab **"Messaging API"**
2. หาส่วน **"Webhook settings"**
3. คลิก **"Edit"** ถัดจาก Webhook URL
4. ใส่ URL:
   ```
   https://abc123.ngrok-free.app/webhook/line
   ```
   *(แทนที่ `abc123.ngrok-free.app` ด้วย URL จาก ngrok ของคุณ)*
5. คลิก **"Update"**

```
┌──────────────────────────────────────────────────────┐
│  Webhook settings                                    │
│                                                      │
│  Webhook URL                                         │
│  ┌────────────────────────────────────────────────┐  │
│  │ https://abc123.ngrok-free.app/webhook/line     │  │
│  └────────────────────────────────────────────────┘  │
│  [Update]                                            │
│                                                      │
│  Use webhook    ●──  ON   ← ต้องเปิดด้วย!           │
│                                                      │
│  [Verify]  ← กดเพื่อทดสอบว่าเชื่อมต่อได้             │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: Webhook settings — ใส่ URL แล้ว]**

### 6.3 เปิด Use Webhook

Toggle **"Use webhook"** ให้เป็น **ON** (สำคัญมาก — ถ้าปิดอยู่ LINE จะไม่ส่ง message มาให้)

### 6.4 กด Verify

คลิกปุ่ม **"Verify"** — ถ้าขึ้น **"Success"** หรือ **"200"** แสดงว่าเชื่อมต่อได้แล้ว ✅

```
┌──────────────────────────────────────────────────────┐
│  Webhook URL verification                            │
│                                                      │
│  ✅ Success                                          │
│  Status code: 200                                    │
│                                                      │
│  [OK]                                                │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: ผลลัพธ์ Verify — Success]**

**ถ้า Verify ไม่ผ่าน** ดูวิธีแก้ได้ที่ [ปัญหาที่พบบ่อย](#9-ปัญหาที่พบบ่อย)

---

## 7. ปิด Auto-reply และ Greeting Message

> **ทำขั้นตอนนี้ให้เสร็จก่อนทดสอบ** — ถ้าไม่ทำ ลูกค้าจะได้รับการตอบซ้ำ 2 ครั้ง  
> (LINE ตอบด้วย Auto-reply ครั้งหนึ่ง และ bot ตอบอีกครั้งหนึ่ง)

### 7.1 เข้า LINE Official Account Manager

ไปที่ **[https://manager.line.biz](https://manager.line.biz)** → เลือก LINE OA ของคุณ

### 7.2 ปิด Auto-reply Message

1. เมนูซ้าย คลิก **"Chat"** → **"Auto-reply messages"**  
   หรือไปที่ **Settings → Response settings**
2. หา **"Auto-reply"** → Switch ให้เป็น **OFF**

```
┌──────────────────────────────────────────────────────┐
│  Response settings                                   │
│                                                      │
│  Response method                                     │
│  ● Chat    ○ Bot    ← เลือก "Bot" ถ้ามีตัวเลือก     │
│                                                      │
│  Auto-reply messages                                 │
│  Enabled  ──●  OFF  ← ต้องปิด                       │
│                                                      │
│  Greeting message                                    │
│  Enabled  ──●  OFF  ← ต้องปิด                       │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: Response settings — Auto-reply และ Greeting ปิดอยู่]**

### 7.3 ปิด Greeting Message

ในหน้าเดียวกัน หา **"Greeting message"** → Switch ให้เป็น **OFF**

> **หมายเหตุ:** bot จะส่ง welcome message เองเมื่อมีคน follow LINE OA  
> (โค้ดอยู่ใน `app/integrations/line_webhook.py` → `_handle_follow()`)  
> ดังนั้นการปิด Greeting message ของ LINE จึงไม่ทำให้ลูกค้าไม่ได้รับการต้อนรับ

---

## 8. ทดสอบ Bot

### 8.1 Add LINE OA เป็นเพื่อน

1. เปิด LINE บนมือถือ
2. ค้นหา LINE ID ของร้าน (เริ่มด้วย `@`) หรือ scan QR Code ใน LINE OA Manager
3. กด **"Add friend"**

> 📸 **[SCREENSHOT: QR Code สำหรับ add friend — อยู่ใน LINE OA Manager หน้า Home]**

### 8.2 ส่งข้อความทดสอบ

ส่งข้อความหา LINE OA ตัวเอง เช่น:
```
ราคาเท่าไหร่คะ
```

รอสักครู่ (2–10 วินาที) bot จะตอบกลับ

### 8.3 ตรวจสอบใน Streamlit Dashboard

เปิด **[http://localhost:8501](http://localhost:8501)** → tab **"รออนุมัติ"**

ถ้าตั้งค่า `AUTO_REPLY=False` (ค่า default):
- จะเห็น message จาก LINE ขึ้นใน queue พร้อม badge **🟢 LINE Message**
- มีคำตอบที่ AI สร้างมาให้ รอการอนุมัติจากคุณ

```
┌──────────────────────────────────────────────────────┐
│  🕐 รออนุมัติ (1 รายการ)                             │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │ 🟢 LINE Message   🛒 ผู้สนใจซื้อ               │  │
│  │ ชื่อลูกค้า                                     │  │
│  │                                                │  │
│  │ 💬 ราคาเท่าไหร่คะ                              │  │
│  │                                                │  │
│  │ [คำตอบที่ AI สร้าง...                    ]     │  │
│  │                                                │  │
│  │ 📲 Quick Reply Buttons:                        │  │
│  │ □ ดูสินค้าเพิ่มเติม □ ติดต่อแอดมิน □ ดูโปรฯ  │  │
│  │                                                │  │
│  │ [✅ ส่งเลย] [✏️ บันทึกแก้ไข] [❌ ข้าม]       │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```
> 📸 **[SCREENSHOT: Dashboard แสดง LINE message รออนุมัติ]**

### 8.4 ทดสอบ Quick Reply Buttons

1. ติ๊ก checkbox **"ดูสินค้าเพิ่มเติม"** ก่อนกด "ส่งเลย"
2. ลูกค้าจะเห็นปุ่มกลมเล็กใต้ข้อความตอบกลับในแชท LINE
3. กดปุ่มนั้นได้เลยโดยไม่ต้องพิมพ์

> 📸 **[SCREENSHOT: LINE chat — เห็น Quick Reply buttons ใต้ข้อความ bot]**

---

## 9. ปัญหาที่พบบ่อย

### Verify Webhook ไม่ผ่าน

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| `{"message":"Request failed"}` | Bot ไม่รัน | รัน `scripts/start_dev.bat` แล้ว curl `localhost:8000/health` |
| Connection timeout | ngrok ไม่รันหรือ URL ผิด | เปิด ngrok ใหม่ แล้ว copy URL ใหม่ลง Console |
| `{"message":"Invalid signature"}` | URL ถูกแต่ยังไม่ใส่ Channel Secret | ตรวจ `.env` ว่า `LINE_CHANNEL_SECRET` ถูกต้อง แล้ว restart bot |
| 404 Not Found | Path ผิด | ตรวจให้แน่ใจว่า URL ลงท้ายด้วย `/webhook/line` |

### Bot ไม่ตอบหลัง Verify ผ่าน

1. ตรวจว่า **"Use webhook"** เป็น **ON** (คนมักลืมขั้นตอนนี้)
2. ตรวจว่าปิด **Auto-reply** ใน LINE OA Manager แล้ว
3. ดู log ใน terminal ที่รัน FastAPI — ควรเห็น:
   ```
   INFO: LINE TextMessage | user_id=Uxxxxx text=ราคาเท่าไหร่คะ...
   ```
   ถ้าไม่มี log นี้ แสดงว่า LINE ยังไม่ส่ง event มาถึง — ตรวจ Webhook URL อีกครั้ง

### Bot ตอบซ้ำ 2 ครั้ง

- ยังไม่ได้ปิด **Auto-reply** หรือ **Greeting message** ของ LINE  
  ดูวิธีปิดได้ที่ [ขั้นตอนที่ 7](#7-ปิด-auto-reply-และ-greeting-message)

### Token Invalid หลังใช้งานไปสักพัก

Long-lived token ไม่ควรหมดอายุ แต่ถ้า Reissue ไปโดยไม่ตั้งใจ:
1. ไป LINE Developers Console → tab Messaging API
2. กด **"Issue"** เพื่อออก token ใหม่
3. Copy ใส่ `.env` แล้ว restart bot

### LINE แจ้ง "This account cannot receive messages"

- LINE OA ฟรีแพลน (Free plan) มี message quota จำกัด  
  ถ้า quota หมด ต้องอัปเกรดเป็น Light หรือ Standard plan  
  ดูรายละเอียดที่ [https://www.linebiz.com/th/service/line-official-account/plan](https://www.linebiz.com/th/service/line-official-account/plan)

### ดู Log แบบ Real-time

```bash
# ดู log ของ FastAPI (bot ทั้งหมด)
tail -f logs/app.log

# หรือดูจาก terminal ที่รัน bot โดยตรง
```

---

## สรุปขั้นตอนสั้น ๆ

```
1. สร้าง LINE OA → manager.line.biz
2. เปิด Messaging API → เลือก / สร้าง Provider
3. ไป LINE Developers Console → copy Channel Secret + Channel Access Token
4. ใส่ค่าใน .env → restart bot
5. รัน: ngrok http 8000 → copy URL ที่ได้
6. ใส่ URL + /webhook/line ใน LINE Console → Verify ให้ผ่าน
7. เปิด "Use webhook" = ON
8. ปิด Auto-reply + Greeting message ใน LINE OA Manager
9. ส่งข้อความหา LINE OA ตัวเอง → เช็ค Streamlit Dashboard
```

---

## ไฟล์ที่เกี่ยวข้องในโปรเจกต์

| ไฟล์ | หน้าที่ |
|---|---|
| `app/integrations/line_webhook.py` | รับ event จาก LINE และตรวจสอบ signature |
| `app/integrations/line_api.py` | ส่งข้อความกลับหา LINE (reply, push, quick reply) |
| `app/services/message_router.py` | routing message ไปยัง AI pipeline |
| `.env` | เก็บ `LINE_CHANNEL_SECRET` และ `LINE_CHANNEL_ACCESS_TOKEN` |

---

*อัปเดตล่าสุด: 2026-04-15 | รองรับ LINE Messaging API v3*
