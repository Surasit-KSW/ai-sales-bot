"""
AI Sales Assistant — Streamlit Web UI (Phase 2)

Run:
    streamlit run streamlit_app.py
"""

import csv
import io
import json
import sys
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="AI Sales Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Fix Windows stdout encoding ───────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.llm_client import OllamaClient
from app.core.profile_loader import load_profile
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator

# ── Constants ─────────────────────────────────────────────────────────────────
INTENT_CONFIG = {
    "POTENTIAL_BUYER": {"label": "🛒 ผู้สนใจซื้อ",    "color": "#28a745", "bg": "#d4edda"},
    "GENERAL_INQUIRY": {"label": "💬 สอบถามทั่วไป",   "color": "#0d6efd", "bg": "#cfe2ff"},
    "COMPLAINT":       {"label": "⚠️ ร้องเรียน",       "color": "#fd7e14", "bg": "#ffe5d0"},
    "SPAM":            {"label": "🚫 Spam",             "color": "#dc3545", "bg": "#f8d7da"},
}

SENTIMENT_EMOJI = {"positive": "😊", "neutral": "😐", "negative": "😟"}

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Intent badge */
    .intent-badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    /* Comment card */
    .comment-card {
        background: #f8f9fa;
        border-left: 4px solid #dee2e6;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 6px;
        font-size: 0.95rem;
    }
    /* Reply box */
    .reply-card {
        background: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    /* Stat card */
    .stat-box {
        text-align: center;
        padding: 12px;
        border-radius: 10px;
        background: #f8f9fa;
        margin: 4px 0;
    }
    .stat-number { font-size: 1.8rem; font-weight: 700; }
    .stat-label  { font-size: 0.75rem; color: #6c757d; }
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── Cached resources (load once per session) ──────────────────────────────────
@st.cache_resource
def get_client() -> OllamaClient:
    return OllamaClient()


@st.cache_resource
def get_profile():
    return load_profile()


@st.cache_resource
def get_services():
    client  = get_client()
    profile = get_profile()
    return CommentAnalyzer(client=client, profile=profile), \
           ReplyGenerator(client=client,  profile=profile)


# ── Helper ────────────────────────────────────────────────────────────────────
def intent_badge_html(intent: str) -> str:
    cfg = INTENT_CONFIG.get(intent, {"label": intent, "color": "#6c757d", "bg": "#e9ecef"})
    return (
        f'<span class="intent-badge" '
        f'style="background:{cfg["bg"]};color:{cfg["color"]}">'
        f'{cfg["label"]}</span>'
    )


def process_comments(comments: List[str]) -> List[Dict[str, Any]]:
    """Run analyzer + generator on a list of comments, streaming results."""
    analyzer, generator = get_services()
    results = []
    progress = st.progress(0, text="กำลังวิเคราะห์…")
    total = len(comments)

    for idx, comment in enumerate(comments):
        progress.progress((idx) / total, text=f"วิเคราะห์ {idx+1}/{total} : {comment[:40]}…")
        analysis  = analyzer.analyze(comment)
        generated = generator.generate(analysis)
        results.append({
            "id":           idx + 1,
            "comment":      comment,
            "intent":       analysis.intent,
            "confidence":   round(analysis.confidence, 2),
            "sentiment":    analysis.sentiment,
            "key_signals":  analysis.key_signals,
            "reply":        generated.reply,
            "was_skipped":  generated.was_skipped,
            "error":        generated.error or analysis.error,
            "processed_at": datetime.now().isoformat(),
        })

    progress.progress(1.0, text="✅ เสร็จแล้ว!")
    return results


def to_csv(results: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "comment", "intent", "confidence", "sentiment", "reply", "was_skipped", "error"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    profile = get_profile()
    client  = get_client()

    with st.sidebar:
        st.markdown("## 🤖 AI Sales Assistant")
        st.divider()

        # Ollama status
        if client.is_healthy():
            st.success(f"✅ Ollama Online\n\n`{client.model}`", icon=None)
        else:
            st.error("❌ Ollama Offline\n\nรัน `ollama serve` ก่อนครับ")

        st.divider()

        # Shop info
        st.markdown("### 🏪 ข้อมูลร้าน")
        st.markdown(f"**{profile.shop_name}**")
        if profile.tagline:
            st.caption(profile.tagline)
        st.markdown(f"🏷️ {profile.product_category}")
        if profile.price_range:
            st.markdown(f"💰 {profile.price_range}")
        if profile.line_id:
            st.markdown(f"📱 LINE: `{profile.line_id}`")

        st.divider()
        st.caption("แก้ข้อมูลร้านได้ที่ `shop_profile.yaml`")
        st.caption("จากนั้น Restart app เพื่อโหลดใหม่")


# ── Main App ──────────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    st.title("🤖 AI Sales Assistant")
    st.caption("วิเคราะห์คอมเมนต์ลูกค้าและสร้างคำตอบภาษาไทยอัตโนมัติ")
    st.divider()

    # ── Input Section ────────────────────────────────────────────────────────
    st.subheader("📝 วางคอมเมนต์ลูกค้า")
    st.caption("ใส่ทีละ 1 บรรทัดต่อ 1 คอมเมนต์")

    col_input, col_tip = st.columns([3, 1])

    with col_input:
        raw_input = st.text_area(
            label="คอมเมนต์",
            placeholder=(
                "ราคาเท่าไหร่คะ มีโปรไหม\n"
                "ผ้าทำจากอะไรคะ\n"
                "สั่งไป 3 วันแล้วยังไม่ได้ของเลยครับ\n"
                "คลิกรับเงินฟรี >> bit.ly/xxxx"
            ),
            height=180,
            label_visibility="collapsed",
        )

    with col_tip:
        st.info(
            "**💡 Tips**\n\n"
            "- 1 บรรทัด = 1 คอมเมนต์\n"
            "- บรรทัดว่างจะถูกข้าม\n"
            "- รองรับ emoji ✅\n"
            "- ไม่จำกัดจำนวน"
        )

    col_btn, col_demo = st.columns([1, 5])
    with col_btn:
        run_btn = st.button("▶ วิเคราะห์", type="primary", use_container_width=True)
    with col_demo:
        demo_btn = st.button("🎯 โหลด Demo", use_container_width=False)

    # Load demo comments
    if demo_btn:
        st.session_state["demo_text"] = (
            "ราคาเท่าไหร่คะ มีโปรไหม อยากได้สีดำ\n"
            "ผ้าทำจากอะไรคะ แพ้ง่ายอยากรู้ก่อนสั่ง\n"
            "ซื้อ 3 ชิ้นได้ส่วนลดไหมครับ\n"
            "สั่งไป 5 วันแล้วยังไม่ได้ของเลยค่ะ\n"
            "คลิกรับเงินฟรี >> bit.ly/xxxx ด่วน!!!"
        )
        st.rerun()

    # Pre-fill demo text if set
    if "demo_text" in st.session_state:
        raw_input = st.session_state.pop("demo_text")

    # ── Processing ───────────────────────────────────────────────────────────
    if run_btn and raw_input.strip():
        comments = [l.strip() for l in raw_input.splitlines() if l.strip()]

        if not get_client().is_healthy():
            st.error("❌ Ollama ไม่ได้รัน — กรุณาเปิด `ollama serve` ก่อนครับ")
            return

        with st.spinner(""):
            results = process_comments(comments)

        st.session_state["results"] = results

    # ── Results ──────────────────────────────────────────────────────────────
    if "results" in st.session_state:
        results: List[Dict] = st.session_state["results"]
        st.divider()

        # Summary stats
        st.subheader("📊 สรุปผล")
        total      = len(results)
        buyers     = sum(1 for r in results if r["intent"] == "POTENTIAL_BUYER")
        inquiries  = sum(1 for r in results if r["intent"] == "GENERAL_INQUIRY")
        complaints = sum(1 for r in results if r["intent"] == "COMPLAINT")
        spam       = sum(1 for r in results if r["intent"] == "SPAM")

        c1, c2, c3, c4, c5 = st.columns(5)
        for col, num, label, color in [
            (c1, total,      "ทั้งหมด",      "#495057"),
            (c2, buyers,     "🛒 ผู้สนใจซื้อ", "#28a745"),
            (c3, inquiries,  "💬 สอบถาม",     "#0d6efd"),
            (c4, complaints, "⚠️ ร้องเรียน",  "#fd7e14"),
            (c5, spam,       "🚫 Spam",        "#dc3545"),
        ]:
            col.markdown(
                f'<div class="stat-box">'
                f'<div class="stat-number" style="color:{color}">{num}</div>'
                f'<div class="stat-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Filter
        st.divider()
        col_filter, col_export_j, col_export_c = st.columns([3, 1, 1])
        with col_filter:
            filter_intent = st.selectbox(
                "กรองตาม Intent",
                ["ทั้งหมด", "🛒 ผู้สนใจซื้อ", "💬 สอบถามทั่วไป", "⚠️ ร้องเรียน", "🚫 Spam"],
                label_visibility="collapsed",
            )

        intent_map = {
            "🛒 ผู้สนใจซื้อ":  "POTENTIAL_BUYER",
            "💬 สอบถามทั่วไป": "GENERAL_INQUIRY",
            "⚠️ ร้องเรียน":    "COMPLAINT",
            "🚫 Spam":          "SPAM",
        }
        filtered = (
            results if filter_intent == "ทั้งหมด"
            else [r for r in results if r["intent"] == intent_map.get(filter_intent)]
        )

        # Export buttons
        with col_export_j:
            st.download_button(
                "⬇ JSON",
                data=json.dumps(results, ensure_ascii=False, indent=2),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_export_c:
            st.download_button(
                "⬇ CSV",
                data=to_csv(results),
                file_name=f"results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        # Result cards
        st.subheader(f"💬 ผลลัพธ์ ({len(filtered)} รายการ)")

        for r in filtered:
            cfg  = INTENT_CONFIG.get(r["intent"], {})
            sent = SENTIMENT_EMOJI.get(r["sentiment"], "")
            conf = int(r["confidence"] * 100)

            with st.container(border=True):
                # Header row
                col_badge, col_conf, col_sent = st.columns([3, 1, 1])
                with col_badge:
                    st.markdown(intent_badge_html(r["intent"]), unsafe_allow_html=True)
                with col_conf:
                    st.caption(f"Confidence: **{conf}%**")
                with col_sent:
                    st.caption(f"Sentiment: {sent} {r['sentiment']}")

                # Comment
                st.markdown(
                    f'<div class="comment-card">💬 <b>ลูกค้า:</b> {r["comment"]}</div>',
                    unsafe_allow_html=True,
                )

                # Reply
                if r["was_skipped"]:
                    st.markdown(
                        '<div class="reply-card" style="color:#dc3545">⏭ ข้าม (SPAM)</div>',
                        unsafe_allow_html=True,
                    )
                elif r["error"] and not r["reply"]:
                    st.error(f"❌ Error: {r['error']}")
                else:
                    # Editable reply
                    edited = st.text_area(
                        "คำตอบ",
                        value=r["reply"],
                        height=120,
                        key=f"reply_{r['id']}",
                        label_visibility="collapsed",
                    )
                    # Update result if edited
                    r["reply"] = edited

                    # Signals
                    if r["key_signals"]:
                        st.caption("🔍 สัญญาณ: " + " · ".join(r["key_signals"]))


if __name__ == "__main__":
    main()
