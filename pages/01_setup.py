"""
pages/01_setup.py — Onboarding Wizard (5 Steps)

ตั้งค่าร้านโดยไม่ต้องแตะ YAML โดยตรง

Persistence layers:
  1. st.session_state    — ภายใน browser session เดียว
  2. data/wizard_draft.json — รอดจากปิด/เปิดหน้าใหม่
  3. shop_profile.yaml   — บันทึกจริง (เฉพาะเมื่อกด "บันทึกและเริ่มใช้งาน")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st
import yaml
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

st.set_page_config(
    page_title="ตั้งค่าร้าน — AI Sales Bot",
    page_icon="🏪",
    layout="centered",
)

ROOT = Path(__file__).resolve().parent.parent
DRAFT_FILE = ROOT / "data" / "wizard_draft.json"
PROFILE_FILE = ROOT / "shop_profile.yaml"

# ── Options ────────────────────────────────────────────────────────────────────
PRODUCT_TYPES = [
    "เสื้อผ้า", "อาหารและเครื่องดื่ม", "ของใช้ในบ้าน", "ความงามและสกินแคร์",
    "เครื่องประดับ", "อิเล็กทรอนิกส์", "สัตว์เลี้ยง", "อื่นๆ (ระบุเอง)",
]
CARRIER_OPTIONS = ["Kerry", "Flash", "Thailand Post", "J&T Express", "DHL", "นิ่มซี่เส็ง", "SCG Express"]
PAYMENT_OPTIONS = ["โอนเงิน", "QR Code", "บัตรเครดิต", "COD (ปลายทาง)", "TrueMoney Wallet", "PromptPay"]
TONE_OPTIONS = ["สุภาพมาก", "เป็นกันเอง", "ทางการ"]
TONE_EXAMPLES = {
    "สุภาพมาก": "สวัสดีครับ/ค่ะ ขอบพระคุณที่ให้ความสนใจนะครับ/ค่ะ ยินดีให้บริการเสมอเลยนะครับ/ค่ะ 🙏",
    "เป็นกันเอง": "สวัสดีค่ะ ยินดีช่วยเลยนะคะ 😊 มีอะไรสงสัยถามได้เลยเนอะ!",
    "ทางการ": "เรียนลูกค้า ทางร้านขอแจ้งข้อมูลดังนี้ กรุณาตรวจสอบรายละเอียดและยืนยันการสั่งซื้อ",
}
CLOSING_WORDS = ["ครับ", "ค่ะ"]
EMOJI_DENSITY_OPTIONS = ["low", "medium", "high"]
EMOJI_DENSITY_LABELS = {"low": "น้อย (1-2 ตัว)", "medium": "พอเหมาะ (2-3 ตัว)", "high": "เยอะ (3-5 ตัว)"}

STEP_LABELS = [
    "1️⃣ ข้อมูลร้าน",
    "2️⃣ สินค้า",
    "3️⃣ โปรโมชั่น",
    "4️⃣ FAQ",
    "5️⃣ สไตล์+ทดสอบ",
]
TOTAL_STEPS = 5

# ── Category field names (for key-shifting on delete) ─────────────────────────
CAT_FIELDS = ["name", "description", "price_range", "bestsellers_text", "colors", "sizes"]
PROMO_FIELDS = ["title", "detail", "condition", "expiry"]
FAQ_FIELDS = ["q", "a"]

# Default values
DEFAULTS: dict = {
    "setup_step": 1,
    # Step 1
    "setup_shop_name": "",
    "setup_shop_tagline": "",
    "setup_shop_description": "",
    "setup_shop_established": "",
    "setup_trust_signals_text": "",
    # Step 2
    "setup_product_type": "เสื้อผ้า",
    "setup_product_type_custom": "",
    "setup_cat_count": 0,
    "setup_materials": "",
    "setup_origin": "",
    "setup_quality_cert": "",
    # Step 3
    "setup_promo_count": 0,
    "setup_free_shipping": "",
    "setup_carriers": [],
    "setup_shipping_days": "",
    "setup_cod": True,
    "setup_return_policy": "",
    "setup_exchange_policy": "",
    "setup_warranty": "",
    "setup_payment_methods": [],
    # Step 4
    "setup_faq_count": 0,
    "setup_escalation_text": "",
    "setup_line_id": "",
    "setup_facebook": "",
    "setup_phone": "",
    "setup_hours": "",
    "setup_response_time": "",
    # Step 5
    "setup_tone": "เป็นกันเอง",
    "setup_closing_word": "ค่ะ",
    "setup_use_emoji": True,
    "setup_emoji_density": "medium",
    "setup_personality": "",
    "setup_forbidden_words_text": "",
    "setup_always_include_text": "",
    "setup_test_comment": "",
    "setup_test_reply": "",
    "setup_saved": False,
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .step-bar { display:flex; gap:6px; margin-bottom:24px; }
    .step-item {
        flex:1; text-align:center; padding:8px 2px;
        border-radius:8px; font-size:0.78rem; font-weight:600;
        line-height:1.3;
    }
    .step-active  { background:#1f77b4; color:white; }
    .step-done    { background:#d4edda; color:#155724; }
    .step-pending { background:#f0f0f0; color:#aaa; }

    .reply-card {
        background:#f0f7ff;
        border-left:4px solid #1f77b4;
        padding:14px 18px;
        border-radius:0 10px 10px 0;
        font-size:1rem; line-height:1.7;
        white-space:pre-wrap;
        margin:10px 0;
    }
    .tone-example {
        background:#fffbf0;
        border-left:3px solid #f0ad4e;
        padding:8px 14px;
        border-radius:0 8px 8px 0;
        font-size:0.9rem;
        margin:6px 0 12px 0;
        color:#555;
    }
    .section-title {
        font-size:0.95rem; font-weight:700;
        color:#1f77b4; margin:16px 0 8px 0;
        border-bottom:2px solid #e0edf8;
        padding-bottom:4px;
    }
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# State helpers
# ══════════════════════════════════════════════════════════════════════════════

def _guess_product_type(text: str) -> str:
    for t in PRODUCT_TYPES:
        if t in text or text in t:
            return t
    return "อื่นๆ (ระบุเอง)"


def _load_from_profile_yaml() -> dict:
    """Map existing shop_profile.yaml → wizard session_state keys."""
    if not PROFILE_FILE.exists():
        return {}
    try:
        raw = yaml.safe_load(PROFILE_FILE.read_text(encoding="utf-8")) or {}
        shop     = raw.get("shop", {})
        products = raw.get("products", {})
        promos   = raw.get("promotions", {})
        policies = raw.get("policies", {})
        faq_list = raw.get("faq", [])
        contact  = raw.get("contact", {})
        style    = raw.get("reply_style", {})
        escl     = raw.get("escalation", {})

        result: dict = {
            "setup_shop_name":          shop.get("name", ""),
            "setup_shop_tagline":       shop.get("tagline", ""),
            "setup_shop_description":   str(shop.get("description", "")).strip(),
            "setup_shop_established":   str(shop.get("established", "")),
            "setup_trust_signals_text": "\n".join(shop.get("trust_signals", [])),
            "setup_materials":          products.get("materials", ""),
            "setup_origin":             products.get("origin", ""),
            "setup_quality_cert":       products.get("quality_cert", ""),
            "setup_free_shipping":      promos.get("shipping", {}).get("free_threshold", ""),
            "setup_carriers":           [c for c in promos.get("shipping", {}).get("carriers", [])
                                         if c in CARRIER_OPTIONS],
            "setup_shipping_days":      promos.get("shipping", {}).get("domestic_days", ""),
            "setup_cod":                bool(promos.get("shipping", {}).get("cod_available", True)),
            "setup_return_policy":      policies.get("return", ""),
            "setup_exchange_policy":    policies.get("exchange", ""),
            "setup_warranty":           policies.get("warranty", ""),
            "setup_payment_methods":    [p for p in policies.get("payment_methods", [])
                                         if p in PAYMENT_OPTIONS],
            "setup_escalation_text":    "\n".join(escl.get("trigger_keywords", [])),
            "setup_line_id":            contact.get("line_id", ""),
            "setup_facebook":           contact.get("facebook", ""),
            "setup_phone":              contact.get("phone", ""),
            "setup_hours":              contact.get("hours", ""),
            "setup_response_time":      contact.get("response_time", ""),
            "setup_tone":               style.get("tone", "เป็นกันเอง"),
            "setup_closing_word":       style.get("closing_word", "ค่ะ"),
            "setup_use_emoji":          bool(style.get("use_emoji", True)),
            "setup_emoji_density":      style.get("emoji_density", "medium"),
            "setup_personality":        str(style.get("personality", "")).strip(),
            "setup_forbidden_words_text": "\n".join(style.get("forbidden_words", [])),
            "setup_always_include_text":  "\n".join(style.get("always_include", [])),
        }

        # Product type from first category name
        cats = products.get("categories", [])
        first_cat_name = cats[0].get("name", "") if cats else ""
        result["setup_product_type"] = _guess_product_type(first_cat_name)

        # Categories (dynamic keys)
        result["setup_cat_count"] = len(cats)
        for i, cat in enumerate(cats):
            bs_lines = []
            for b in cat.get("bestsellers", []):
                name = b.get("name", "")
                price = b.get("price", "")
                hl = b.get("highlight", "")
                if name:
                    line = f"{name} — {price}" + (f" ({hl})" if hl else "")
                    bs_lines.append(line)
            v = cat.get("variants", {})
            result[f"setup_cat_{i}_name"]            = cat.get("name", "")
            result[f"setup_cat_{i}_description"]     = cat.get("description", "")
            result[f"setup_cat_{i}_price_range"]     = cat.get("price_range", "")
            result[f"setup_cat_{i}_bestsellers_text"]= "\n".join(bs_lines)
            result[f"setup_cat_{i}_colors"]          = ", ".join(v.get("colors", []))
            result[f"setup_cat_{i}_sizes"]           = ", ".join(v.get("sizes", []))

        # Promotions (dynamic keys)
        promo_list = promos.get("current", [])
        result["setup_promo_count"] = len(promo_list)
        for i, p in enumerate(promo_list):
            result[f"setup_promo_{i}_title"]     = p.get("title", "")
            result[f"setup_promo_{i}_detail"]    = p.get("detail", "")
            result[f"setup_promo_{i}_condition"] = p.get("condition", "")
            result[f"setup_promo_{i}_expiry"]    = p.get("expiry", "ongoing")

        # FAQs (dynamic keys)
        result["setup_faq_count"] = len(faq_list)
        for i, item in enumerate(faq_list):
            if isinstance(item, dict):
                result[f"setup_faq_{i}_q"] = item.get("question", "")
                result[f"setup_faq_{i}_a"] = item.get("answer", "")
            else:
                result[f"setup_faq_{i}_q"] = str(item)
                result[f"setup_faq_{i}_a"] = ""

        return result
    except Exception:
        return {}


def init_state() -> None:
    if st.session_state.get("setup_initialized"):
        return

    saved: dict = {}
    if DRAFT_FILE.exists():
        try:
            saved = json.loads(DRAFT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    if not saved:
        saved = _load_from_profile_yaml()

    # Restore all saved keys first (covers dynamic cat/promo/faq keys)
    for key, value in saved.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Fill any missing DEFAULTS keys with their default values
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default

    st.session_state.setup_initialized = True


def save_draft() -> None:
    DRAFT_FILE.parent.mkdir(exist_ok=True)
    draft = {}
    for key, value in st.session_state.items():
        if key.startswith("setup_") and isinstance(value, (str, int, float, bool, list, dict)):
            draft[key] = value
    DRAFT_FILE.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_draft() -> None:
    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()


# ══════════════════════════════════════════════════════════════════════════════
# Dynamic list helpers
# ══════════════════════════════════════════════════════════════════════════════

def _delete_item(prefix: str, fields: list[str], idx: int) -> None:
    """Shift dynamic item keys down after deleting idx, decrement count."""
    count_key = f"setup_{prefix}_count"
    count = st.session_state.get(count_key, 0)
    for i in range(idx, count - 1):
        for f in fields:
            st.session_state[f"setup_{prefix}_{i}_{f}"] = st.session_state.get(
                f"setup_{prefix}_{i + 1}_{f}", ""
            )
    for f in fields:
        key = f"setup_{prefix}_{count - 1}_{f}"
        if key in st.session_state:
            del st.session_state[key]
    st.session_state[count_key] = max(0, count - 1)
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# Profile building
# ══════════════════════════════════════════════════════════════════════════════

def _parse_bestsellers(text: str) -> list[dict]:
    """Parse bestsellers text (one per line: 'Name — Price (highlight)')."""
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        highlight = ""
        if "(" in line and line.endswith(")"):
            highlight = line[line.rfind("(") + 1:-1].strip()
            line = line[:line.rfind("(")].strip()
        parts = line.split("—", 1)
        bs_name = parts[0].strip()
        bs_price = parts[1].strip() if len(parts) > 1 else ""
        if bs_name:
            items.append({"name": bs_name, "price": bs_price, "highlight": highlight})
    return items


def build_yaml_dict() -> dict:
    ss = st.session_state

    trust_signals     = [l.strip() for l in ss.get("setup_trust_signals_text", "").splitlines() if l.strip()]
    forbidden_words   = [l.strip() for l in ss.get("setup_forbidden_words_text", "").splitlines() if l.strip()]
    always_include    = [l.strip() for l in ss.get("setup_always_include_text", "").splitlines() if l.strip()]
    escl_keywords     = [l.strip() for l in ss.get("setup_escalation_text", "").splitlines() if l.strip()]

    # Product type
    product_type = ss.get("setup_product_type", "เสื้อผ้า")
    if product_type == "อื่นๆ (ระบุเอง)":
        product_type = ss.get("setup_product_type_custom", "สินค้าทั่วไป").strip() or "สินค้าทั่วไป"

    # Categories
    cat_count = ss.get("setup_cat_count", 0)
    categories = []
    for i in range(cat_count):
        name = ss.get(f"setup_cat_{i}_name", "").strip()
        if not name:
            continue
        colors_raw = ss.get(f"setup_cat_{i}_colors", "")
        sizes_raw  = ss.get(f"setup_cat_{i}_sizes", "")
        categories.append({
            "name":        name,
            "description": ss.get(f"setup_cat_{i}_description", ""),
            "price_range": ss.get(f"setup_cat_{i}_price_range", ""),
            "bestsellers": _parse_bestsellers(ss.get(f"setup_cat_{i}_bestsellers_text", "")),
            "variants": {
                "colors": [c.strip() for c in colors_raw.split(",") if c.strip()],
                "sizes":  [s.strip() for s in sizes_raw.split(",")  if s.strip()],
                "other":  [],
            },
        })

    # Promotions
    promo_count = ss.get("setup_promo_count", 0)
    promotions_current = []
    for i in range(promo_count):
        title = ss.get(f"setup_promo_{i}_title", "").strip()
        if title:
            promotions_current.append({
                "title":     title,
                "detail":    ss.get(f"setup_promo_{i}_detail", ""),
                "condition": ss.get(f"setup_promo_{i}_condition", ""),
                "expiry":    ss.get(f"setup_promo_{i}_expiry", "ongoing") or "ongoing",
            })

    # FAQs
    faq_count = ss.get("setup_faq_count", 0)
    faqs = []
    for i in range(faq_count):
        q = ss.get(f"setup_faq_{i}_q", "").strip()
        if q:
            faqs.append({"question": q, "answer": ss.get(f"setup_faq_{i}_a", "")})

    # Free shipping text normalization
    fs_raw = ss.get("setup_free_shipping", "").strip()
    if fs_raw and not fs_raw.startswith("ฟรีส่ง"):
        free_shipping = f"ฟรีส่งเมื่อซื้อครบ {fs_raw} บาท"
    else:
        free_shipping = fs_raw

    # Determine order_channels from filled contact fields
    order_channels = []
    if ss.get("setup_line_id", "").strip():
        order_channels.append("LINE OA")
    if ss.get("setup_facebook", "").strip():
        order_channels.append("Facebook Inbox")

    return {
        "shop": {
            "name":          ss.get("setup_shop_name", ""),
            "tagline":       ss.get("setup_shop_tagline", ""),
            "description":   ss.get("setup_shop_description", ""),
            "established":   ss.get("setup_shop_established", ""),
            "trust_signals": trust_signals,
        },
        "products": {
            "categories":  categories,
            "materials":   ss.get("setup_materials", ""),
            "origin":      ss.get("setup_origin", ""),
            "quality_cert": ss.get("setup_quality_cert", ""),
        },
        "promotions": {
            "current": promotions_current,
            "shipping": {
                "free_threshold": free_shipping,
                "carriers":       list(ss.get("setup_carriers", [])),
                "domestic_days":  ss.get("setup_shipping_days", ""),
                "cod_available":  bool(ss.get("setup_cod", True)),
            },
        },
        "policies": {
            "return":          ss.get("setup_return_policy", ""),
            "exchange":        ss.get("setup_exchange_policy", ""),
            "warranty":        ss.get("setup_warranty", ""),
            "payment_methods": list(ss.get("setup_payment_methods", [])),
        },
        "faq": faqs,
        "contact": {
            "line_id":       ss.get("setup_line_id", ""),
            "facebook":      ss.get("setup_facebook", ""),
            "phone":         ss.get("setup_phone", ""),
            "email":         "",
            "hours":         ss.get("setup_hours", ""),
            "response_time": ss.get("setup_response_time", ""),
            "order_channels": order_channels,
        },
        "reply_style": {
            "tone":            ss.get("setup_tone", "เป็นกันเอง"),
            "closing_word":    ss.get("setup_closing_word", "ค่ะ"),
            "use_emoji":       bool(ss.get("setup_use_emoji", True)),
            "emoji_density":   ss.get("setup_emoji_density", "medium"),
            "personality":     ss.get("setup_personality", ""),
            "forbidden_words": forbidden_words,
            "always_include":  always_include,
        },
        "escalation": {
            "trigger_keywords": escl_keywords,
            "action":           "flag_for_human",
            "human_notify":     True,
        },
    }


def build_temp_profile():
    """Build a ShopProfile from current wizard state (for AI test, not saved)."""
    from app.core.profile_loader import (
        ShopProfile, Contact, ReplyStyle, FAQ,
        ProductCategory, Promotions, CurrentPromotion,
        ShippingPromo, Policies, Escalation, Bestseller, ProductVariants,
    )

    d        = build_yaml_dict()
    shop_d   = d["shop"]
    prod_d   = d["products"]
    promo_d  = d["promotions"]
    policy_d = d["policies"]
    style_d  = d["reply_style"]
    escl_d   = d["escalation"]
    cont_d   = d["contact"]

    categories = []
    for cat in prod_d.get("categories", []):
        bs = [Bestseller(name=b["name"], price=b["price"], highlight=b.get("highlight", ""))
              for b in cat.get("bestsellers", [])]
        v  = cat.get("variants", {})
        categories.append(ProductCategory(
            name=cat["name"],
            description=cat.get("description", ""),
            price_range=cat.get("price_range", ""),
            bestsellers=bs,
            variants=ProductVariants(colors=v.get("colors", []), sizes=v.get("sizes", [])),
        ))

    ship_d = promo_d.get("shipping", {})
    promotions = Promotions(
        current=[
            CurrentPromotion(
                title=p["title"], detail=p.get("detail", ""),
                condition=p.get("condition", ""), expiry=p.get("expiry", "ongoing"),
            )
            for p in promo_d.get("current", [])
        ],
        shipping=ShippingPromo(
            free_threshold=ship_d.get("free_threshold", ""),
            carriers=ship_d.get("carriers", []),
            domestic_days=ship_d.get("domestic_days", ""),
            cod_available=ship_d.get("cod_available", True),
        ),
    )

    return ShopProfile(
        shop_name    =shop_d.get("name") or "ร้านค้าออนไลน์",
        tagline      =shop_d.get("tagline", ""),
        description  =shop_d.get("description", ""),
        established  =str(shop_d.get("established", "")),
        trust_signals=shop_d.get("trust_signals", []),
        categories   =categories,
        materials    =prod_d.get("materials", ""),
        origin       =prod_d.get("origin", ""),
        quality_cert =prod_d.get("quality_cert", ""),
        promotions   =promotions,
        policies=Policies(
            return_policy  =policy_d.get("return", ""),
            exchange       =policy_d.get("exchange", ""),
            warranty       =policy_d.get("warranty", ""),
            payment_methods=policy_d.get("payment_methods", []),
        ),
        faqs=[FAQ(question=f["question"], answer=f["answer"]) for f in d.get("faq", [])],
        contact=Contact(
            line_id       =cont_d.get("line_id", ""),
            facebook      =cont_d.get("facebook", ""),
            phone         =cont_d.get("phone", ""),
            hours         =cont_d.get("hours", ""),
            response_time =cont_d.get("response_time", ""),
            order_channels=cont_d.get("order_channels", []),
        ),
        style=ReplyStyle(
            tone          =style_d.get("tone", "เป็นกันเอง"),
            closing_word  =style_d.get("closing_word", "ค่ะ"),
            use_emoji     =bool(style_d.get("use_emoji", True)),
            emoji_density =style_d.get("emoji_density", "medium"),
            personality   =style_d.get("personality", ""),
            forbidden_words=style_d.get("forbidden_words", []),
            always_include =style_d.get("always_include", []),
        ),
        escalation=Escalation(
            trigger_keywords=escl_d.get("trigger_keywords", []),
        ),
    )


def save_profile() -> None:
    data   = build_yaml_dict()
    header = (
        "# ==============================================================================\n"
        "#  SHOP PROFILE — สร้างโดย Setup Wizard\n"
        "#  แก้ไขได้ที่ตรงนี้โดยตรง หรือกลับมาใช้ Setup Wizard อีกครั้ง\n"
        "# ==============================================================================\n\n"
    )
    PROFILE_FILE.write_text(
        header + yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    st.cache_resource.clear()
    clear_draft()


# ══════════════════════════════════════════════════════════════════════════════
# UI helpers
# ══════════════════════════════════════════════════════════════════════════════

def render_step_bar(current: int) -> None:
    items_html = ""
    for i, label in enumerate(STEP_LABELS, start=1):
        if i < current:
            cls = "step-done"
            label = label + " ✓"
        elif i == current:
            cls = "step-active"
        else:
            cls = "step-pending"
        items_html += f'<div class="step-item {cls}">{label}</div>'
    st.markdown(f'<div class="step-bar">{items_html}</div>', unsafe_allow_html=True)


def _section(title: str) -> None:
    st.markdown(f'<p class="section-title">{title}</p>', unsafe_allow_html=True)


def _nav_buttons(step: int) -> None:
    """Render Back / Next (or Save) buttons for a given step."""
    is_first = step == 1
    is_last  = step == TOTAL_STEPS

    col_back, _, col_next = st.columns([1, 2, 1])
    with col_back:
        if not is_first:
            if st.button("← ย้อนกลับ", use_container_width=True, key=f"step{step}_back"):
                st.session_state.setup_step = step - 1
                save_draft()
                st.rerun()
    with col_next:
        if not is_last:
            if st.button("ถัดไป →", type="primary", use_container_width=True, key=f"step{step}_next"):
                if _validate_step(step):
                    st.session_state.setup_step = step + 1
                    st.session_state.setup_test_reply = ""
                    save_draft()
                    st.rerun()


def _validate_step(step: int) -> bool:
    if step == 1 and not st.session_state.get("setup_shop_name", "").strip():
        st.error("กรุณาใส่ชื่อร้านก่อน (ช่องที่มี *)")
        return False
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — ข้อมูลพื้นฐานร้าน
# ══════════════════════════════════════════════════════════════════════════════

def render_step1() -> None:
    st.subheader("🏪 ข้อมูลพื้นฐานร้าน")
    st.caption("AI จะใช้ข้อมูลเหล่านี้แนะนำตัวและสร้างความน่าเชื่อถือเวลาตอบลูกค้า")
    st.divider()

    st.text_input("ชื่อร้าน *", placeholder="เช่น ร้านมายชอป, ปุ้มปุ้มแฟชั่น",
                  key="setup_shop_name")
    st.text_input("สโลแกน / แท็กไลน์",
                  placeholder="เช่น แฟชั่นสตรีราคาเป็นกันเอง",
                  key="setup_shop_tagline")
    st.text_area("คำอธิบายร้าน",
                 placeholder="เช่น ร้านเสื้อผ้าแฟชั่นสตรีออนไลน์ คัดสรรสไตล์เกาหลี-ญี่ปุ่น ผ้าคุณภาพดีราคาเข้าถึงได้",
                 height=90, key="setup_shop_description")

    col_year, _ = st.columns([1, 2])
    with col_year:
        st.text_input("ก่อตั้งเมื่อปี พ.ศ.",
                      placeholder="เช่น 2563",
                      key="setup_shop_established")

    _section("จุดเด่นของร้าน / สิ่งที่ทำให้ลูกค้าเชื่อใจ")
    st.caption("พิมพ์ทีละบรรทัด เช่น  ขายมาแล้วกว่า 5 ปี  /  รีวิว 4.9 ดาว  /  ลูกค้ากว่า 10,000 คน")
    st.text_area("", key="setup_trust_signals_text",
                 placeholder="ขายมาแล้วกว่า 5 ปี\nลูกค้ากว่า 10,000 คน\nรีวิว 4.9 ดาว",
                 height=100, label_visibility="collapsed")

    st.divider()
    _nav_buttons(1)


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — สินค้าและราคา
# ══════════════════════════════════════════════════════════════════════════════

def render_step2() -> None:
    st.subheader("📦 สินค้าและราคา")
    st.caption("ยิ่งกรอกละเอียด AI จะตอบเรื่องสินค้าได้ถูกต้องมากขึ้น")
    st.divider()

    _section("ประเภทสินค้าหลัก")
    pt_idx = PRODUCT_TYPES.index(st.session_state.get("setup_product_type", "เสื้อผ้า"))
    st.selectbox("ประเภทสินค้า", PRODUCT_TYPES, index=pt_idx, key="setup_product_type",
                 label_visibility="collapsed")
    if st.session_state.get("setup_product_type") == "อื่นๆ (ระบุเอง)":
        st.text_input("ระบุประเภทสินค้า", placeholder="เช่น เครื่องสำอาง, อาหารเสริม",
                      key="setup_product_type_custom")

    _section("หมวดสินค้า")
    st.caption("เพิ่มหมวดสินค้าที่ร้านมีขาย เช่น เดรส, เสื้อ, กางเกง แต่ละหมวดจะช่วยให้ AI ตอบเรื่องราคาและสินค้าได้ตรง")

    cat_count = st.session_state.get("setup_cat_count", 0)
    cat_to_delete = None
    for i in range(cat_count):
        name = st.session_state.get(f"setup_cat_{i}_name", "") or f"หมวดสินค้า {i + 1}"
        with st.expander(f"📦 {name}", expanded=not st.session_state.get(f"setup_cat_{i}_name", "")):
            col_n, col_p, col_del = st.columns([3, 3, 0.7])
            with col_n:
                st.text_input("ชื่อหมวด *", key=f"setup_cat_{i}_name",
                              placeholder="เช่น เดรสและชุดเซ็ต")
            with col_p:
                st.text_input("ช่วงราคา", key=f"setup_cat_{i}_price_range",
                              placeholder="เช่น 399 - 1,290 บาท")
            with col_del:
                st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_cat_{i}", help="ลบหมวดนี้",
                             use_container_width=True):
                    cat_to_delete = i

            st.text_area("คำอธิบายหมวด", key=f"setup_cat_{i}_description",
                         placeholder="เช่น เสื้อผ้าสไตล์เกาหลี-ญี่ปุ่น ใส่สบาย เหมาะทุกโอกาส",
                         height=60)

            st.markdown("**สินค้าขายดีในหมวดนี้** — หนึ่งรายการต่อบรรทัด รูปแบบ: `ชื่อสินค้า — ราคา`")
            st.text_area("", key=f"setup_cat_{i}_bestsellers_text",
                         placeholder="เดรสลายดอกไม้ Korean Style — 590 บาท\nชุดเซ็ตเสื้อครอป+กางเกง — 790 บาท",
                         height=90, label_visibility="collapsed")

            c1, c2 = st.columns(2)
            with c1:
                st.text_input("สีที่มี (คั่นด้วยจุลภาค)",
                              key=f"setup_cat_{i}_colors",
                              placeholder="ดำ, ขาว, ชมพู, น้ำเงิน")
            with c2:
                st.text_input("ไซส์ที่มี (คั่นด้วยจุลภาค)",
                              key=f"setup_cat_{i}_sizes",
                              placeholder="S, M, L, XL")

    if cat_to_delete is not None:
        _delete_item("cat", CAT_FIELDS, cat_to_delete)

    if st.button("＋ เพิ่มหมวดสินค้า", key="add_cat"):
        st.session_state["setup_cat_count"] = cat_count + 1
        st.rerun()

    _section("วัสดุและแหล่งผลิต")
    st.text_area("วัสดุ / คุณสมบัติสินค้า",
                 placeholder="เช่น ผ้า Cotton 100%, ชีฟอง, Spandex คุณภาพดี ผ่านการทดสอบความทนทาน",
                 height=70, key="setup_materials")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("แหล่งผลิต", placeholder="เช่น ผลิตในไทย โรงงานมาตรฐาน",
                      key="setup_origin")
    with c2:
        st.text_input("การรับรอง / มาตรฐาน",
                      placeholder="เช่น ผ่านการตรวจสอบทุกชิ้นก่อนจัดส่ง",
                      key="setup_quality_cert")

    st.divider()
    _nav_buttons(2)


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — โปรโมชั่นและนโยบาย
# ══════════════════════════════════════════════════════════════════════════════

def render_step3() -> None:
    st.subheader("🎁 โปรโมชั่นและนโยบาย")
    st.caption("AI จะนำโปรและนโยบายมาตอบลูกค้าโดยอัตโนมัติ")
    st.divider()

    _section("โปรโมชั่นปัจจุบัน")
    promo_count = st.session_state.get("setup_promo_count", 0)
    promo_to_delete = None
    for i in range(promo_count):
        title = st.session_state.get(f"setup_promo_{i}_title", "") or f"โปรโมชั่น {i + 1}"
        with st.container(border=True):
            c1, c_del = st.columns([10, 0.8])
            with c1:
                st.text_input(f"ชื่อโปรโมชั่น {i + 1} *",
                              key=f"setup_promo_{i}_title",
                              placeholder="เช่น ซื้อ 2 ลด 10%")
            with c_del:
                st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_promo_{i}", help="ลบโปรนี้",
                             use_container_width=True):
                    promo_to_delete = i

            st.text_area("รายละเอียด",
                         key=f"setup_promo_{i}_detail",
                         placeholder="เช่น ซื้อ 2 ชิ้นขึ้นไป ลดทันที 10% ทุกสินค้าในร้าน",
                         height=65)
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("เงื่อนไข", key=f"setup_promo_{i}_condition",
                              placeholder="เช่น ทุกสินค้า ไม่มีขั้นต่ำ")
            with c2:
                st.text_input("หมดอายุ", key=f"setup_promo_{i}_expiry",
                              placeholder="เช่น 31/12/2568 หรือ ongoing")

    if promo_to_delete is not None:
        _delete_item("promo", PROMO_FIELDS, promo_to_delete)

    if st.button("＋ เพิ่มโปรโมชั่น", key="add_promo"):
        st.session_state["setup_promo_count"] = promo_count + 1
        st.rerun()

    _section("การจัดส่ง")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("ฟรีส่งเมื่อซื้อครบ (บาท)",
                      placeholder="เช่น 500",
                      key="setup_free_shipping")
    with c2:
        st.text_input("ระยะเวลาจัดส่ง",
                      placeholder="เช่น 1-3 วันทำการ",
                      key="setup_shipping_days")

    st.multiselect("บริษัทขนส่งที่ใช้", options=CARRIER_OPTIONS,
                   key="setup_carriers")
    st.toggle("รับปลายทาง (COD) ✅", key="setup_cod")

    _section("ช่องทางชำระเงิน")
    st.multiselect("ช่องทางที่รับชำระ", options=PAYMENT_OPTIONS,
                   key="setup_payment_methods")

    _section("นโยบายร้าน")
    c1, c2 = st.columns(2)
    with c1:
        st.text_area("นโยบายคืนสินค้า",
                     placeholder="เช่น คืนได้ภายใน 7 วัน หากสินค้าชำรุดจากการผลิต",
                     height=80, key="setup_return_policy")
    with c2:
        st.text_area("นโยบายเปลี่ยนสินค้า",
                     placeholder="เช่น เปลี่ยนไซส์ได้ฟรี 1 ครั้ง ภายใน 14 วัน",
                     height=80, key="setup_exchange_policy")
    st.text_input("การรับประกัน",
                  placeholder="เช่น รับประกันความพึงพอใจ 100% ทุกชิ้น",
                  key="setup_warranty")

    st.divider()
    _nav_buttons(3)


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — FAQ และ Escalation
# ══════════════════════════════════════════════════════════════════════════════

def render_step4() -> None:
    st.subheader("❓ FAQ และช่องทางติดต่อ")
    st.caption("AI จะค้นหาคำตอบจาก FAQ ก่อนเสมอ ยิ่งมีมาก ยิ่งตอบตรงและแม่นยำ")
    st.divider()

    _section("คำถามที่พบบ่อย (FAQ)")
    faq_count = st.session_state.get("setup_faq_count", 0)
    faq_to_delete = None
    for i in range(faq_count):
        with st.container(border=True):
            c1, c_del = st.columns([11, 0.8])
            with c1:
                st.text_input(f"คำถาม {i + 1}",
                              key=f"setup_faq_{i}_q",
                              placeholder="เช่น สินค้ามีไซส์อะไรบ้าง")
            with c_del:
                st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_faq_{i}", help="ลบข้อนี้",
                             use_container_width=True):
                    faq_to_delete = i
            st.text_area("คำตอบ",
                         key=f"setup_faq_{i}_a",
                         placeholder="เช่น มี S M L XL และบางรุ่นมี XXL ดูตาราง size guide ในรูปสินค้าได้เลยค่ะ",
                         height=70)

    if faq_to_delete is not None:
        _delete_item("faq", FAQ_FIELDS, faq_to_delete)

    if st.button("＋ เพิ่มคำถาม", key="add_faq"):
        st.session_state["setup_faq_count"] = faq_count + 1
        st.rerun()

    _section("คำที่ต้องส่งต่อแอดมินทันที")
    st.caption(
        "ถ้า comment ลูกค้ามีคำเหล่านี้ AI จะไม่ตอบ แต่จะแจ้งแอดมินทันที\n"
        "พิมพ์ทีละบรรทัด เช่น  โกง  /  คืนเงิน  /  ฟ้อง"
    )
    st.text_area("", key="setup_escalation_text",
                 placeholder="โกง\nคืนเงิน\nหลอก\nฟ้อง\nแจ้งความ\nแย่มาก",
                 height=110, label_visibility="collapsed")

    _section("ช่องทางติดต่อ")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input("LINE ID / LINE OA", placeholder="เช่น @myshop",
                      key="setup_line_id")
        st.text_input("เบอร์โทรศัพท์", placeholder="เช่น 082-XXX-XXXX",
                      key="setup_phone")
    with c2:
        st.text_input("Facebook Page", placeholder="เช่น fb.com/myshop",
                      key="setup_facebook")
        st.text_input("เวลาทำการ", placeholder="เช่น เปิด 09:00-21:00 ทุกวัน",
                      key="setup_hours")
    st.text_input("เวลาตอบกลับโดยประมาณ",
                  placeholder="เช่น ตอบกลับภายใน 30 นาที",
                  key="setup_response_time")

    st.divider()
    _nav_buttons(4)


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — สไตล์การตอบและทดสอบ
# ══════════════════════════════════════════════════════════════════════════════

def render_step5() -> None:
    st.subheader("✨ สไตล์การตอบและทดสอบ")
    st.caption("กำหนดบุคลิก AI ให้ตรงกับแบรนด์ร้าน แล้วทดสอบก่อนบันทึก")
    st.divider()

    _section("โทนและบุคลิก")

    # Tone radio with live example preview
    tone_idx = TONE_OPTIONS.index(st.session_state.get("setup_tone", "เป็นกันเอง"))
    tone = st.radio("โทนการพูด", TONE_OPTIONS, index=tone_idx,
                    horizontal=True, key="setup_tone")
    st.markdown(
        f'<div class="tone-example">ตัวอย่าง: {TONE_EXAMPLES.get(tone, "")}</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        cw_idx = CLOSING_WORDS.index(st.session_state.get("setup_closing_word", "ค่ะ"))
        st.radio("คำลงท้าย", CLOSING_WORDS, index=cw_idx, horizontal=True,
                 key="setup_closing_word")
    with c2:
        st.toggle("ใช้ Emoji 🎉", key="setup_use_emoji")
        if st.session_state.get("setup_use_emoji", True):
            ed_idx = EMOJI_DENSITY_OPTIONS.index(
                st.session_state.get("setup_emoji_density", "medium")
            )
            st.radio(
                "ความถี่ Emoji",
                EMOJI_DENSITY_OPTIONS,
                index=ed_idx,
                horizontal=True,
                key="setup_emoji_density",
                format_func=lambda x: EMOJI_DENSITY_LABELS.get(x, x),
            )

    st.text_area(
        "บุคลิก AI",
        placeholder=(
            "เช่น ใจดี กระตือรือร้น ช่วยเหลือลูกค้าอย่างจริงใจ\n"
            "อธิบายละเอียดแต่ไม่ยืดเยื้อ ชวนซื้ออย่างสุภาพโดยนำเสนอจุดเด่นและโปรโมชั่น"
        ),
        height=90, key="setup_personality",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.text_area(
            "คำต้องห้าม (ทีละบรรทัด)",
            placeholder="ไม่ทราบ\nไม่รู้\nไม่แน่ใจ",
            height=90, key="setup_forbidden_words_text",
        )
    with c2:
        st.text_area(
            "ต้องระบุในทุกข้อความ (ทีละบรรทัด)",
            placeholder="LINE @myshop ทุกครั้งที่แนะนำให้ติดต่อ",
            height=90, key="setup_always_include_text",
        )

    st.divider()
    _section("ทดสอบ AI")

    from app.core.llm_client import OllamaClient
    client = OllamaClient()
    if not client.is_healthy():
        st.warning(
            "⚠️ Ollama ออฟไลน์ — ไม่สามารถทดสอบ AI ได้ตอนนี้\n\n"
            "รัน `ollama serve` แล้วรีเฟรชหน้านี้\n\n"
            "คุณยังสามารถบันทึกข้อมูลร้านไปก่อนได้",
        )
    else:
        st.text_input(
            "พิมพ์ comment ลูกค้าทดลอง",
            placeholder="เช่น มีไซส์ XL ไหมคะ ราคาเท่าไหร่",
            key="setup_test_comment",
        )
        if st.button("🤖 ทดสอบ AI", type="secondary", key="step5_test"):
            comment = st.session_state.get("setup_test_comment", "").strip()
            if not comment:
                st.warning("กรุณาพิมพ์ comment ก่อน")
            else:
                with st.spinner("AI กำลังคิด…"):
                    from app.services.analyzer import CommentAnalyzer
                    from app.services.generator import ReplyGenerator
                    profile  = build_temp_profile()
                    analyzer = CommentAnalyzer(client=client, profile=profile)
                    generator = ReplyGenerator(client=client, profile=profile)
                    analysis = analyzer.analyze(comment)
                    result   = generator.generate(analysis)
                    st.session_state.setup_test_reply = (
                        result.reply or "(ไม่มีคำตอบ — comment อาจถูกจัดว่าเป็น spam)"
                    )
        reply = st.session_state.get("setup_test_reply", "")
        if reply:
            st.markdown("**คำตอบที่ AI จะส่ง:**")
            st.markdown(f'<div class="reply-card">{reply}</div>', unsafe_allow_html=True)
            st.caption("ถ้าคำตอบยังไม่ถูกใจ กด ← ย้อนกลับ แล้วปรับข้อมูลหรือสไตล์การตอบ")

    st.divider()

    # Summary expander
    with st.expander("📋 สรุปข้อมูลทั้งหมดก่อนบันทึก"):
        ss = st.session_state
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**ชื่อร้าน:** {ss.get('setup_shop_name') or '—'}")
            st.markdown(f"**สโลแกน:** {ss.get('setup_shop_tagline') or '—'}")
            st.markdown(f"**ก่อตั้งปี:** {ss.get('setup_shop_established') or '—'}")
            n_cats = ss.get("setup_cat_count", 0)
            st.markdown(f"**หมวดสินค้า:** {n_cats} หมวด")
            n_promos = ss.get("setup_promo_count", 0)
            st.markdown(f"**โปรโมชั่น:** {n_promos} รายการ")
        with col2:
            st.markdown(f"**โทน:** {ss.get('setup_tone') or '—'}")
            st.markdown(f"**คำลงท้าย:** {ss.get('setup_closing_word') or '—'}")
            use_emoji = ss.get("setup_use_emoji", True)
            st.markdown(f"**Emoji:** {'ใช้ ✅' if use_emoji else 'ไม่ใช้ ❌'}")
            n_faqs = ss.get("setup_faq_count", 0)
            st.markdown(f"**FAQ:** {n_faqs} ข้อ")
            st.markdown(f"**LINE:** {ss.get('setup_line_id') or '—'}")

    # Save button
    col_back, _, col_save = st.columns([1, 2, 1])
    with col_back:
        if st.button("← ย้อนกลับ", use_container_width=True, key="step5_back"):
            st.session_state.setup_step = 4
            save_draft()
            st.rerun()
    with col_save:
        if st.button("💾 บันทึกและเริ่มใช้งาน", type="primary",
                     use_container_width=True, key="step5_save"):
            if not st.session_state.get("setup_shop_name", "").strip():
                st.error("กรุณากลับไปใส่ชื่อร้านในขั้นตอนที่ 1 ก่อน")
            else:
                try:
                    save_profile()
                    st.session_state.setup_saved = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"บันทึกไม่สำเร็จ: {exc}")

    if st.session_state.get("setup_saved"):
        st.success("✅ บันทึก shop_profile.yaml เรียบร้อยแล้ว!")
        st.info(
            "**ขั้นตอนต่อไป:**\n"
            "- กลับไปที่หน้าหลัก **AI Sales Assistant** เพื่อเริ่มใช้งาน\n"
            "- หากต้องการแก้ไขทีหลัง กลับมาที่หน้า Setup ได้เสมอ\n"
            "- ตั้งค่า Webhook ดูได้ที่ `docs/FACEBOOK_SETUP.md` หรือ `docs/LINE_SETUP.md`",
        )
        if st.button("🏠 ไปหน้าหลัก", type="primary", key="go_home"):
            st.switch_page("streamlit_app.py")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    init_state()

    st.title("🏪 ตั้งค่าร้านค้า")
    st.caption("กรอกข้อมูลร้านทีเดียว AI จะจำและนำไปใช้ตอบลูกค้าทุกครั้ง")

    step = st.session_state.get("setup_step", 1)
    render_step_bar(step)

    if step == 1:
        render_step1()
    elif step == 2:
        render_step2()
    elif step == 3:
        render_step3()
    elif step == 4:
        render_step4()
    elif step == 5:
        render_step5()


if __name__ == "__main__":
    main()
