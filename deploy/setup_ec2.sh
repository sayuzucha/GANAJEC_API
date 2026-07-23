#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# GANAJEC AI — Setup inicial en EC2 (Ubuntu 22.04)
# Ejecutar UNA SOLA VEZ como usuario ubuntu:
#   chmod +x setup_ec2.sh && ./setup_ec2.sh
# ══════════════════════════════════════════════════════════════════
set -e

APP_DIR="/home/ubuntu/ganajec_api"
REPO_URL="https://github.com/TU_USUARIO/TU_REPO.git"   # ← cambia esto
BRANCH="main"

echo "━━━ [1/7] Actualizando paquetes ━━━"
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip nginx git curl

echo "━━━ [2/7] Clonando repositorio ━━━"
if [ -d "$APP_DIR" ]; then
  echo "El directorio ya existe, haciendo pull..."
  cd "$APP_DIR" && git pull origin $BRANCH
else
  git clone -b $BRANCH "$REPO_URL" "$APP_DIR"
fi

echo "━━━ [3/7] Creando entorno virtual ━━━"
cd "$APP_DIR"
python3.11 -m venv .venv
source .venv/bin/activate

echo "━━━ [4/7] Instalando dependencias ━━━"
pip install --upgrade pip
pip install -r requirements.txt

echo "━━━ [5/7] Configurando variables de entorno ━━━"
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo ""
  echo "⚠️  EDITA el archivo .env antes de continuar:"
  echo "    nano $APP_DIR/.env"
  echo ""
fi

echo "━━━ [6/7] Instalando servicio systemd ━━━"
sudo cp "$APP_DIR/deploy/ganajec-api.service" /etc/systemd/system/ganajec-api.service
sudo systemctl daemon-reload
sudo systemctl enable ganajec-api
sudo systemctl restart ganajec-api

echo "━━━ [7/7] Configurando Nginx ━━━"
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/ganajec
sudo ln -sf /etc/nginx/sites-available/ganajec /etc/nginx/sites-enabled/ganajec
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "✅ Setup completo."
echo "   API corriendo en: http://$(curl -s ifconfig.me)/api"
echo "   Logs: sudo journalctl -u ganajec-api -f"
