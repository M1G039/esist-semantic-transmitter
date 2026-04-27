#!/usr/bin/env bash

echo "[*] Installing dependencies..."
echo ""
source .venv/bin/activate
pip install -r requirements.txt
sleep 2
echo ""
echo "[CHECK] Finalized initial setup. To run the application execute the comand: streamlit run app.py"
