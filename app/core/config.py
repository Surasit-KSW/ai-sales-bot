"""
Centralised configuration for the AI Sales Assistant.

Two layers of configuration:
  1. Config (this file)  — AI/model settings (Ollama URL, model name, temperature)
  2. ShopProfile (shop_profile.yaml) — business data (what to say in replies)

Keeping them separate lets shop owners update their product info and tone
without touching any technical settings.
"""

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
    ollama_model: str = "gemma3:4b"          # upgrade to gemma3:12b for best quality
    request_timeout_seconds: int = 90        # 4b model is slower than 2b — give it time

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
        "- ตอบให้กระชับ ไม่เกิน 3-4 ประโยค\n"
        "- ห้าม Hard-sell หรือกดดันลูกค้า\n"
        "- ใช้ข้อมูลร้านที่ให้ไว้ข้างต้นในการตอบ อย่าแต่งข้อมูลขึ้นมาเอง\n"
        "- ถ้าไม่รู้คำตอบ ให้บอกลูกค้าว่าจะตรวจสอบและแจ้งกลับ"
    )

    # --- Reply Generator User Prompt ---
    generator_user_prompt_template: str = (
        "สร้างข้อความตอบกลับสำหรับความคิดเห็นนี้:\n\n"
        "ความคิดเห็น: \"{comment}\"\n"
        "ประเภท: {intent}\n"
        "อารมณ์ลูกค้า: {sentiment}\n\n"
        "แนวทางตามประเภท:\n"
        "- POTENTIAL_BUYER : ให้ข้อมูลสินค้า/ราคา/โปรโมชั่น + บอกช่องทางสั่งซื้อ\n"
        "- GENERAL_INQUIRY : ตอบคำถามตรงๆ จากข้อมูลร้าน + เชิญชวนให้ถามเพิ่ม\n"
        "- COMPLAINT       : ขอโทษ + แสดงความเข้าใจ + บอกวิธีแก้ไขที่ชัดเจน\n"
        "- SPAM            : ตอบว่า SKIP เท่านั้น\n\n"
        "ข้อความตอบกลับ:"
    )


# Singleton — import this everywhere
settings = Config()
