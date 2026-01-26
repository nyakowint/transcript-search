@echo off
setlocal
pnpm install
pnpm run build
python app.py
