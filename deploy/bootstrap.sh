#!/usr/bin/env bash
# Первичная настройка ВМ Yandex Cloud (Ubuntu 22.04/24.04). Запускать один раз под пользователем с sudo:
#   scp -i ~/.ssh/fsp_ycloud deploy/bootstrap.sh yc-user@<IP>:~
#   ssh -i ~/.ssh/fsp_ycloud yc-user@<IP> "bash bootstrap.sh '$(cat ~/.ssh/fsp_deploy.pub)'"
# Что делает: Docker + compose, swap 2 ГБ, пользователь deploy (ключ GitHub Actions), каталог /opt/fsp/app, .env со случайными секретами.
set -euo pipefail

DEPLOY_PUBKEY="${1:?Передайте публичный ключ деплоя (содержимое ~/.ssh/fsp_deploy.pub) первым аргументом}"
APP_DIR=/opt/fsp/app
IP=$(curl -fsS --max-time 5 https://ipinfo.io/ip || hostname -I | awk '{print $1}')
DOMAIN_DEFAULT="$(echo "$IP" | tr . -).sslip.io"
DOMAIN="${DOMAIN:-$DOMAIN_DEFAULT}"

echo "==> Docker"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 rsync curl
sudo systemctl enable --now docker

echo "==> swap 2G (сборка фронтенда на маленькой ВМ)"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "==> пользователь deploy"
id deploy >/dev/null 2>&1 || sudo useradd -m -s /bin/bash -G docker deploy
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
echo "$DEPLOY_PUBKEY" | sudo tee /home/deploy/.ssh/authorized_keys >/dev/null
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys && sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo install -d -o deploy -g deploy "$APP_DIR"

echo "==> .env (секреты генерируются здесь и не покидают сервер)"
if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u deploy tee "$APP_DIR/.env" >/dev/null <<ENV
PUBLIC_URL=https://$DOMAIN
DOMAIN=$DOMAIN
COMPOSE_PROFILES=https
HTTP_PORT=127.0.0.1:8080
API_PORT=8000
POSTGRES_PASSWORD=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
DEMO_MODE=1
DEMO_COOLDOWN_MIN=2
ENV
  sudo chmod 600 "$APP_DIR/.env"
fi

echo
echo "Готово. Стенд будет на https://$DOMAIN после первого деплоя из GitHub Actions."
echo "Проверьте, что в группе безопасности ВМ открыты входящие 22, 80, 443."
