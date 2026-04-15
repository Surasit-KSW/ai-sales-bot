"""
Demo Script — AI Sales Assistant v2
Runs 6 sample comments covering all intents including escalation.
Use this to quickly showcase the system to clients.

Run:
    python demo.py
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.llm_client import OllamaClient
from app.core.profile_loader import load_profile
from app.services.analyzer import CommentAnalyzer
from app.services.generator import ReplyGenerator

# ── ANSI Colors ──────────────────────────────────────────────────────────────
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
MAGENTA = "\033[95m"
RESET  = "\033[0m"

INTENT_COLOR = {
    "POTENTIAL_BUYER": GREEN,
    "GENERAL_INQUIRY": CYAN,
    "COMPLAINT":       YELLOW,
    "SPAM":            RED,
}

# ── Demo Comments (6 cases covering all intents + escalation) ─────────────────
DEMO_COMMENTS = [
    "ราคาเท่าไหร่คะ มีโปรไหม อยากได้สีดำ",
    "ผ้าทำจากอะไรคะ แพ้ง่ายอยากรู้ก่อนสั่ง",
    "ซื้อ 3 ชิ้นได้ส่วนลดไหมครับ จะซื้อให้แม่กับน้องด้วย",
    "สั่งไป 5 วันแล้วยังไม่ได้ของเลยค่ะ ติดต่อยังไงคะ",
    "อยากคืนเงินค่ะ รู้สึกว่าโกงเลย สินค้าไม่ตรงปก",
    "คลิกรับเงินฟรี >> bit.ly/xxxx ด่วนก่อนหมดเขต!!!",
]


def print_header(profile) -> None:
    width = 66
    print(f"\n{BOLD}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}{'  🤖  AI SALES ASSISTANT — DEMO v2':^{width}}{RESET}")
    print(f"{BOLD}{CYAN}{f'  ร้าน: {profile.shop_name}  |  {profile.tagline}':^{width}}{RESET}")
    print(f"{BOLD}{'═' * width}{RESET}\n")


def print_profile_summary(profile) -> None:
    """Show a summary of what's loaded from shop_profile.yaml."""
    print(f"{BOLD}📋 Shop Profile Summary{RESET}")
    print(f"  ร้าน       : {profile.shop_name}")
    print(f"  สโลแกน    : {profile.tagline}")
    print(f"  หมวดสินค้า : {len(profile.categories)} หมวด")
    for cat in profile.categories:
        bs_names = ", ".join(b.name for b in cat.bestsellers) if cat.bestsellers else "-"
        print(f"    • {cat.name} ({cat.price_range}) — ขายดี: {bs_names}")
    print(f"  โปรโมชั่น  : {len(profile.promotions.current)} รายการ")
    for p in profile.promotions.current:
        print(f"    • {p.title}: {p.detail}")
    print(f"  FAQ        : {len(profile.faqs)} ข้อ")
    for faq in profile.faqs:
        print(f"    Q: {faq.question}")
    pol = profile.policies
    print(f"  นโยบาย    : คืน={bool(pol.return_policy)} | เปลี่ยน={bool(pol.exchange)} | ประกัน={bool(pol.warranty)}")
    print(f"  Escalation : {len(profile.escalation.trigger_keywords)} คำ trigger → {profile.escalation.action}")
    print(f"  ติดต่อ     : LINE {profile.contact.line_id} | {profile.contact.hours}")
    print()


def print_result(
    idx: int,
    comment: str,
    intent: str,
    confidence: float,
    reply: str,
    was_skipped: bool,
    is_escalated: bool,
) -> None:
    color = INTENT_COLOR.get(intent, RESET)
    print(f"{BOLD}── Comment {idx} {'─'*50}{RESET}")
    print(f"  {BLUE}💬 ลูกค้า   :{RESET} {comment}")
    print(f"  {color}🏷  Intent   : [{intent}] ({confidence:.0%} confidence){RESET}")

    if is_escalated:
        print(f"  {MAGENTA}🚨 Reply    : [ESCALATED] ส่งต่อให้ทีมงานตรวจสอบ — ไม่ตอบอัตโนมัติ{RESET}")
    elif was_skipped:
        print(f"  {RED}⏭  Reply    : (ข้าม — SPAM){RESET}")
    else:
        print(f"  {GREEN}✉  Reply    :{RESET}")
        words = reply.replace("\n", " ").split()
        line, lines = "", []
        for w in words:
            if len(line) + len(w) + 1 > 60:
                lines.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            lines.append(line)
        for ln in lines:
            print(f"             {ln}")
    print()


def run_demo() -> None:
    profile = load_profile()
    print_header(profile)
    print_profile_summary(profile)

    # Health check
    client = OllamaClient()
    if not client.is_healthy():
        print(f"{RED}✗ Ollama is not running. Please run: ollama serve{RESET}")
        sys.exit(1)

    print(f"  {GREEN}✓ Ollama connected{RESET}  |  model: {client.model}")
    print(f"  {GREEN}✓ Shop profile loaded{RESET}  |  {profile.shop_name}")
    print(f"\n  Processing {len(DEMO_COMMENTS)} demo comments…\n")

    analyzer  = CommentAnalyzer(client=client, profile=profile)
    generator = ReplyGenerator(client=client, profile=profile)

    for idx, comment in enumerate(DEMO_COMMENTS, 1):
        print(f"  ⏳ [{idx}/{len(DEMO_COMMENTS)}] Analyzing…", end="\r")
        analysis  = analyzer.analyze(comment)
        generated = generator.generate(analysis)

        print_result(
            idx=idx,
            comment=comment,
            intent=analysis.intent,
            confidence=analysis.confidence,
            reply=generated.reply,
            was_skipped=generated.was_skipped,
            is_escalated=generated.is_escalated,
        )

    # Footer
    print(f"{BOLD}{'═' * 66}{RESET}")
    print(f"{BOLD}{GREEN}  ✅ Demo complete!{RESET}")
    print(f"  แก้ข้อมูลร้านได้ที่  →  {BOLD}shop_profile.yaml{RESET}")
    print(f"  รันกับข้อมูลจริง   →  {BOLD}python main.py{RESET}")
    print(f"{BOLD}{'═' * 66}{RESET}\n")


if __name__ == "__main__":
    run_demo()
