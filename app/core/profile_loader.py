"""
Shop Profile Loader — Schema v2

Loads shop_profile.yaml and converts it into:
  1. Typed dataclasses (structured, safe)
  2. A plain-text context string injected into LLM prompts

Schema v2 adds: product categories with bestsellers/variants,
structured promotions, detailed policies, FAQ with Q&A pairs,
rich contact info, emoji density, personality, escalation rules.

All fields have safe defaults — the app never crashes on a partial profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

from app.utils.logger import get_logger

logger = get_logger(__name__)

PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "shop_profile.yaml"


# ---------------------------------------------------------------------------
# Sub-dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Bestseller:
    name: str = ""
    price: str = ""
    highlight: str = ""


@dataclass
class ProductVariants:
    colors: List[str] = field(default_factory=list)
    sizes: List[str] = field(default_factory=list)
    other: List[str] = field(default_factory=list)


@dataclass
class ProductCategory:
    name: str = ""
    description: str = ""
    price_range: str = ""
    bestsellers: List[Bestseller] = field(default_factory=list)
    variants: ProductVariants = field(default_factory=ProductVariants)


@dataclass
class CurrentPromotion:
    title: str = ""
    detail: str = ""
    condition: str = ""
    expiry: str = "ongoing"


@dataclass
class ShippingPromo:
    free_threshold: str = ""
    carriers: List[str] = field(default_factory=list)
    domestic_days: str = ""
    cod_available: bool = True


@dataclass
class Promotions:
    current: List[CurrentPromotion] = field(default_factory=list)
    loyalty_detail: str = ""
    shipping: ShippingPromo = field(default_factory=ShippingPromo)


@dataclass
class Policies:
    return_policy: str = ""
    exchange: str = ""
    warranty: str = ""
    payment_methods: List[str] = field(default_factory=list)
    authenticity: str = ""


@dataclass
class FAQ:
    question: str = ""
    answer: str = ""


@dataclass
class Contact:
    line_id: str = ""
    facebook: str = ""
    phone: str = ""
    email: str = ""
    hours: str = ""
    response_time: str = ""
    order_channels: List[str] = field(default_factory=list)


@dataclass
class ReplyStyle:
    tone: str = "เป็นกันเอง"
    closing_word: str = "ค่ะ"
    use_emoji: bool = True
    emoji_density: str = "medium"   # low / medium / high
    personality: str = ""
    forbidden_words: List[str] = field(default_factory=list)
    always_include: List[str] = field(default_factory=list)


@dataclass
class Escalation:
    trigger_keywords: List[str] = field(default_factory=list)
    action: str = "flag_for_human"
    human_notify: bool = True


# ---------------------------------------------------------------------------
# Main ShopProfile dataclass
# ---------------------------------------------------------------------------

@dataclass
class ShopProfile:
    """
    Structured representation of the shop owner's business data.
    All fields have safe defaults — app never crashes on a partial profile.
    """

    # Basic info
    shop_name: str = "ร้านค้าออนไลน์"
    tagline: str = ""
    description: str = ""
    established: str = ""
    trust_signals: List[str] = field(default_factory=list)
    platform: str = ""   # kept for UI compatibility (streamlit sidebar)

    # Products
    categories: List[ProductCategory] = field(default_factory=list)
    materials: str = ""
    origin: str = ""
    quality_cert: str = ""

    # Promotions
    promotions: Promotions = field(default_factory=Promotions)

    # Policies
    policies: Policies = field(default_factory=Policies)

    # FAQ
    faqs: List[FAQ] = field(default_factory=list)

    # Contact
    contact: Contact = field(default_factory=Contact)

    # Reply style
    style: ReplyStyle = field(default_factory=ReplyStyle)

    # Escalation
    escalation: Escalation = field(default_factory=Escalation)

    # -----------------------------------------------------------------------
    # Prompt helpers
    # -----------------------------------------------------------------------

    def to_prompt_context(self) -> str:
        """
        Convert the profile into a natural-language string for LLM system prompts.

        Includes: shop info, trust signals, categories with bestsellers/variants,
        materials, all promotions, shipping, policies, contact, and FAQ.
        The FAQ block is prefixed with an explicit instruction so the model
        uses it as a primary reference before reasoning from scratch.
        """
        parts: List[str] = [f"ชื่อร้าน: {self.shop_name}"]

        if self.tagline:
            parts.append(f"สโลแกน: {self.tagline}")
        if self.description:
            parts.append(f"เกี่ยวกับร้าน: {self.description.strip()}")
        if self.trust_signals:
            parts.append("ความน่าเชื่อถือ: " + " | ".join(self.trust_signals))

        # --- Products ---
        if self.categories:
            cat_lines = []
            for cat in self.categories:
                line = f"  [{cat.name}]"
                if cat.price_range:
                    line += f" ราคา {cat.price_range}"
                if cat.bestsellers:
                    bs = ", ".join(
                        f"{b.name} {b.price}" + (f" ({b.highlight})" if b.highlight else "")
                        for b in cat.bestsellers
                    )
                    line += f"\n    สินค้าขายดี: {bs}"
                if cat.variants.colors:
                    line += f"\n    สี: {', '.join(cat.variants.colors)}"
                if cat.variants.sizes:
                    line += f"\n    ไซส์: {', '.join(cat.variants.sizes)}"
                cat_lines.append(line)
            parts.append("สินค้า:\n" + "\n".join(cat_lines))

        if self.materials:
            parts.append(f"วัสดุ: {self.materials}")
        if self.origin:
            parts.append(f"แหล่งผลิต: {self.origin}")
        if self.quality_cert:
            parts.append(f"มาตรฐาน: {self.quality_cert}")

        # --- Promotions ---
        if self.promotions.current:
            promo_lines = []
            for p in self.promotions.current:
                line = f"  • {p.title}: {p.detail}"
                if p.condition:
                    line += f" (เงื่อนไข: {p.condition})"
                promo_lines.append(line)
            parts.append("โปรโมชั่นปัจจุบัน:\n" + "\n".join(promo_lines))
        if self.promotions.loyalty_detail:
            parts.append(f"โปรสมาชิก: {self.promotions.loyalty_detail}")

        # --- Shipping ---
        s = self.promotions.shipping
        ship_parts = []
        if s.free_threshold:
            ship_parts.append(s.free_threshold)
        if s.carriers:
            ship_parts.append("ขนส่ง: " + ", ".join(s.carriers))
        if s.domestic_days:
            ship_parts.append(f"ใช้เวลา {s.domestic_days}")
        if s.cod_available:
            ship_parts.append("รับปลายทางได้")
        if ship_parts:
            parts.append("จัดส่ง: " + " | ".join(ship_parts))

        # --- Policies ---
        pol = self.policies
        pol_lines = []
        if pol.return_policy:
            pol_lines.append(f"คืนสินค้า: {pol.return_policy}")
        if pol.exchange:
            pol_lines.append(f"เปลี่ยนสินค้า: {pol.exchange}")
        if pol.warranty:
            pol_lines.append(f"ประกัน: {pol.warranty}")
        if pol.payment_methods:
            pol_lines.append("ชำระเงิน: " + ", ".join(pol.payment_methods))
        if pol.authenticity:
            pol_lines.append(f"ความแท้: {pol.authenticity}")
        if pol_lines:
            parts.append("นโยบาย:\n" + "\n".join(f"  {p}" for p in pol_lines))

        # --- Contact ---
        c = self.contact
        cnt_parts = []
        if c.order_channels:
            cnt_parts.append("สั่งซื้อผ่าน: " + ", ".join(c.order_channels))
        if c.line_id:
            cnt_parts.append(f"LINE: {c.line_id}")
        if c.facebook:
            cnt_parts.append(f"Facebook: {c.facebook}")
        if c.hours:
            cnt_parts.append(f"เวลาเปิด: {c.hours}")
        if c.response_time:
            cnt_parts.append(f"ตอบกลับ: {c.response_time}")
        if cnt_parts:
            parts.append("ติดต่อ: " + " | ".join(cnt_parts))

        # --- FAQ (must come last so the model sees it as primary reference) ---
        if self.faqs:
            faq_lines = [
                f"  Q: {f.question}\n  A: {f.answer}"
                for f in self.faqs
            ]
            parts.append(
                "FAQ — ตอบตาม FAQ นี้ก่อนถ้าคำถามตรงกัน:\n" + "\n".join(faq_lines)
            )

        return "\n".join(parts)

    def to_style_instructions(self) -> str:
        """Build style instructions for the generator system prompt."""
        s = self.style
        emoji_map = {
            "low":  "ใช้ emoji น้อยๆ 1-2 ตัวต่อข้อความ",
            "high": "ใช้ emoji เยอะสีสัน 3-5 ตัวต่อข้อความ",
        }
        emoji_instr = (
            emoji_map.get(s.emoji_density, "ใช้ emoji พอเหมาะ 2-3 ตัวต่อข้อความ")
            if s.use_emoji else "ไม่ใช้ emoji"
        )

        parts = [
            f"โทนการพูด: {s.tone}",
            f"ลงท้ายด้วย '{s.closing_word}'",
            emoji_instr,
        ]
        if s.personality:
            parts.append(f"บุคลิก: {s.personality.strip()}")
        if s.forbidden_words:
            parts.append("ห้ามใช้คำ: " + ", ".join(f'"{w}"' for w in s.forbidden_words))
        if s.always_include:
            parts.append("ต้องระบุเสมอ: " + "; ".join(s.always_include))

        return " | ".join(parts)

    def is_escalation_trigger(self, text: str) -> bool:
        """Return True if text contains any escalation trigger keyword."""
        lower_text = text.lower()
        return any(kw.lower() in lower_text for kw in self.escalation.trigger_keywords)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_profile(path: Path = PROFILE_PATH) -> ShopProfile:
    """
    Load and parse shop_profile.yaml into a ShopProfile dataclass.

    Falls back to default values if:
      - File not found
      - YAML is malformed
      - Individual fields are missing

    Never raises — always returns something usable.
    """
    if not path.exists():
        logger.warning(
            "shop_profile.yaml not found at %s — using default profile. "
            "Fill in shop_profile.yaml for accurate AI replies.",
            path,
        )
        return ShopProfile()

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        shop_d       = data.get("shop", {})
        products_d   = data.get("products", {})
        promos_d     = data.get("promotions", {})
        policies_d   = data.get("policies", {})
        faq_d        = data.get("faq", [])
        contact_d    = data.get("contact", {})
        style_d      = data.get("reply_style", {})
        escalation_d = data.get("escalation", {})

        # --- Categories ---
        categories: List[ProductCategory] = []
        for cat in products_d.get("categories", []):
            bestsellers = [
                Bestseller(
                    name=b.get("name", ""),
                    price=b.get("price", ""),
                    highlight=b.get("highlight", ""),
                )
                for b in cat.get("bestsellers", [])
            ]
            v = cat.get("variants", {})
            variants = ProductVariants(
                colors=list(v.get("colors", [])),
                sizes=list(v.get("sizes", [])),
                other=list(v.get("other", [])),
            )
            categories.append(ProductCategory(
                name=cat.get("name", ""),
                description=cat.get("description", ""),
                price_range=cat.get("price_range", ""),
                bestsellers=bestsellers,
                variants=variants,
            ))

        # --- Promotions ---
        current_promos = [
            CurrentPromotion(
                title=p.get("title", ""),
                detail=p.get("detail", ""),
                condition=p.get("condition", ""),
                expiry=p.get("expiry", "ongoing"),
            )
            for p in promos_d.get("current", [])
        ]
        ship_d = promos_d.get("shipping", {})
        shipping_promo = ShippingPromo(
            free_threshold=ship_d.get("free_threshold", ""),
            carriers=list(ship_d.get("carriers", [])),
            domestic_days=ship_d.get("domestic_days", ""),
            cod_available=bool(ship_d.get("cod_available", True)),
        )
        loyalty = promos_d.get("loyalty", {})
        promotions = Promotions(
            current=current_promos,
            loyalty_detail=loyalty.get("detail", "") if isinstance(loyalty, dict) else "",
            shipping=shipping_promo,
        )

        # --- Policies ---
        policies = Policies(
            return_policy=policies_d.get("return", ""),
            exchange=policies_d.get("exchange", ""),
            warranty=policies_d.get("warranty", ""),
            payment_methods=list(policies_d.get("payment_methods", [])),
            authenticity=policies_d.get("authenticity", ""),
        )

        # --- FAQ (supports both new {question, answer} dicts and legacy plain strings) ---
        faqs: List[FAQ] = []
        for item in (faq_d or []):
            if isinstance(item, dict):
                faqs.append(FAQ(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                ))
            elif isinstance(item, str) and item.strip():
                faqs.append(FAQ(question=item, answer=""))

        # --- Contact ---
        contact = Contact(
            line_id=contact_d.get("line_id", ""),
            facebook=contact_d.get("facebook", ""),
            phone=contact_d.get("phone", ""),
            email=contact_d.get("email", ""),
            hours=contact_d.get("hours", ""),
            response_time=contact_d.get("response_time", ""),
            order_channels=list(contact_d.get("order_channels", [])),
        )

        # --- Style ---
        style = ReplyStyle(
            tone=style_d.get("tone", "เป็นกันเอง"),
            closing_word=style_d.get("closing_word", "ค่ะ"),
            use_emoji=bool(style_d.get("use_emoji", True)),
            emoji_density=style_d.get("emoji_density", "medium"),
            personality=str(style_d.get("personality", "")).strip(),
            forbidden_words=list(style_d.get("forbidden_words", [])),
            always_include=list(style_d.get("always_include", [])),
        )

        # --- Escalation ---
        escalation = Escalation(
            trigger_keywords=list(escalation_d.get("trigger_keywords", [])),
            action=escalation_d.get("action", "flag_for_human"),
            human_notify=bool(escalation_d.get("human_notify", True)),
        )

        profile = ShopProfile(
            shop_name=shop_d.get("name", "ร้านค้าออนไลน์"),
            tagline=shop_d.get("tagline", ""),
            description=str(shop_d.get("description", "")).strip(),
            established=str(shop_d.get("established", "")),
            trust_signals=list(shop_d.get("trust_signals", [])),
            platform=shop_d.get("platform", ""),   # legacy field
            categories=categories,
            materials=products_d.get("materials", ""),
            origin=products_d.get("origin", ""),
            quality_cert=products_d.get("quality_cert", ""),
            promotions=promotions,
            policies=policies,
            faqs=faqs,
            contact=contact,
            style=style,
            escalation=escalation,
        )

        logger.info(
            "Shop profile loaded: %s | %d categories | %d promos | %d FAQs",
            profile.shop_name,
            len(profile.categories),
            len(profile.promotions.current),
            len(profile.faqs),
        )
        return profile

    except yaml.YAMLError as exc:
        logger.error("Failed to parse shop_profile.yaml: %s — using defaults.", exc)
        return ShopProfile()
