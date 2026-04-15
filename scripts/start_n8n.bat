@echo off
:: ============================================================
:: Start N8N — AI Sales Bot (standalone, no Docker)
:: ============================================================

echo Starting N8N for AI Sales Bot...
echo N8N UI: http://localhost:5678

:: Load .env file values
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" (
        set "%%A=%%B"
    )
)

:: N8N settings
set N8N_HOST=localhost
set N8N_PORT=5678
set N8N_PROTOCOL=http
set WEBHOOK_URL=http://localhost:5678
set GENERIC_TIMEZONE=Asia/Bangkok
set N8N_LOG_LEVEL=info

:: Point to FastAPI running locally
set FASTAPI_INTERNAL_URL=http://localhost:8000

"C:\npm_global\n8n.cmd" start
