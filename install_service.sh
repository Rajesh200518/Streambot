#!/bin/bash
echo "Installing StreamBot as systemctl service..."
cp /root/Streambot/streambot.service /etc/systemd/system/streambot.service
systemctl daemon-reload
systemctl enable streambot
systemctl start streambot
systemctl status streambot
echo "✅ Done! Use these commands to manage:"
echo "  systemctl start streambot"
echo "  systemctl stop streambot"
echo "  systemctl restart streambot"
echo "  systemctl status streambot"
echo "  journalctl -u streambot -f"
