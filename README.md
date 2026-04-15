<div align="center">

# 🤖 AI Sales Assistant
### ระบบ AI ตอบคอมเมนต์ลูกค้าอัตโนมัติ สำหรับร้านค้าออนไลน์ไทย

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.33+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge&logo=ollama)](https://ollama.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**ฟรี | Private | ทำงานบน Local | ไม่มีค่า API รายเดือน**

</div>

---

## 🎯 ปัญหาที่แก้ได้

ร้านค้าออนไลน์บน Facebook / LINE OA ได้รับคอมเมนต์หลายร้อยข้อความต่อวัน การตอบด้วยมือทุกข้อความ **ช้า ไม่สม่ำเสมอ และพลาดโอกาสขาย**

AI Sales Assistant อ่านทุกคอมเมนต์ → จำแนกประเภท → สร้างคำตอบภาษาไทยที่เหมาะสมกับร้านของคุณ → รอ **อนุมัติ** ก่อนส่ง

---

## ✨ ความสามารถหลัก

| Feature | รายละเอียด |
|---------|-----------|
| 🧠 **Intent Classification** | จำแนกเป็น 4 ประเภท: ผู้สนใจซื้อ / สอบถามทั่วไป / ร้องเรียน / Spam |
| ✍️ **Thai Reply Generation** | สร้างคำตอบภาษาไทยที่เป็นธรรมชาติ ตาม tone ร้านคุณ |
| 🏪 **Shop Profile** | แก้ไฟล์ `shop_profile.yaml` เพียงไฟล์เดียว ไม่ต้องแตะ code |
| 🖥️ **Streamlit Dashboard** | UI อนุมัติ/แก้ไขคำตอบก่อนส่ง + ดูสถิติ |
| 📱 **Facebook Integration** | รับ Webhook จาก Facebook Page Comment อัตโนมัติ |
| 💬 **LINE OA Integration** | รับข้อความจาก LINE Official Account อัตโนมัติ |
| 🔄 **n8n Orchestration** | Workflow automation เชื่อม channel ต่าง ๆ เข้า AI backend |
| 🗄️ **SQLite History** | บันทึกประวัติทุก conversation พร้อม approval status |
| 🐳 **Docker Ready** | `docker-compose up` เดียว ได้ครบทุก service |
| 🔒 **100% Private** | รันบนเครื่องคุณ ข้อมูลลูกค้าไม่ออกไปไหน |
| 💸 **ฟรีตลอดชีพ** | ไม่มีค่า API ไม่มีรายเดือน |

---

## 🏗️ สถาปัตยกรรมระบบ

```
                    ┌─────────────────────────────────────┐
                    │         External Channels            │
                    │   Facebook Page    LINE Official     │
                    │   (Comments/DM)    Account (Bot)     │
                    └──────────┬───────────────┬───────────┘
                               │ Webhook       │ Webhook
                    ┌──────────▼───────────────▼───────────┐
                    │         FastAPI Backend :8000         │
                    │  /webhook  /webhook/line  /process/*  │
                    └──────────────────┬────────────────────┘
                                       │
                         ┌─────────────▼──────────────┐
                         │       AI Pipeline           │
                         │  Analyzer → Generator       │
                         │  (Ollama + Gemma 3 4B)      │
                         └──────┬─────────────┬────────┘
                                │             │
                    ┌───────────▼──┐     ┌────▼──────────────┐
                    │  SQLite DB   │     │  n8n Orchestrator  │
                    │  (History)   │     │  :5678 (Workflows) │
                    └──────────────┘     └────────────────────┘
                                                │
                         ┌──────────────────────▼──────────┐
                         │    Streamlit Dashboard :8501     │
                         │  อนุมัติ / แก้ไข / ส่งคำตอบ     │
                         └─────────────────────────────────┘
```

---

## 📁 โครงสร้างโปรเจกต์

```
ai-sales-bot/
│
├── 📄 shop_profile.yaml        ← ✏️  แก้ตรงนี้อย่างเดียว! ข้อมูลร้านของคุณ
├── 📄 main.py                  ← CLI mode: รันกับไฟล์ข้อมูลจริง
├── 📄 main_api.py              ← FastAPI entry point (webhook + REST API)
├── 📄 demo.py                  ← รันเพื่อดู demo 5 ตัวอย่าง
├── 📄 streamlit_app.py         ← Streamlit Dashboard (approval UI)
├── 📄 Dockerfile               ← Container image สำหรับ fastapi & streamlit
├── 📄 docker-compose.yml       ← Orchestrate: n8n + fastapi + streamlit
│
├── 📂 app/
│   ├── 📂 core/
│   │   ├── config.py           ← ตั้งค่า AI (model, temperature, prompts)
│   │   ├── database.py         ← SQLite ORM (conversation history)
│   │   ├── llm_client.py       ← Ollama wrapper (retry, error handling)
│   │   └── profile_loader.py   ← โหลด shop_profile.yaml → dataclass
│   │
│   ├── 📂 services/
│   │   ├── analyzer.py         ← จำแนก intent ของคอมเมนต์
│   │   ├── comment_processor.py← End-to-end pipeline: analyze → generate → save
│   │   ├── generator.py        ← สร้างคำตอบภาษาไทย
│   │   └── message_router.py   ← Route message ไปยัง channel ที่ถูกต้อง
│   │
│   ├── 📂 integrations/
│   │   ├── facebook_api.py     ← Facebook Graph API client
│   │   ├── facebook_webhook.py ← FastAPI router: FB verification + events
│   │   ├── line_api.py         ← LINE Messaging API client
│   │   ├── line_webhook.py     ← FastAPI router: LINE bot events
│   │   └── process_router.py   ← FastAPI router: /process/* (n8n calls)
│   │
│   └── 📂 utils/
│       └── logger.py           ← Structured logging (console + file)
│
├── 📂 n8n/
│   └── 📂 workflows/           ← n8n workflow JSON files (import ได้เลย)
│
├── 📂 scripts/
│   ├── 01_setup.py             ← Setup wizard: ตรวจสอบ dependencies
│   ├── start_dev.sh            ← Start all services (Linux/Mac)
│   └── start_dev.bat           ← Start all services (Windows)
│
└── 📂 data/
    ├── input_comments.txt      ← CLI mode: ใส่คอมเมนต์ (1 บรรทัด = 1 คอมเมนต์)
    └── bot.db                  ← SQLite database (auto-created)
```

---

## 🛠️ การติดตั้ง

### Requirements
- Python 3.11+
- [Ollama](https://ollama.com) (ดาวน์โหลดและติดตั้ง)
- Docker + Docker Compose *(สำหรับ production mode)*

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ai-sales-bot.git
cd ai-sales-bot

# สร้าง virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# ติดตั้ง dependencies
pip install -r requirements.txt
```

### 2. ดาวน์โหลด AI Model

```bash
ollama pull gemma3:4b
```

> **หมายเหตุ:** ต้องการ RAM ~6GB | ดาวน์โหลดครั้งแรก ~3.3GB

### 3. ตั้งค่า Environment Variables

```bash
cp .env.example .env
```

แก้ไฟล์ `.env`:

```env
# Facebook
FB_VERIFY_TOKEN=your_verify_token
FB_PAGE_ACCESS_TOKEN=your_page_access_token

# LINE
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## ⚙️ ตั้งค่าร้านของคุณ

แก้ไฟล์ `shop_profile.yaml` — **ไม่ต้องรู้ Python เลย**

```yaml
shop:
  name: "ชื่อร้านคุณ"
  tagline: "สโลแกนร้าน"

products:
  category: "ประเภทสินค้า"
  price_range: "เริ่มต้น XXX บาท"
  promotions: "โปรโมชั่นปัจจุบัน"

contact:
  line_id: "@yourshop"
  order_channel: "ทักมาทาง Inbox หรือ LINE"

reply_style:
  tone: "เป็นกันเอง"      # สุภาพมาก / เป็นกันเอง / ทางการ
  closing_word: "ค่ะ"     # ครับ หรือ ค่ะ
  use_emoji: true
```

---

## ▶️ วิธีใช้งาน

### Mode 1 — Demo (ทดสอบครั้งแรก)

```bash
ollama serve          # เปิด Ollama (Terminal แรก)
python demo.py        # รัน demo 5 ตัวอย่าง (Terminal ที่สอง)
```

### Mode 2 — CLI (ประมวลผลไฟล์)

```bash
# 1. ใส่คอมเมนต์ลูกค้าใน data/input_comments.txt (1 บรรทัด = 1 คอมเมนต์)
# 2. รัน
ollama serve
python main.py

# ผลลัพธ์จะอยู่ที่ data/processed_results.json
```

### Mode 3 — Full Stack (Docker)

```bash
# 1. ตั้งค่า .env ก่อน
cp .env.example .env

# 2. รัน Ollama บน host (Docker ไม่รัน Ollama)
ollama serve

# 3. เปิดทุก service ด้วยคำสั่งเดียว
docker-compose up -d

# Services ที่เปิดขึ้นมา:
#   http://localhost:8000   FastAPI (API docs: /docs)
#   http://localhost:8501   Streamlit Dashboard
#   http://localhost:5678   n8n Workflow Editor
```

### Mode 4 — Development (ไม่ใช้ Docker)

```bash
# Windows
scripts/start_dev.bat

# Linux/Mac
scripts/start_dev.sh
```

---

## 📊 Demo Output

```
════════════════════════════════════════════════════════════
              🤖  AI SALES ASSISTANT — DEMO
                    ร้าน: ร้านมายชอป
════════════════════════════════════════════════════════════

  ✓ Ollama connected  |  model: gemma3:4b
  ✓ Shop profile loaded  |  ร้านมายชอป

── Comment 1 ──────────────────────────────────────────────
  💬 ลูกค้า : ราคาเท่าไหร่คะ มีโปรไหม อยากได้สีดำ
  🏷  Intent  : [POTENTIAL_BUYER] (85% confidence)
  ✉  Reply   :
           สวัสดีค่ะ 😊 เสื้อผ้าของเรามีให้เลือกตั้งแต่ 199 บาท -
           1,290 บาทเลยค่ะ มีโปรซื้อ 2 ชิ้นลด 10% หรือ 3 ชิ้นลด 15%
           สีดำมีค่ะ! ทัก Inbox หรือ LINE: @myshop ได้เลยนะคะ 🥰

── Comment 5 ──────────────────────────────────────────────
  💬 ลูกค้า : คลิกรับเงินฟรี >> bit.ly/xxxx ด่วนก่อนหมดเขต!!!
  🏷  Intent  : [SPAM] (95% confidence)
  ⏭  Reply   : (ข้าม — SPAM)
════════════════════════════════════════════════════════════
  ✅ Demo complete!
════════════════════════════════════════════════════════════
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | ตรวจสอบ Ollama + model |
| `GET` | `/webhook` | Facebook webhook verification |
| `POST` | `/webhook` | Facebook comment events |
| `POST` | `/webhook/line` | LINE bot events |
| `POST` | `/process/comment` | N8N → process single comment |
| `POST` | `/process/batch` | N8N → process batch comments |

ดู interactive docs ที่ `http://localhost:8000/docs`

---

## 🔒 ทำไมต้องใช้ Local LLM?

| | Cloud AI (ChatGPT/Claude API) | AI Sales Assistant (Local) |
|---|---|---|
| **Privacy** | ❌ ข้อมูลลูกค้าไปอยู่บน Server ต่างประเทศ | ✅ ข้อมูลอยู่บนเครื่องคุณ 100% |
| **PDPA** | ⚠️ ต้องขอ consent ก่อนส่งข้อมูล | ✅ ไม่มีปัญหา ข้อมูลไม่ออก |
| **ค่าใช้จ่าย** | ❌ จ่ายต่อ token อาจหลักพัน฿/เดือน | ✅ ฟรี หลังติดตั้งครั้งแรก |
| **Internet** | ❌ ต้องการ Internet ตลอดเวลา | ✅ ทำงาน Offline ได้ |

---

## 🗺️ Changelog

| Version | สิ่งที่ทำ |
|---------|---------|
| **v1.0** | CLI pipeline: Analyzer + Generator + Ollama |
| **v2.0** | Streamlit Dashboard (approval UI + analytics) |
| **v3.0** | Multi-channel (Facebook, LINE) + FastAPI + n8n + Docker |

### Roadmap — V4

- [ ] **📊 Analytics Dashboard** — Conversion rate, สินค้าที่ถูกถามมากสุด
- [ ] **⚡ Auto-Reply Mode** — ส่งคำตอบอัตโนมัติ (bypass approval) สำหรับ SPAM/simple intents
- [ ] **🛒 TikTok Shop** — รองรับ TikTok comment webhook
- [ ] **🔔 Line Notify Alerts** — แจ้งเตือนเมื่อมีคอมเมนต์รอ approval
- [ ] **🌐 Multi-Language** — รองรับภาษาอังกฤษในคำตอบ

---

## 📄 License

MIT License — ใช้งานได้ฟรี แก้ไข และนำไปขายต่อได้

---

<div align="center">

Built with ❤️ for Thai Online Sellers

Powered by [Ollama](https://ollama.com) + [Gemma 3](https://ollama.com/library/gemma3) + [n8n](https://n8n.io) + [FastAPI](https://fastapi.tiangolo.com)

</div>
