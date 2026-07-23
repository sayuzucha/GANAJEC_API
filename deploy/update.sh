#!/bin/bash
# ══════════════════════════════════════════════════════════════════
# GANAJEC AI — Actualizar despliegue en EC2
# Ejecutar cada vez que hagas push al repo:
#   ./deploy/update.sh
# ══════════════════════════════════════════════════════════════════
set -e

APP_DIR="/home/ubuntu/ganajec_api"

echo "━━━ Actualizando código ━━━"
cd "$APP_DIR"
git pull origin main

echo "━━━ Actualizando dependencias ━━━"
source .venv/bin/activate
pip install -r requirements.txt

echo "━━━ Reiniciando servicio ━━━"
sudo systemctl restart ganajec-api

echo "✅ Actualización completa."
sudo systemctl status ganajec-api --no-pager
