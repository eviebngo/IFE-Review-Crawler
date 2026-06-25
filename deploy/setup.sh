#!/bin/bash
set -e

APP_DIR="/home/ubuntu/simple_crawler"

echo "==> Installing system packages"
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip python3-venv nginx git

echo "==> Setting up Python environment"
cd "$APP_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
pip install --quiet gunicorn

echo "==> Installing Flask app as a systemd service"
sudo cp deploy/ife-app.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ife-app
sudo systemctl restart ife-app

echo "==> Configuring nginx"
sudo cp deploy/nginx.conf /etc/nginx/sites-available/ife-app
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/ife-app /etc/nginx/sites-enabled/ife-app
sudo nginx -t
sudo systemctl restart nginx

echo "==> Scheduling daily crawl at 3 AM"
CRON_CMD="0 3 * * * $APP_DIR/.venv/bin/python $APP_DIR/daily_crawl.py >> $APP_DIR/crawl_log.txt 2>&1"
(crontab -l 2>/dev/null | grep -v daily_crawl; echo "$CRON_CMD") | crontab -

echo ""
echo "Done! App is running at http://$(curl -s ifconfig.me)"
echo "Daily crawl is scheduled for 3 AM server time."
echo ""
echo "To check app status:  sudo systemctl status ife-app"
echo "To view logs:         sudo journalctl -u ife-app -f"
echo "To view crawl log:    tail -f $APP_DIR/crawl_log.txt"
