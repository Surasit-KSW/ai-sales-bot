"""
Shop Profile Loader

Loads shop_profile.yaml and converts it into:
  1. A ShopProfile dataclass (structured, type-safe)
  2. A plain-text context string injected into LLM prompts

Why a separate loader module?
  config.py holds AI/model settings (how to talk to Ollama).
  profile_loader.py holds business data (what to say).
  Keeping them separate means a shop owner can update their profile
  without touching any technical configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Expected location of the profile file — next to main.py
PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "shop_profile.yaml"


@dataclass
class ShopProfile:
    """
    Structured representation of the shop owner's business data.
    All fields have safe defaults so the app never crashes on a
    partially-filled profile.
    """

    # Basic info
    shop_name: str = "ร้านค้าออนไลน์"
    tagline: str = ""
    platform: str = ""

    # Products
    product_category: str = "สินค้าทั่วไป"
    product_description: str = ""
    price_range: str = ""
    highlights: List[str] = field(default_factory=list)
    promotions: str = ""

    # Contact
    order_channel: str = "ทักมาทาง Inbox"
    line_id: str = ""
    facebook: str = ""
    response_hours: str = ""

    # Shipping
    nationwide: bool = True
    shipping_fee: str = "ตามที่ตกลง"
    free_shipping_threshold: str = ""
    shipping_duration: str = ""
    cod_available: bool = False

    # Policy
    return_policy: str = ""
    warranty: str = ""
    payment: str = ""

    # Reply style
    tone: str = "เป็นกันเอง"
    closing_word: str = "ค่ะ"
    use_emoji: bool = True
    signature: str = ""

    def to_prompt_context(self) -> str:
        """
        Convert the profile into a concise paragraph for LLM system prompts.

        This is the key method — it turns structured YAML data into natural
        language that the model can use to craft accurate, specific replies.
        """
        highlights_text = ""
        if self.highlights:
            highlights_text = "จุดเด่น: " + " | ".join(self.highlights)

        shipping_text = f"ค่าส่ง {self.shipping_fee}"
        if self.free_shipping_threshold:
            shipping_text += f" ({self.free_shipping_threshold})"
        if self.shipping_duration:
            shipping_text += f" ใช้เวลา {self.shipping_duration}"
        if self.cod_available:
            shipping_text += " รับปลายทางได้"

        contact_text = self.order_channel
        if self.line_id:
            contact_text += f" LINE: {self.line_id}"

        parts = [
            f"ชื่อร้าน: {self.shop_name}",
            f"สินค้า: {self.product_category} — {self.product_description}".strip(" —"),
        ]
        if self.price_range:
            parts.append(f"ราคา: {self.price_range}")
        if highlights_text:
            parts.append(highlights_text)
        if self.promotions:
            parts.append(f"โปรโมชั่น: {self.promotions}")
        parts.append(f"สั่งซื้อ: {contact_text}")
        parts.append(f"จัดส่ง: {shipping_text}")
        if self.return_policy:
            parts.append(f"นโยบาย: {self.return_policy}")
        if self.payment:
            parts.append(f"ชำระเงิน: {self.payment}")

        return "\n".join(parts)

    def to_style_instructions(self) -> str:
        """
        Build style instructions for the generator system prompt.
        """
        emoji_instruction = "ใช้ emoji ได้บ้างพอเหมาะ" if self.use_emoji else "ไม่ใช้ emoji"
        sig = f"\n\nลงท้ายด้วย: {self.signature}" if self.signature else ""
        return (
            f"ใช้โทนการพูดแบบ{self.tone} "
            f"ลงท้ายด้วยคำว่า '{self.closing_word}' "
            f"{emoji_instruction}{sig}"
        )


def load_profile(path: Path = PROFILE_PATH) -> ShopProfile:
    """
    Load and parse shop_profile.yaml into a ShopProfile dataclass.

    Falls back to default values if:
      - File not found (first-time user hasn't created it yet)
      - YAML is malformed
      - Individual fields are missing

    Args:
        path: Path to the YAML profile file.

    Returns:
        ShopProfile instance (never raises — always returns something usable).
    """
    if not path.exists():
        logger.warning(
            "shop_profile.yaml not found at %s — using default profile. "
            "Copy shop_profile.yaml and fill in your shop details for better replies.",
            path,
        )
        return ShopProfile()

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # --- Extract each section with safe .get() fallbacks ---
        shop = data.get("shop", {})
        products = data.get("products", {})
        contact = data.get("contact", {})
        shipping = data.get("shipping", {})
        policy = data.get("policy", {})
        style = data.get("reply_style", {})

        profile = ShopProfile(
            # Basic
            shop_name=shop.get("name", "ร้านค้าออนไลน์"),
            tagline=shop.get("tagline", ""),
            platform=shop.get("platform", ""),
            # Products
            product_category=products.get("category", "สินค้าทั่วไป"),
            product_description=str(products.get("description", "")).strip(),
            price_range=products.get("price_range", ""),
            highlights=list(products.get("highlights", [])),
            promotions=products.get("promotions", ""),
            # Contact
            order_channel=contact.get("order_channel", "ทักมาทาง Inbox"),
            line_id=contact.get("line_id", ""),
            facebook=contact.get("facebook", ""),
            response_hours=contact.get("response_hours", ""),
            # Shipping
            nationwide=bool(shipping.get("nationwide", True)),
            shipping_fee=shipping.get("fee", "ตามที่ตกลง"),
            free_shipping_threshold=shipping.get("free_shipping_threshold", ""),
            shipping_duration=shipping.get("duration", ""),
            cod_available=bool(shipping.get("cod_available", False)),
            # Policy
            return_policy=policy.get("return_policy", ""),
            warranty=policy.get("warranty", ""),
            payment=policy.get("payment", ""),
            # Style
            tone=style.get("tone", "เป็นกันเอง"),
            closing_word=style.get("closing_word", "ค่ะ"),
            use_emoji=bool(style.get("use_emoji", True)),
            signature=style.get("signature", ""),
        )

        logger.info("Shop profile loaded: %s | %s", profile.shop_name, profile.product_category)
        return profile

    except yaml.YAMLError as exc:
        logger.error("Failed to parse shop_profile.yaml: %s — using defaults.", exc)
        return ShopProfile()
