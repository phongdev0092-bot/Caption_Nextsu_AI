#!/bin/bash
# ======================================================================
#   INSIDE FPT AUTO LOGIN & RETRIEVAL TOOL - UBUNTU / LINUX
# ======================================================================

echo "======================================================================"
echo "   INSIDE FPT RETRIEVAL TOOL - KHOI DONG TREN UBUNTU LINUX"
echo "======================================================================"

# Kiem tra python3
if ! command -v python3 &> /dev/null; then
    echo "[!] Khong tim thay python3. Dang cai dat..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

# Cai dat thu vien neu chua co
if [ ! -d "venv" ]; then
    echo "[*] Tao moi virtualenv..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "[*] Dang kiem tra va cai dat thu vien..."
pip install -r requirements.txt

echo "[*] Dang khoi dong Web Server..."
python3 server.py
