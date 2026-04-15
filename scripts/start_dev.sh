#!/usr/bin/env bash
# scripts/start_dev.sh — Start all dev services for ai-sales-bot (Linux / macOS / WSL)
set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-gemma4:e4b}"
FASTAPI_PORT=8000
STREAMLIT_PORT=8501

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }

# ── 1. Check / start Ollama ───────────────────────────────────────────────────
info "ตรวจสอบ Ollama..."

if ! command -v ollama &>/dev/null; then
  error "ไม่พบ Ollama — กรุณาติดตั้งก่อน: https://ollama.com/download"
  exit 1
fi

if ! curl -sf http://localhost:11434/api/tags &>/dev/null; then
  warn "Ollama ยังไม่รัน — กำลัง start..."
  ollama serve &>/dev/null &
  # รอให้ API พร้อม (สูงสุด 15 วินาที)
  for i in $(seq 1 15); do
    sleep 1
    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
      success "Ollama started แล้ว"
      break
    fi
    if [ "$i" -eq 15 ]; then
      error "Ollama start ไม่สำเร็จภายใน 15 วินาที"
      exit 1
    fi
  done
else
  success "Ollama กำลังรันอยู่แล้ว"
fi

# ── 2. Check / pull model ─────────────────────────────────────────────────────
info "ตรวจสอบ model ${OLLAMA_MODEL}..."

if ollama list 2>/dev/null | grep -q "^${OLLAMA_MODEL}"; then
  success "Model ${OLLAMA_MODEL} มีอยู่แล้ว"
else
  warn "ไม่พบ model ${OLLAMA_MODEL} — กำลัง pull (อาจใช้เวลาสักครู่)..."
  ollama pull "${OLLAMA_MODEL}"
  success "Pull ${OLLAMA_MODEL} เสร็จแล้ว"
fi

# ── 3. Check .env ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ ! -f ".env" ]; then
  warn "ไม่พบ .env — กำลัง copy จาก .env.example..."
  cp .env.example .env
  warn "กรุณาแก้ไข .env ใส่ token จริงก่อนใช้งาน"
fi

# ── 4. Start FastAPI ──────────────────────────────────────────────────────────
info "กำลัง start FastAPI ที่ port ${FASTAPI_PORT}..."
uvicorn main_api:app --host 0.0.0.0 --port "${FASTAPI_PORT}" --reload &
FASTAPI_PID=$!

# ── 5. Start Streamlit ────────────────────────────────────────────────────────
info "กำลัง start Streamlit ที่ port ${STREAMLIT_PORT}..."
streamlit run streamlit_app.py \
  --server.port "${STREAMLIT_PORT}" \
  --server.address 0.0.0.0 \
  --server.headless true &
STREAMLIT_PID=$!

# ── 6. Print URLs ─────────────────────────────────────────────────────────────
sleep 2
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  AI Sales Bot — Dev Server พร้อมใช้งานแล้ว!${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo -e "  ${CYAN}FastAPI  (webhook):${RESET}  http://localhost:${FASTAPI_PORT}"
echo -e "  ${CYAN}API Docs (Swagger):${RESET}  http://localhost:${FASTAPI_PORT}/docs"
echo -e "  ${CYAN}Streamlit (UI):    ${RESET}  http://localhost:${STREAMLIT_PORT}"
echo ""
echo -e "  ${YELLOW}Webhook endpoint:${RESET}    http://localhost:${FASTAPI_PORT}/webhook"
echo -e "  ${YELLOW}LINE endpoint:   ${RESET}    http://localhost:${FASTAPI_PORT}/webhook/line"
echo ""
echo -e "  ${BOLD}หากใช้ ngrok:${RESET}  ngrok http ${FASTAPI_PORT}"
echo -e "  ${BOLD}จากนั้นใช้ URL ที่ ngrok ให้ตั้งเป็น Webhook ใน Meta / LINE Console${RESET}"
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  กด ${RED}Ctrl+C${RESET} เพื่อหยุด server ทั้งหมด"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ── Cleanup on Ctrl+C ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  info "กำลัง stop services..."
  kill "$FASTAPI_PID" "$STREAMLIT_PID" 2>/dev/null || true
  success "หยุด server เรียบร้อย"
}
trap cleanup INT TERM

wait "$FASTAPI_PID" "$STREAMLIT_PID"
