@echo off
:: scripts/start_dev.bat — Start all dev services for ai-sales-bot (Windows)
setlocal EnableDelayedExpansion

set OLLAMA_MODEL=gemma4:e4b
set FASTAPI_PORT=8000
set STREAMLIT_PORT=8501

echo.
echo [INFO]  AI Sales Bot — Dev Startup Script
echo ============================================================

:: ── 1. Check Ollama installed ─────────────────────────────────────────────────
echo [INFO]  ตรวจสอบ Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ไม่พบ Ollama
    echo         กรุณาติดตั้งที่: https://ollama.com/download
    pause
    exit /b 1
)

:: ── 2. Check Ollama running ───────────────────────────────────────────────────
curl -sf http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [WARN]  Ollama ยังไม่รัน — กำลัง start...
    start "" /B ollama serve
    :: รอ 10 วินาทีให้ Ollama พร้อม
    set /a WAIT=0
    :wait_ollama
    timeout /t 1 /nobreak >nul
    curl -sf http://localhost:11434/api/tags >nul 2>&1
    if not errorlevel 1 goto ollama_ready
    set /a WAIT+=1
    if !WAIT! lss 15 goto wait_ollama
    echo [ERROR] Ollama start ไม่สำเร็จภายใน 15 วินาที
    pause
    exit /b 1
    :ollama_ready
    echo [OK]    Ollama started แล้ว
) else (
    echo [OK]    Ollama กำลังรันอยู่แล้ว
)

:: ── 3. Check / pull model ─────────────────────────────────────────────────────
echo [INFO]  ตรวจสอบ model %OLLAMA_MODEL%...
ollama list 2>nul | findstr /B /C:"%OLLAMA_MODEL%" >nul 2>&1
if errorlevel 1 (
    echo [WARN]  ไม่พบ model %OLLAMA_MODEL% — กำลัง pull (อาจใช้เวลาสักครู่)...
    ollama pull %OLLAMA_MODEL%
    if errorlevel 1 (
        echo [ERROR] Pull model ไม่สำเร็จ
        pause
        exit /b 1
    )
    echo [OK]    Pull %OLLAMA_MODEL% เสร็จแล้ว
) else (
    echo [OK]    Model %OLLAMA_MODEL% มีอยู่แล้ว
)

:: ── 4. Check .env ─────────────────────────────────────────────────────────────
if not exist "%~dp0..\\.env" (
    echo [WARN]  ไม่พบ .env — กำลัง copy จาก .env.example...
    copy "%~dp0..\\.env.example" "%~dp0..\\.env" >nul
    echo [WARN]  กรุณาแก้ไข .env ใส่ token จริงก่อนใช้งาน
)

:: เปลี่ยน directory ไปยัง project root
cd /d "%~dp0.."

:: ── 5. Start FastAPI ──────────────────────────────────────────────────────────
echo [INFO]  กำลัง start FastAPI ที่ port %FASTAPI_PORT%...
start "FastAPI - AI Sales Bot" cmd /k "uvicorn main_api:app --host 0.0.0.0 --port %FASTAPI_PORT% --reload"

:: รอให้ FastAPI พร้อม
timeout /t 3 /nobreak >nul

:: ── 6. Start Streamlit ────────────────────────────────────────────────────────
echo [INFO]  กำลัง start Streamlit ที่ port %STREAMLIT_PORT%...
start "Streamlit - AI Sales Bot" cmd /k "streamlit run streamlit_app.py --server.port %STREAMLIT_PORT% --server.address 0.0.0.0 --server.headless true"

:: รอสักครู่ให้ทั้งคู่เปิดขึ้นมา
timeout /t 3 /nobreak >nul

:: ── 7. Print URLs ─────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   AI Sales Bot — Dev Server พร้อมใช้งานแล้ว!
echo ============================================================
echo.
echo   FastAPI  (webhook) :  http://localhost:%FASTAPI_PORT%
echo   API Docs (Swagger) :  http://localhost:%FASTAPI_PORT%/docs
echo   Streamlit (UI)     :  http://localhost:%STREAMLIT_PORT%
echo.
echo   Webhook endpoint   :  http://localhost:%FASTAPI_PORT%/webhook
echo   LINE endpoint      :  http://localhost:%FASTAPI_PORT%/webhook/line
echo.
echo   หากใช้ ngrok:  ngrok http %FASTAPI_PORT%
echo   จากนั้นใช้ URL ที่ ngrok ให้ตั้งเป็น Webhook ใน Meta / LINE Console
echo.
echo ============================================================
echo   ปิดหน้าต่าง FastAPI และ Streamlit เพื่อหยุด server
echo ============================================================
echo.

:: เปิด browser อัตโนมัติ
start "" "http://localhost:%STREAMLIT_PORT%"

pause
