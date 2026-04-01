#!/bin/bash
# Install and configure Nginx to expose the admin UI on port 80.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEMPLATE_PATH="${PROJECT_ROOT}/config/nginx/pharma_admin.conf.template"

PUBLIC_HOST="${1:-211.188.51.10}"
ADMIN_PORT="${2:-8000}"
SITE_NAME="pharma_admin"
RENDERED_CONF="$(mktemp)"

cleanup() {
    rm -f "${RENDERED_CONF}"
}
trap cleanup EXIT

if [ ! -f "${TEMPLATE_PATH}" ]; then
    echo "Missing template: ${TEMPLATE_PATH}" >&2
    exit 1
fi

sed \
    -e "s/__PUBLIC_HOST__/${PUBLIC_HOST}/g" \
    -e "s/__ADMIN_PORT__/${ADMIN_PORT}/g" \
    "${TEMPLATE_PATH}" > "${RENDERED_CONF}"

echo "========================================="
echo "Admin API Nginx setup"
echo "========================================="
echo "Public host : ${PUBLIC_HOST}"
echo "Upstream    : 127.0.0.1:${ADMIN_PORT}"
echo ""

echo "[1/6] Installing Nginx..."
sudo apt-get update
sudo apt-get install -y nginx

echo "[2/6] Installing site config..."
sudo cp "${RENDERED_CONF}" "/etc/nginx/sites-available/${SITE_NAME}"

echo "[3/6] Enabling site..."
sudo ln -sfn "/etc/nginx/sites-available/${SITE_NAME}" "/etc/nginx/sites-enabled/${SITE_NAME}"

echo "[4/6] Validating Nginx config..."
sudo nginx -t

echo "[5/6] Enabling Nginx service..."
sudo systemctl enable nginx

echo "[6/6] Reloading Nginx..."
if sudo systemctl is-active --quiet nginx; then
    sudo systemctl reload nginx
else
    sudo systemctl start nginx
fi

echo ""
echo "========================================="
echo "Admin API is now exposed on port 80"
echo "========================================="
echo "Admin UI : http://${PUBLIC_HOST}/admin"
echo "Health   : http://${PUBLIC_HOST}/health"
echo ""
echo "Useful commands:"
echo "sudo nginx -t"
echo "sudo systemctl status nginx"
echo "curl -I http://${PUBLIC_HOST}/health"
