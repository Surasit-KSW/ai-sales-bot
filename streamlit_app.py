"""
AI Sales Assistant — Operator Dashboard

Tabs:
  1. รออนุมัติ   — review and send pending replies
  2. N8N Monitor — workflow status and execution log
  3. Lead Board  — POTENTIAL_BUYER tracking and Google Sheets sync
  4. ประวัติ     — full message history with filters and CSV export

Run:
    streamlit run streamlit_app.py
"""

import csv
import io
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Sales Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core import database as db
from app.core.llm_client import OllamaClient
from app.core.profile_loader import load_profile
from app.integrations.facebook_api import FacebookAPI
from app.integrations.line_api import LineAPI
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator

# ── Bootstrap DB ──────────────────────────────────────────────────────────────
db.init_db()

# One-time JSON → SQLite migration
_PENDING_JSON = Path("data/pending_replies.json")
_HISTORY_JSON = Path("data/reply_history.json")
if (_PENDING_JSON.exists() or _HISTORY_JSON.exists()) and not Path("data/.migrated").exists():
    n = db.migrate_from_json(_PENDING_JSON, _HISTORY_JSON)
    if n:
        Path("data/.migrated").write_text(str(n))

# ── Constants ─────────────────────────────────────────────────────────────────
INTENT_CONFIG = {
    "POTENTIAL_BUYER": {"label": "🛒 ผู้สนใจซื้อ",   "color": "#28a745", "bg": "#d4edda"},
    "GENERAL_INQUIRY": {"label": "💬 สอบถามทั่วไป",  "color": "#0d6efd", "bg": "#cfe2ff"},
    "COMPLAINT":       {"label": "⚠️ ร้องเรียน",      "color": "#fd7e14", "bg": "#ffe5d0"},
    "SPAM":            {"label": "🚫 Spam",            "color": "#dc3545", "bg": "#f8d7da"},
}
SENTIMENT_EMOJI = {"positive": "😊", "neutral": "😐", "negative": "😟"}
CHANNEL_CONFIG = {
    "facebook": {"badge": "🔵 Facebook", "color": "#1877f2", "bg": "#e7f0fd"},
    "line":     {"badge": "🟢 LINE",     "color": "#06c755", "bg": "#e6f9ed"},
}
QR_OPTIONS = ["ดูสินค้าเพิ่มเติม", "ติดต่อแอดมิน", "ดูโปรโมชั่น"]

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.intent-badge, .channel-badge {
    display: inline-block; padding: 2px 10px; border-radius: 20px;
    font-size: 0.78rem; font-weight: 600; margin-right: 4px; margin-bottom: 4px;
}
.comment-card {
    background: #f8f9fa; border-left: 4px solid #dee2e6;
    padding: 10px 14px; border-radius: 0 8px 8px 0; margin-bottom: 6px; font-size: 0.95rem;
}
.stat-box { text-align:center; padding:12px; border-radius:10px; background:#f8f9fa; margin:4px 0; }
.stat-number { font-size:1.8rem; font-weight:700; }
.stat-label  { font-size:0.75rem; color:#6c757d; }
.qr-section  {
    background:#f0f9f4; border:1px solid #b7e4c7; border-radius:8px; padding:8px 12px; margin:6px 0;
}
.status-dot-green { color:#28a745; font-size:0.9rem; }
.status-dot-red   { color:#dc3545; font-size:0.9rem; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ── Cached resources ──────────────────────────────────────────────────────────
@st.cache_resource
def get_client() -> OllamaClient:
    return OllamaClient()

@st.cache_resource
def get_profile():
    return load_profile()

@st.cache_resource
def get_services():
    client = get_client()
    profile = get_profile()
    return CommentAnalyzer(client=client, profile=profile), ReplyGenerator(client=client, profile=profile)

@st.cache_resource
def get_fb_api() -> FacebookAPI:
    return FacebookAPI()

@st.cache_resource
def get_line_api() -> LineAPI:
    return LineAPI()


# ── Service health checks ─────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def check_ollama() -> bool:
    return get_client().is_healthy()

@st.cache_data(ttl=30)
def check_fastapi() -> bool:
    try:
        r = requests.get("http://localhost:8000/health", timeout=3)
        return r.ok
    except Exception:
        return False

@st.cache_data(ttl=30)
def check_n8n() -> bool:
    n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
    try:
        r = requests.get(f"{n8n_url}/healthz", timeout=3)
        return r.ok
    except Exception:
        return False

@st.cache_data(ttl=300)
def fetch_line_bot_info(token: str) -> dict:
    if not token:
        return {}
    try:
        r = requests.get(
            "https://api.line.me/v2/bot/info",
            headers={"Authorization": f"Bearer {token}"}, timeout=5,
        )
        return r.json() if r.ok else {}
    except Exception:
        return {}

@st.cache_data(ttl=300)
def fetch_line_followers(token: str) -> int | None:
    if not token:
        return None
    try:
        r = requests.get(
            "https://api.line.me/v2/bot/followers/count",
            headers={"Authorization": f"Bearer {token}"}, timeout=5,
        )
        if r.ok:
            data = r.json()
            if data.get("status") == "ready":
                return data.get("count")
    except Exception:
        pass
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────
def channel_badge_html(channel: str) -> str:
    cfg = CHANNEL_CONFIG.get(channel, CHANNEL_CONFIG["facebook"])
    return f'<span class="channel-badge" style="background:{cfg["bg"]};color:{cfg["color"]}">{cfg["badge"]}</span>'

def intent_badge_html(intent: str) -> str:
    cfg = INTENT_CONFIG.get(intent, {"label": intent, "color": "#6c757d", "bg": "#e9ecef"})
    return f'<span class="intent-badge" style="background:{cfg["bg"]};color:{cfg["color"]}">{cfg["label"]}</span>'

def fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%y %H:%M")
    except Exception:
        return ""

def is_auto_reply(channel: str = "") -> bool:
    key = f"AUTO_REPLY_{channel.upper()}" if channel else "AUTO_REPLY"
    val = os.environ.get(key, os.environ.get("AUTO_REPLY", "False"))
    return val.strip().lower() == "true"

def set_auto_reply(channel: str, enabled: bool) -> None:
    key = f"AUTO_REPLY_{channel.upper()}"
    os.environ[key] = "True" if enabled else "False"


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    profile = get_profile()
    fb_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

    with st.sidebar:
        # Shop identity
        st.markdown("## 🤖 AI Sales Assistant")
        with st.container(border=True):
            st.markdown(f"### 🏪 {profile.shop_name}")
            if profile.tagline:
                st.caption(profile.tagline)
            if profile.platform:
                st.caption(f"📱 {profile.platform}")

        st.divider()

        # ── Service status ─────────────────────────────────────────
        st.markdown("**สถานะระบบ**")

        col1, col2 = st.columns(2)
        with col1:
            ollama_ok = check_ollama()
            st.markdown(
                f'<span class="{"status-dot-green" if ollama_ok else "status-dot-red"}">{"🟢" if ollama_ok else "🔴"} Ollama</span>',
                unsafe_allow_html=True,
            )
            fastapi_ok = check_fastapi()
            st.markdown(
                f'<span class="{"status-dot-green" if fastapi_ok else "status-dot-red"}">{"🟢" if fastapi_ok else "🔴"} FastAPI</span>',
                unsafe_allow_html=True,
            )
        with col2:
            n8n_ok = check_n8n()
            st.markdown(
                f'<span class="{"status-dot-green" if n8n_ok else "status-dot-red"}">{"🟢" if n8n_ok else "🔴"} N8N</span>',
                unsafe_allow_html=True,
            )
            fb_ok = bool(fb_token)
            st.markdown(
                f'<span class="{"status-dot-green" if fb_ok else "status-dot-red"}">{"🟢" if fb_ok else "🔴"} Facebook</span>',
                unsafe_allow_html=True,
            )

        if line_token:
            bot_info = fetch_line_bot_info(line_token)
            display_name = bot_info.get("displayName", "")
            if display_name:
                st.caption(f"🟢 LINE: `{display_name}`")
            else:
                st.caption("🟢 LINE เชื่อมต่อแล้ว")
            followers = fetch_line_followers(line_token)
            if followers is not None:
                st.metric("LINE Followers", f"{followers:,}")
        else:
            st.caption("🔴 LINE: ยังไม่เชื่อมต่อ")

        st.divider()

        # ── Auto-Reply toggles (per-channel) ──────────────────────
        st.markdown("**การตอบกลับอัตโนมัติ**")
        fb_auto = st.toggle(
            "🔵 Facebook",
            value=is_auto_reply("facebook"),
            key="toggle_fb",
            help="เปิด = AI ตอบ Facebook ทันที ปิด = รออนุมัติ",
        )
        line_auto = st.toggle(
            "🟢 LINE",
            value=is_auto_reply("line"),
            key="toggle_line",
            help="เปิด = AI ตอบ LINE ทันที ปิด = รออนุมัติ",
        )
        if fb_auto != is_auto_reply("facebook"):
            set_auto_reply("facebook", fb_auto)
            st.rerun()
        if line_auto != is_auto_reply("line"):
            set_auto_reply("line", line_auto)
            st.rerun()

        st.divider()

        # ── Today stats ────────────────────────────────────────────
        st.markdown("**วันนี้**")
        stats = db.get_today_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Messages", stats["total"])
        c2.metric("ส่งแล้ว", stats["replied"])
        c3.metric("รออยู่", stats["pending"])

        st.divider()

        # Last refresh time
        st.caption(f"อัพเดทล่าสุด: {datetime.now().strftime('%H:%M น.')}")


# ── Tab 1: รออนุมัติ ──────────────────────────────────────────────────────────
def render_pending_tab():
    # Process queued actions before rendering widgets
    if st.session_state.get("pending_actions"):
        for item_id, (action, final_reply, item) in list(st.session_state.pending_actions.items()):
            if action == "sent":
                ch = item.get("channel", "facebook")
                if ch == "facebook":
                    comment_id = item.get("comment_id", "")
                    if comment_id and os.environ.get("FB_PAGE_ACCESS_TOKEN"):
                        get_fb_api().post_comment_reply(comment_id, final_reply)
                elif ch == "line":
                    user_id = item.get("user_id", "")
                    if user_id:
                        qr_opts = [
                            QR_OPTIONS[i] for i in range(len(QR_OPTIONS))
                            if st.session_state.get(f"qr_{item_id}_{i}", False)
                        ]
                        if qr_opts:
                            get_line_api().push_quick_reply(user_id, final_reply, qr_opts)
                        else:
                            get_line_api().push_message(user_id, final_reply)

            escalated = action == "escalated"
            db.update_message_status(
                item_id,
                status="escalated" if escalated else action,
                final_reply=final_reply,
                escalated=escalated,
            )

        st.session_state.pending_actions = {}
        st.rerun()

    # ── Filters ────────────────────────────────────────────────────────
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.subheader("🕐 รออนุมัติ")
    with col_refresh:
        if st.button("🔄", use_container_width=True, help="รีเฟรช"):
            st.rerun()

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ch_filter = st.radio(
            "ช่องทาง",
            ["ทั้งหมด", "🔵 Facebook", "🟢 LINE"],
            horizontal=True, key="pend_ch", label_visibility="collapsed",
        )
    with col_f2:
        intent_filter = st.radio(
            "Intent",
            ["ทั้งหมด", "⚠️ ร้องเรียน", "🛒 ผู้สนใจ"],
            horizontal=True, key="pend_intent", label_visibility="collapsed",
        )

    ch_map = {"🔵 Facebook": "facebook", "🟢 LINE": "line"}
    intent_map = {"⚠️ ร้องเรียน": "COMPLAINT", "🛒 ผู้สนใจ": "POTENTIAL_BUYER"}

    pending = db.get_pending(
        channel=ch_map.get(ch_filter),
        intent=intent_map.get(intent_filter),
    )

    st.caption(f"{len(pending)} รายการรออยู่")

    if not pending:
        st.info("ไม่มี message รออนุมัติ — รายการใหม่จาก Facebook / LINE จะปรากฏที่นี่")
        _render_test_input()
        return

    # ── Cards ───────────────────────────────────────────────────────────
    for item in pending:
        item_id = item["id"]
        conf = int(item.get("confidence", 0) * 100)
        ch = item.get("channel", "facebook")
        sent_emoji = SENTIMENT_EMOJI.get(item.get("sentiment", ""), "")

        with st.container(border=True):
            col_name, col_meta = st.columns([3, 2])
            with col_name:
                st.markdown(
                    channel_badge_html(ch) + intent_badge_html(item.get("intent", "")),
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{item.get('user_name') or 'ไม่ทราบชื่อ'}**")
            with col_meta:
                st.caption(
                    f"Confidence: **{conf}%** &nbsp; "
                    f"{sent_emoji} {item.get('sentiment','')} &nbsp; "
                    f"รับเมื่อ: {fmt_dt(item.get('timestamp',''))}"
                )

            st.markdown(
                f'<div class="comment-card">💬 {item.get("text", "")}</div>',
                unsafe_allow_html=True,
            )
            signals = item.get("key_signals", [])
            if signals:
                st.caption("🔍 " + " · ".join(signals))

            if item.get("is_escalated"):
                st.error("🚨 Escalated — รอการติดต่อจากทีมงาน")
                continue

            if item.get("intent") == "SPAM":
                col_skip, _ = st.columns([1, 3])
                with col_skip:
                    if st.button("❌ นำออก", key=f"skip_spam_{item_id}", use_container_width=True):
                        _queue_action(item_id, "skipped", "", item)
                continue

            if item.get("error") and not item.get("reply"):
                st.error(f"❌ AI ตอบไม่ได้: {item['error']}")
                col_skip, _ = st.columns([1, 3])
                with col_skip:
                    if st.button("❌ ข้าม", key=f"skip_err_{item_id}", use_container_width=True):
                        _queue_action(item_id, "skipped", "", item)
                continue

            edited = st.text_area(
                "คำตอบ", value=item.get("reply", ""),
                height=100, key=f"reply_{item_id}", label_visibility="collapsed",
            )

            if ch == "line":
                st.markdown(
                    '<div class="qr-section">📲 <strong>Quick Reply Buttons</strong> (ไม่บังคับ)</div>',
                    unsafe_allow_html=True,
                )
                qr_cols = st.columns(len(QR_OPTIONS))
                for i, (qr_col, opt) in enumerate(zip(qr_cols, QR_OPTIONS)):
                    with qr_col:
                        st.checkbox(opt, key=f"qr_{item_id}_{i}")

            col_send, col_edit, col_skip, col_esc = st.columns(4)
            with col_send:
                if st.button("✅ ส่ง", key=f"send_{item_id}", type="primary", use_container_width=True):
                    _queue_action(item_id, "sent", edited, item)
            with col_edit:
                if st.button("✏️ บันทึก", key=f"save_{item_id}", use_container_width=True):
                    db.update_message_status(item_id, "pending", edited)
                    st.toast("บันทึกแล้ว", icon="✏️")
                    st.rerun()
            with col_skip:
                if st.button("❌ ข้าม", key=f"skip_{item_id}", use_container_width=True):
                    _queue_action(item_id, "skipped", "", item)
            with col_esc:
                if st.button("🚨 Escalate", key=f"esc_{item_id}", use_container_width=True):
                    _queue_action(item_id, "escalated", "", item)

    st.divider()
    _render_test_input()


def _queue_action(item_id: str, action: str, reply: str, item: dict) -> None:
    if "pending_actions" not in st.session_state:
        st.session_state.pending_actions = {}
    st.session_state.pending_actions[item_id] = (action, reply, item)
    st.rerun()


def _render_test_input():
    with st.expander("➕ เพิ่ม comment ทดสอบ"):
        col_ch, col_name = st.columns([1, 2])
        with col_ch:
            test_channel = st.selectbox(
                "ช่องทาง", ["facebook", "line"], key="test_ch",
                format_func=lambda c: "🔵 Facebook" if c == "facebook" else "🟢 LINE",
            )
        with col_name:
            test_name = st.text_input("ชื่อ", value="ลูกค้าทดสอบ", key="test_name")
        test_comment = st.text_input(
            "ข้อความ", placeholder="ราคาเท่าไหร่คะ มีโปรไหม", key="test_comment",
        )
        if st.button("▶ วิเคราะห์และเพิ่มใน Queue", type="primary", key="test_add"):
            if not test_comment.strip():
                st.warning("กรุณาใส่ข้อความ")
                return
            if not check_ollama():
                st.error("Ollama ออฟไลน์")
                return
            with st.spinner("กำลังวิเคราะห์…"):
                analyzer, generator = get_services()
                analysis = analyzer.analyze(test_comment.strip())
                result = generator.generate(analysis)
            db.save_message({
                "id": str(uuid.uuid4()),
                "channel": test_channel,
                "comment_id": "",
                "user_id": "test_user_id" if test_channel == "line" else "",
                "user_name": test_name or "ลูกค้าทดสอบ",
                "text": test_comment.strip(),
                "intent": analysis.intent,
                "confidence": round(analysis.confidence, 2),
                "sentiment": analysis.sentiment,
                "key_signals": analysis.key_signals,
                "reply": result.reply,
                "error": result.error or analysis.error,
                "status": "pending",
                "timestamp": datetime.now().isoformat(),
            })
            st.success(f"เพิ่มใน queue — Intent: {analysis.intent}")
            st.rerun()


# ── Tab 2: N8N Monitor ────────────────────────────────────────────────────────
def render_n8n_tab():
    n8n_base = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
    api_key = os.getenv("N8N_API_KEY", "")

    col_status, col_link = st.columns([2, 3])
    with col_status:
        n8n_ok = check_n8n()
        if n8n_ok:
            st.success("🟢 N8N กำลังทำงาน")
        else:
            st.error("🔴 N8N ออฟไลน์")
            st.code(f'scripts\\start_n8n.bat  # หรือ\n"C:/npm_global/n8n.cmd" start')
    with col_link:
        st.info(f"**N8N Dashboard:** [เปิดในเบราว์เซอร์]({n8n_base})")
        if not api_key:
            st.caption("ตั้งค่า `N8N_API_KEY` ใน `.env` เพื่อดู workflow status ที่นี่")

    st.divider()

    # ── Workflow list (requires N8N_API_KEY) ─────────────────────────────
    if api_key and n8n_ok:
        headers = {"X-N8N-API-KEY": api_key, "Accept": "application/json"}

        st.subheader("Workflows")
        try:
            resp = requests.get(f"{n8n_base}/api/v1/workflows", headers=headers, timeout=5)
            if resp.ok:
                workflows = resp.json().get("data", [])
                for wf in workflows:
                    col_name, col_status_wf, col_btn = st.columns([3, 1, 1])
                    with col_name:
                        st.write(f"**{wf.get('name', 'Unnamed')}**")
                    with col_status_wf:
                        active = wf.get("active", False)
                        st.markdown(
                            f'<span style="color:{"#28a745" if active else "#dc3545"}">{"● Active" if active else "● Inactive"}</span>',
                            unsafe_allow_html=True,
                        )
                    with col_btn:
                        wf_id = wf.get("id", "")
                        if wf_id and st.button("▶ Trigger", key=f"trigger_{wf_id}", use_container_width=True):
                            try:
                                run_resp = requests.post(
                                    f"{n8n_base}/api/v1/workflows/{wf_id}/run",
                                    headers=headers, json={}, timeout=10,
                                )
                                if run_resp.ok:
                                    st.toast(f"Triggered: {wf.get('name')}", icon="▶")
                                else:
                                    st.warning(f"Failed: {run_resp.status_code}")
                            except Exception as e:
                                st.warning(f"Error: {e}")
            else:
                st.warning(f"N8N API returned {resp.status_code} — ตรวจสอบ N8N_API_KEY")
        except Exception as exc:
            st.warning(f"ไม่สามารถดึง workflow list: {exc}")

        st.divider()

        # ── Execution log ──────────────────────────────────────────────
        st.subheader("Execution Log (10 รายการล่าสุด)")
        try:
            exec_resp = requests.get(
                f"{n8n_base}/api/v1/executions?limit=10&includeData=false",
                headers=headers, timeout=5,
            )
            if exec_resp.ok:
                executions = exec_resp.json().get("data", [])
                if executions:
                    for ex in executions:
                        status = ex.get("status", "unknown")
                        status_color = {"success": "#28a745", "error": "#dc3545", "running": "#fd7e14"}.get(status, "#6c757d")
                        started = ex.get("startedAt", "")
                        wf_name = ex.get("workflowData", {}).get("name", ex.get("workflowId", "?"))
                        st.markdown(
                            f'<div style="padding:4px 0; border-bottom:1px solid #eee">'
                            f'<span style="color:{status_color}">● {status.upper()}</span> &nbsp; '
                            f'<strong>{wf_name}</strong> &nbsp; '
                            f'<span style="color:#888; font-size:0.85rem">{fmt_dt(started)}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("ยังไม่มี execution")
        except Exception as exc:
            st.warning(f"ไม่สามารถดึง execution log: {exc}")

    else:
        # No API key — show workflow guide
        st.subheader("Workflows ในโปรเจกต์นี้")
        workflows_info = [
            ("01_facebook_router", "Facebook Comment Router", "รับ comment FB → AI → ตอบกลับ"),
            ("02_line_router",     "LINE Message Router",     "รับ message LINE → AI → ตอบกลับ"),
            ("03_lead_capture",    "Lead Capture",             "บันทึก leads ลง Google Sheets"),
            ("04_owner_notify",    "Owner Notification",       "แจ้งเจ้าของร้านทาง LINE Notify"),
            ("05_error_handler",   "Error Handler",            "จัดการ errors ทั้งระบบ"),
        ]
        for file, name, desc in workflows_info:
            with st.container(border=True):
                st.markdown(f"**{name}**  \n{desc}  \n`n8n/workflows/{file}.json`")

        st.divider()
        st.subheader("วิธีเปิดใช้ N8N API")
        st.code("""# เพิ่มใน .env
N8N_API_KEY=your_api_key_here

# รับ API key จาก N8N:
# Settings → API → Create API Key""")

    # ── System errors from DB ──────────────────────────────────────────
    errors = db.get_errors(limit=10)
    if errors:
        st.divider()
        st.subheader("System Errors (10 ล่าสุด)")
        for err in errors:
            st.error(
                f"**{err.get('type','')}** | {err.get('source','')} | "
                f"{fmt_dt(err.get('timestamp',''))}  \n{err.get('detail','')}"
            )


# ── Tab 3: Lead Board ─────────────────────────────────────────────────────────
def render_leads_tab():
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.subheader("🛒 Lead Board")
    with col_refresh:
        if st.button("🔄", key="leads_refresh", use_container_width=True):
            st.rerun()

    leads = db.get_leads()
    if not leads:
        st.info("ยังไม่มี leads — เมื่อมี POTENTIAL_BUYER message เข้ามา จะปรากฏที่นี่")
        return

    # ── Stats ──────────────────────────────────────────────────────────
    total_leads = len(leads)
    contacted   = sum(1 for l in leads if l.get("contacted"))
    pending_contact = total_leads - contacted
    fb_leads    = sum(1 for l in leads if l.get("channel") == "facebook")
    line_leads  = sum(1 for l in leads if l.get("channel") == "line")

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, num, label, color in [
        (c1, total_leads,      "Leads ทั้งหมด",  "#0d6efd"),
        (c2, pending_contact,  "รอติดต่อ",        "#fd7e14"),
        (c3, contacted,        "ติดต่อแล้ว",      "#28a745"),
        (c4, fb_leads,         "🔵 Facebook",     "#1877f2"),
        (c5, line_leads,       "🟢 LINE",          "#06c755"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-number" style="color:{color}">{num}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Filters ────────────────────────────────────────────────────────
    col_f1, col_f2, col_export, col_sync = st.columns([2, 2, 1, 1])
    with col_f1:
        filter_status = st.selectbox(
            "สถานะ", ["ทั้งหมด", "รอติดต่อ", "ติดต่อแล้ว"], key="lead_status_filter",
        )
    with col_f2:
        filter_ch = st.selectbox(
            "ช่องทาง", ["ทั้งหมด", "🔵 Facebook", "🟢 LINE"], key="lead_ch_filter",
        )
    with col_export:
        csv_data = _export_leads_csv(leads)
        st.download_button(
            "📥 CSV", data=csv_data,
            file_name=f"leads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv", use_container_width=True,
        )
    with col_sync:
        if st.button("☁ Sync N8N", use_container_width=True, help="ส่ง leads ที่ยังไม่ได้ sync ไปยัง N8N workflow 03"):
            _sync_leads_to_n8n(leads)

    # Apply filters
    if filter_status == "รอติดต่อ":
        leads = [l for l in leads if not l.get("contacted")]
    elif filter_status == "ติดต่อแล้ว":
        leads = [l for l in leads if l.get("contacted")]
    ch_filter_map = {"🔵 Facebook": "facebook", "🟢 LINE": "line"}
    if filter_ch in ch_filter_map:
        leads = [l for l in leads if l.get("channel") == ch_filter_map[filter_ch]]

    # ── Lead cards ─────────────────────────────────────────────────────
    for lead in leads:
        msg_id = lead.get("message_id", "")
        contacted_flag = bool(lead.get("contacted"))
        ch = lead.get("channel", "facebook")

        with st.container(border=True):
            col_info, col_action = st.columns([4, 1])
            with col_info:
                st.markdown(
                    channel_badge_html(ch) +
                    f' <strong>{lead.get("user_name") or "ไม่ทราบชื่อ"}</strong>'
                    f' <span style="color:#888; font-size:0.85rem">{fmt_dt(lead.get("created_at",""))}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="comment-card">💬 {lead.get("product_interest","")}</div>',
                    unsafe_allow_html=True,
                )
                conf = int(float(lead.get("confidence", 0)) * 100)
                st.caption(f"Confidence: {conf}% · {SENTIMENT_EMOJI.get(lead.get('sentiment',''), '')} {lead.get('sentiment','')}")
            with col_action:
                new_contacted = st.checkbox(
                    "ติดต่อแล้ว",
                    value=contacted_flag,
                    key=f"lead_contacted_{msg_id}",
                )
                if new_contacted != contacted_flag and msg_id:
                    db.update_lead_contacted(msg_id, new_contacted)
                    st.rerun()


def _export_leads_csv(leads: list) -> bytes:
    fields = ["created_at", "channel", "user_name", "product_interest", "confidence", "contacted", "status"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for l in leads:
        writer.writerow({
            "created_at":       fmt_dt(l.get("created_at", "")),
            "channel":          l.get("channel", ""),
            "user_name":        l.get("user_name", ""),
            "product_interest": l.get("product_interest", ""),
            "confidence":       f"{int(float(l.get('confidence', 0)) * 100)}%",
            "contacted":        "ใช่" if l.get("contacted") else "ไม่",
            "status":           l.get("status", ""),
        })
    return buf.getvalue().encode("utf-8-sig")


def _sync_leads_to_n8n(leads: list) -> None:
    """POST unsent leads to N8N workflow 03 (lead-capture)."""
    n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678")
    endpoint = f"{n8n_url}/webhook/lead-capture"
    sent = 0
    errors = 0
    for lead in leads:
        if lead.get("contacted"):
            continue
        try:
            r = requests.post(endpoint, json={
                "channel":   lead.get("channel"),
                "user_id":   lead.get("user_id"),
                "user_name": lead.get("user_name"),
                "text":      lead.get("product_interest"),
                "intent":    "POTENTIAL_BUYER",
                "timestamp": lead.get("created_at"),
            }, timeout=5)
            if r.ok:
                sent += 1
            else:
                errors += 1
        except Exception:
            errors += 1

    if sent:
        st.success(f"Synced {sent} leads ไปยัง N8N")
    if errors:
        st.warning(f"{errors} leads ส่งไม่ได้ — N8N อาจออฟไลน์")


# ── Tab 4: ประวัติ ─────────────────────────────────────────────────────────────
def render_history_tab():
    col_title, col_export = st.columns([5, 1])
    with col_title:
        st.subheader("📋 ประวัติ")

    # ── Filters ────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_ch = st.selectbox(
            "ช่องทาง", ["ทั้งหมด", "🔵 Facebook", "🟢 LINE"], key="hist_ch",
        )
    with col_f2:
        filter_intent = st.selectbox(
            "Intent",
            ["ทั้งหมด", "🛒 ผู้สนใจซื้อ", "💬 สอบถาม", "⚠️ ร้องเรียน", "🚫 Spam"],
            key="hist_intent",
        )
    with col_f3:
        date_from = st.date_input("จากวันที่", value=None, key="hist_date_from")
    with col_f4:
        keyword = st.text_input("ค้นหา", placeholder="ชื่อ / ข้อความ", key="hist_keyword")

    ch_map = {"🔵 Facebook": "facebook", "🟢 LINE": "line"}
    intent_map = {
        "🛒 ผู้สนใจซื้อ": "POTENTIAL_BUYER",
        "💬 สอบถาม":      "GENERAL_INQUIRY",
        "⚠️ ร้องเรียน":   "COMPLAINT",
        "🚫 Spam":         "SPAM",
    }

    history = db.get_history(
        channel=ch_map.get(filter_ch),
        intent=intent_map.get(filter_intent),
        keyword=keyword.strip() or None,
        date_from=date_from.isoformat() if date_from else None,
    )

    # ── Summary stats ──────────────────────────────────────────────────
    sent_c  = sum(1 for h in history if h.get("status") == "sent")
    skip_c  = sum(1 for h in history if h.get("status") == "skipped")
    esc_c   = sum(1 for h in history if h.get("status") == "escalated")
    buyer_c = sum(1 for h in history if h.get("intent") == "POTENTIAL_BUYER")
    comp_c  = sum(1 for h in history if h.get("intent") == "COMPLAINT")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, num, label, color in [
        (c1, len(history), "ทั้งหมด",       "#495057"),
        (c2, sent_c,       "✅ ส่งแล้ว",    "#28a745"),
        (c3, skip_c,       "❌ ข้าม",        "#dc3545"),
        (c4, esc_c,        "🚨 Escalated",   "#fd7e14"),
        (c5, buyer_c,      "🛒 ผู้สนใจซื้อ", "#0d6efd"),
        (c6, comp_c,       "⚠️ ร้องเรียน",   "#e83e8c"),
    ]:
        col.markdown(
            f'<div class="stat-box"><div class="stat-number" style="color:{color}">{num}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Export button
    if history:
        csv_bytes = _export_history_csv(history)
        st.download_button(
            "📥 Export CSV",
            data=csv_bytes,
            file_name=f"history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    if not history:
        st.info("ไม่มีข้อมูลในช่วงเวลาที่เลือก")
        return

    # ── History cards ──────────────────────────────────────────────────
    for item in history:
        status = item.get("status", "")
        status_label = {
            "sent":      "✅ ส่งแล้ว",
            "skipped":   "❌ ข้ามแล้ว",
            "escalated": "🚨 Escalated",
        }.get(status, status)
        conf = int(item.get("confidence", 0) * 100)
        ch = item.get("channel", "facebook")

        with st.container(border=True):
            col_badge, col_status, col_time = st.columns([3, 2, 2])
            with col_badge:
                st.markdown(
                    channel_badge_html(ch) + intent_badge_html(item.get("intent", "")),
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{item.get('user_name') or 'ไม่ทราบชื่อ'}**")
            with col_status:
                st.markdown(status_label)
                st.caption(f"Confidence: {conf}%")
            with col_time:
                st.caption(f"เมื่อ: {fmt_dt(item.get('timestamp',''))}")

            st.markdown(
                f'<div class="comment-card">💬 {item.get("text","")}</div>',
                unsafe_allow_html=True,
            )

            reply = item.get("reply", "")
            if reply and status != "skipped":
                with st.expander("ดูคำตอบที่ส่ง"):
                    st.write(reply)


def _export_history_csv(history: list) -> bytes:
    fields = ["timestamp", "channel", "user_name", "text", "intent", "sentiment",
              "confidence", "status", "reply"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in history:
        writer.writerow({
            "timestamp":  fmt_dt(item.get("timestamp", "")),
            "channel":    item.get("channel", ""),
            "user_name":  item.get("user_name", ""),
            "text":       item.get("text", ""),
            "intent":     item.get("intent", ""),
            "sentiment":  item.get("sentiment", ""),
            "confidence": f"{int(item.get('confidence', 0) * 100)}%",
            "status":     item.get("status", ""),
            "reply":      item.get("reply", ""),
        })
    return buf.getvalue().encode("utf-8-sig")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if "pending_actions" not in st.session_state:
        st.session_state.pending_actions = {}

    render_sidebar()

    st.title("🤖 AI Sales Assistant")
    st.caption("ระบบตรวจสอบและอนุมัติคำตอบก่อนส่งลูกค้า Facebook & LINE")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🕐 รออนุมัติ",
        "⚙️ N8N Monitor",
        "🛒 Lead Board",
        "📋 ประวัติ",
    ])

    with tab1:
        render_pending_tab()
    with tab2:
        render_n8n_tab()
    with tab3:
        render_leads_tab()
    with tab4:
        render_history_tab()

    # ── Auto-refresh every 30 seconds ────────────────────────────────
    time.sleep(30)
    st.rerun()


if __name__ == "__main__":
    main()
