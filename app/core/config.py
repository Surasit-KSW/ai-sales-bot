"""
Centralised configuration for the AI Sales Assistant.

Two layers of configuration:
  1. Config (this file)  — AI/model settings (Ollama URL, model name, temperature)
  2. ShopProfile (shop_profile.yaml) — business data (what to say in replies)

Keeping them separate lets shop owners update their product info and tone
without touching any technical settings.
"""

import requests
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

INPUT_FILE = DATA_DIR / "input_comments.txt"
OUTPUT_FILE = DATA_DIR / "processed_results.json"


# ---------------------------------------------------------------------------
# AI / Model Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Config:
    # --- Ollama connection ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    request_timeout_seconds: int = 300       # gemma4:e4b (9.6 GB) ต้องการเวลามากกว่า gemma3:4b

    # --- Processing ---
    max_retries: int = 2
    temperature: float = 0.7                 # 0.0 = robotic, 1.0 = very creative

    # -----------------------------------------------------------------------
    # Prompt Templates
    #
    # These are TEMPLATES — {shop_context}, {style_instructions}, {comment}
    # etc. are filled in at runtime by the analyzer/generator services.
    #
    # Notice: prompts no longer contain hardcoded shop info.
    # All business data comes from ShopProfile (shop_profile.yaml).
    # -----------------------------------------------------------------------

    # --- Intent Classifier System Prompt ---
    # Kept in English: small/medium models follow English instructions more
    # reliably than Thai for structured tasks like JSON output.
    analyzer_system_prompt: str = (
        "You are a JSON-only intent classifier for a Thai e-commerce shop. \n"
        "Shop context (use this to understand what products are being asked about):\n"
        "{shop_context}\n\n"
        "You MUST respond with valid JSON only — no explanation, no markdown fences.\n"
        "The 'intent' field MUST be exactly one of: "
        "POTENTIAL_BUYER, GENERAL_INQUIRY, SPAM, COMPLAINT"
    )

    # --- Intent Classifier User Prompt ---
    analyzer_user_prompt_template: str = (
        "Classify this Thai customer comment.\n\n"
        "Comment: \"{comment}\"\n\n"
        "Classification rules:\n"
        "- POTENTIAL_BUYER : asks price, stock, size, color, shipping cost, bulk deal, "
        "or expresses intent to buy\n"
        "- GENERAL_INQUIRY : asks about specs, material, warranty, reviews — "
        "curious but no clear buying signal\n"
        "- COMPLAINT       : unhappy, reports damaged/wrong item, requests refund "
        "or late delivery\n"
        "- SPAM            : promotional links, unrelated ads, bot content\n\n"
        "Respond with ONLY this JSON (replace values, keep keys in English):\n"
        "{{\n"
        '  "intent": "ONE_OF: POTENTIAL_BUYER, GENERAL_INQUIRY, SPAM, COMPLAINT",\n'
        '  "confidence": 0.0,\n'
        '  "key_signals": ["signal1"],\n'
        '  "sentiment": "ONE_OF: positive, neutral, negative"\n'
        "}}\n\n"
        "JSON only:"
    )

    # --- Reply Generator System Prompt ---
    # Thai prompt here because the OUTPUT is Thai — models follow language
    # style instructions better when written in the target language.
    generator_system_prompt: str = (
        "คุณเป็น AI พนักงานขายออนไลน์ของร้านนี้:\n"
        "{shop_context}\n\n"
        "กฎการตอบ:\n"
        "- {style_instructions}\n"
        "- ตรวจสอบ FAQ ในข้อมูลร้านก่อนเสมอ ถ้าคำถามตรงกับ FAQ ให้ตอบตาม FAQ นั้นทันที\n"
        "- ถ้าลูกค้าถามหรือสนใจโปรโมชั่น ให้ดึงโปรโมชั่นที่เกี่ยวข้องมาแจ้งด้วย\n"
        "- ถ้าลูกค้าถามเรื่องนโยบาย (คืน/เปลี่ยน/ชำระ/ส่ง) ให้ตอบตามนโยบายในข้อมูลร้านเท่านั้น\n"
        "- ตอบตรงประเด็นที่ลูกค้าถามก่อนเสมอ อย่าออกนอกเรื่อง\n"
        "- ตอบกระชับ 2-3 ประโยค ไม่ยืดเยื้อ\n"
        "- ทุกข้อความต้องจบด้วย call-to-action ที่ชัดเจน เช่น บอกช่องทางสั่ง/ติดต่อ\n"
        "- ใช้ข้อมูลร้านที่ให้ไว้เท่านั้น ห้ามแต่งข้อมูลขึ้นมาเอง\n"
        "- ห้าม Hard-sell หรือกดดันลูกค้า\n"
        "- ถ้าไม่รู้คำตอบ ให้บอกว่าจะตรวจสอบและแจ้งกลับทาง LINE ที่ระบุไว้"
    )

    # --- Reply Generator User Prompt ---
    generator_user_prompt_template: str = (
        "ความคิดเห็นของลูกค้า: \"{comment}\"\n"
        "ประเภท: {intent} | อารมณ์: {sentiment}\n\n"
        "แนวทางการตอบ:\n"
        "- POTENTIAL_BUYER : (1) ยืนยันราคา/โปรที่ถาม (2) เสนอจุดเด่นสั้นๆ (3) บอกช่องทางสั่งซื้อ\n"
        "- GENERAL_INQUIRY : (1) ตอบคำถามโดยตรงจากข้อมูลร้าน (2) เชิญให้ทักมาถามเพิ่ม\n"
        "- COMPLAINT       : (1) ขอโทษและแสดงความเข้าใจ (2) บอกวิธีแก้ไขพร้อมช่องทางติดต่อที่ชัดเจน\n"
        "- SPAM            : ตอบว่า SKIP เท่านั้น\n\n"
        "ข้อความตอบกลับ (ตอบตรงๆ ห้ามขึ้นต้นด้วย 'ข้อความตอบกลับ:' หรือคำนำอื่นๆ):"
    )


# ---------------------------------------------------------------------------
# Model Resolution — fallback if preferred model is unavailable
# ---------------------------------------------------------------------------
_PREFERRED_MODEL = "gemma4:e4b"
_FALLBACK_MODEL = "gemma3:4b"


def _resolve_model() -> str:
    """Return the preferred model if available in Ollama, else fall back."""
    try:
        resp = requests.get(
            f"{Config.ollama_base_url}/api/tags",
            timeout=5,
        )
        if resp.status_code == 200:
            available = [m["name"] for m in resp.json().get("models", [])]
            if _PREFERRED_MODEL in available:
                return _PREFERRED_MODEL
    except Exception:
        pass
    print(
        f"[WARNING] Model '{_PREFERRED_MODEL}' not found in Ollama. "
        f"Falling back to '{_FALLBACK_MODEL}'."
    )
    return _FALLBACK_MODEL


# Singleton — import this everywhere
settings = Config(ollama_model=_resolve_model())
