<div align="center">

# 🤖 AI Sales Assistant
### ระบบ AI ตอบคอมเมนต์ลูกค้าอัตโนมัติ สำหรับร้านค้าออนไลน์ไทย

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge&logo=ollama)](https://ollama.com)
[![Gemma](https://img.shields.io/badge/Gemma_3-4B-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ollama.com/library/gemma3)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**ฟรี | Private | ทำงานบน Local | ไม่มีค่า API รายเดือน**

</div>

---

## 🎯 ปัญหาที่แก้ได้

ร้านค้าออนไลน์บน Facebook / TikTok Shop / LINE OA ได้รับคอมเมนต์หลายร้อยข้อความต่อวัน การตอบด้วยมือทุกข้อความ **ช้า ไม่สม่ำเสมอ และพลาดโอกาสขาย**

AI Sales Assistant อ่านทุกคอมเมนต์ → จำแนกประเภท → สร้างคำตอบภาษาไทยที่เหมาะสมกับร้านของคุณ

---

## ✨ ความสามารถหลัก

| Feature | รายละเอียด |
|---------|-----------|
| 🧠 **Intent Classification** | จำแนกเป็น 4 ประเภท: ผู้สนใจซื้อ / สอบถามทั่วไป / ร้องเรียน / Spam |
| ✍️ **Thai Reply Generation** | สร้างคำตอบภาษาไทยที่เป็นธรรมชาติ ตาม tone ร้านคุณ |
| 🏪 **Shop Profile** | แก้ไฟล์ `shop_profile.yaml` เพียงไฟล์เดียว ไม่ต้องแตะ code |
| 🔒 **100% Private** | รันบนเครื่องคุณ ข้อมูลลูกค้าไม่ออกไปไหน |
| 💸 **ฟรีตลอดชีพ** | ไม่มีค่า API ไม่มีรายเดือน |
| 🛡️ **Graceful Failure** | Ollama ดับ → ข้ามคอมเมนต์นั้น pipeline ไม่หยุด |

---

## 🚀 Demo

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

── Comment 2 ──────────────────────────────────────────────
  💬 ลูกค้า : ผ้าทำจากอะไรคะ แพ้ง่ายอยากรู้ก่อนสั่ง
  🏷  Intent  : [GENERAL_INQUIRY] (80% confidence)
  ✉  Reply   :
           สวัสดีค่ะ เสื้อผ้าของเราทำจากผ้าคอตตอนนุ่มใส่สบาย
           ระบายอากาศดีมากค่ะ มีให้เลือก 5 สี 4 ไซส์ (S/M/L/XL)
           สอบถามเพิ่มเติมได้ทาง LINE: @myshop ค่ะ 😊

── Comment 3 ──────────────────────────────────────────────
  💬 ลูกค้า : ซื้อ 3 ชิ้นได้ส่วนลดไหมครับ จะซื้อให้แม่กับน้องด้วย
  🏷  Intent  : [POTENTIAL_BUYER] (90% confidence)
  ✉  Reply   :
           สวัสดีค่ะ! ซื้อ 3 ชิ้นได้ลด 15% เลยนะคะ 😊
           เหมาะมากสำหรับซื้อให้ครอบครัวเลยค่ะ
           สั่งได้ทาง Inbox Facebook หรือ LINE: @myshop

── Comment 4 ──────────────────────────────────────────────
  💬 ลูกค้า : สั่งไป 5 วันแล้วยังไม่ได้ของเลยค่ะ ติดต่อยังไงคะ
  🏷  Intent  : [COMPLAINT] (90% confidence)
  ✉  Reply   :
           ขออภัยมากๆ นะคะ เข้าใจความกังวลค่ะ
           ทางร้านกำลังตรวจสอบสถานะพัสดุกับ Kerry/Flash ให้เลยค่ะ
           รบกวนส่งเลขพัสดุมาทาง Inbox เพื่อเร่งติดตามให้นะคะ 🙏

── Comment 5 ──────────────────────────────────────────────
  💬 ลูกค้า : คลิกรับเงินฟรี >> bit.ly/xxxx ด่วนก่อนหมดเขต!!!
  🏷  Intent  : [SPAM] (95% confidence)
  ⏭  Reply   : (ข้าม — SPAM)

════════════════════════════════════════════════════════════
  ✅ Demo complete!
════════════════════════════════════════════════════════════
```

---

## 📁 โครงสร้างโปรเจกต์

```
ai-sales-bot/
│
├── 📄 shop_profile.yaml        ← ✏️  แก้ตรงนี้อย่างเดียว! ข้อมูลร้านของคุณ
├── 📄 main.py                  ← รันกับไฟล์ข้อมูลจริง
├── 📄 demo.py                  ← รันเพื่อดู demo 5 ตัวอย่าง
│
├── 📂 app/
│   ├── 📂 core/
│   │   ├── config.py           ← ตั้งค่า AI (model, temperature, prompts)
│   │   ├── llm_client.py       ← Ollama wrapper (retry, error handling)
│   │   └── profile_loader.py   ← โหลด shop_profile.yaml → dataclass
│   │
│   ├── 📂 services/
│   │   ├── analyzer.py         ← จำแนก intent ของคอมเมนต์
│   │   └── generator.py        ← สร้างคำตอบภาษาไทย
│   │
│   └── 📂 utils/
│       └── logger.py           ← Structured logging (console + file)
│
└── 📂 data/
    └── input_comments.txt      ← ใส่คอมเมนต์ที่นี่ (1 บรรทัด = 1 คอมเมนต์)
```

---

## 🛠️ การติดตั้ง

### 1. Requirements
- Python 3.11+
- [Ollama](https://ollama.com) (ดาวน์โหลดและติดตั้ง)

### 2. Clone & Install

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

### 3. ดาวน์โหลด AI Model

```bash
ollama pull gemma3:4b
```

> **หมายเหตุ:** ต้องการ RAM ~6GB | ดาวน์โหลดครั้งแรก ~3.3GB

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

### รัน Demo (แนะนำสำหรับทดสอบครั้งแรก)

```bash
ollama serve          # เปิด Ollama (Terminal แรก)
python demo.py        # รัน demo (Terminal ที่สอง)
```

### รันกับข้อมูลจริง

```bash
# 1. ใส่คอมเมนต์ลูกค้าใน data/input_comments.txt (1 บรรทัด = 1 คอมเมนต์)
# 2. รัน
python main.py

# ผลลัพธ์จะอยู่ที่ data/processed_results.json
```

### ตัวอย่าง Output (JSON)

```json
{
  "id": 1,
  "comment": "ราคาเท่าไหร่คะ มีโปรไหม",
  "intent": "POTENTIAL_BUYER",
  "confidence": 0.85,
  "sentiment": "positive",
  "key_signals": ["price_inquiry", "promotion_interest"],
  "reply": "สวัสดีค่ะ 😊 เสื้อผ้าของเรามีให้เลือกตั้งแต่ 199 บาท...",
  "was_skipped": false,
  "processed_at": "2026-04-10T17:15:28"
}
```

---

## 🔒 ทำไมต้องใช้ Local LLM?

| | Cloud AI (ChatGPT/Claude API) | AI Sales Assistant (Local) |
|---|---|---|
| **Privacy** | ❌ ข้อมูลลูกค้าไปอยู่บน Server ต่างประเทศ | ✅ ข้อมูลอยู่บนเครื่องคุณ 100% |
| **PDPA** | ⚠️ ต้องขอ consent ก่อนส่งข้อมูล | ✅ ไม่มีปัญหา ข้อมูลไม่ออก |
| **ค่าใช้จ่าย** | ❌ จ่ายต่อ token อาจหลักพัน฿/เดือน | ✅ ฟรี หลังติดตั้งครั้งแรก |
| **Internet** | ❌ ต้องการ Internet ตลอดเวลา | ✅ ทำงาน Offline ได้ |

---

## 🗺️ Roadmap — V2

สิ่งที่จะเพิ่มในเวอร์ชันถัดไป:

- [ ] **🖥️ Web UI** — Dashboard ด้วย Streamlit: วาง-คอมเมนต์ เห็น-ผล อนุมัติ-ก่อนส่ง
- [ ] **🗄️ Database** — บันทึกประวัติทุก conversation ด้วย SQLite
- [ ] **📱 Auto-Post** — โพสต์ตอบกลับ Facebook / LINE OA อัตโนมัติผ่าน API
- [ ] **📊 Analytics** — Dashboard แสดง: สินค้าไหนถูกถามมากสุด, Conversion rate
- [ ] **⚡ Batch Mode** — ประมวลผลหลายร้อยคอมเมนต์พร้อมกัน

---

## 📄 License

MIT License — ใช้งานได้ฟรี แก้ไข และนำไปขายต่อได้

---

<div align="center">

Built with ❤️ for Thai Online Sellers | Powered by [Ollama](https://ollama.com) + [Gemma 3](https://ollama.com/library/gemma3)

</div>
