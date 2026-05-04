@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo Created .env from .env.example
  ) else (
    type nul > ".env"
    echo Created empty .env
  )
)

python -m canada_id.start_local