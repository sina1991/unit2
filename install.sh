#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://github.com/sina1991/unit2.git"
BRANCH="feature/core-implementation"
APP_DIR="/opt/db-analytics"
SERVICE="db-analytics"
APP_USER="unit2"

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run this installer as root (use sudo)."
    exit 1
fi

if [[ ! -f /etc/os-release ]]; then
    echo "ERROR: Unsupported operating system."
    exit 1
fi

. /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID:-}" != "debian" ]]; then
    echo "ERROR: This installer supports Ubuntu and Debian."
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git python3 python3-venv python3-pip ca-certificates

if ! id "$APP_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "/var/lib/$APP_USER" \
        --shell /usr/sbin/nologin "$APP_USER"
fi

if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch origin "$BRANCH"
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" merge --ff-only "origin/$BRANCH"
elif [[ ! -e "$APP_DIR" ]]; then
    git clone --branch "$BRANCH" --single-branch "$REPO" "$APP_DIR"
else
    echo "ERROR: $APP_DIR exists but is not a Git repository."
    exit 1
fi

cd "$APP_DIR"

if [[ ! -f requirements.txt || ! -f .env.example ]]; then
    echo "ERROR: requirements.txt or .env.example is missing."
    exit 1
fi

if [[ ! -f .env ]]; then
    install -m 600 .env.example .env
fi

if grep -q '^ANALYTICS_HOST=' .env; then
    sed -i 's/^ANALYTICS_HOST=.*/ANALYTICS_HOST=0.0.0.0/' .env
else
    echo 'ANALYTICS_HOST=0.0.0.0' >> .env
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

mkdir -p data
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 .env

runuser -u "$APP_USER" -- "$APP_DIR/.venv/bin/python" -m app.cli init

cat > "/etc/systemd/system/$SERVICE.service" <<EOF
[Unit]
Description=Unit 2 Analytics API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python -m app.server
Restart=on-failure
RestartSec=5
TimeoutStopSec=15
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now "$SERVICE"
systemctl --no-pager --full status "$SERVICE" || true

echo
echo "Unit 2 installation finished."
echo "API: http://<SERVER-IP>:8001"
echo "Docs: http://<SERVER-IP>:8001/docs"
echo "Logs: journalctl -u $SERVICE -f"
echo
echo "IMPORTANT: Configure DB_GOLD_API_BASE_URL in $APP_DIR/.env"
echo "to point to the actual DB Gold API, then restart the service:"
echo "systemctl restart $SERVICE"
