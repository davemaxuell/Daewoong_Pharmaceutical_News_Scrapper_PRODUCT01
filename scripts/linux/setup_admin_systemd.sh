#!/bin/bash
# Setup systemd service for the admin API on Linux servers.

set -e

echo "========================================="
echo "Admin API systemd setup"
echo "========================================="

echo "[1/4] Copying service file..."
sudo cp systemd_pharma_admin_api.service /etc/systemd/system/

echo "[2/4] Setting permissions..."
sudo chmod 644 /etc/systemd/system/systemd_pharma_admin_api.service

echo "[3/4] Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "[4/4] Enabling and starting admin API..."
sudo systemctl enable systemd_pharma_admin_api.service
sudo systemctl start systemd_pharma_admin_api.service

echo ""
echo "========================================="
echo "Admin API setup complete"
echo "========================================="
echo ""
echo "Useful commands:"
echo "sudo systemctl status systemd_pharma_admin_api.service"
echo "sudo journalctl -u systemd_pharma_admin_api.service -f"
echo "tail -f logs/admin_api_output.log"
echo "tail -f logs/admin_api_error.log"
