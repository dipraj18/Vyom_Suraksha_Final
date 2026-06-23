#!/usr/bin/env bash
# ==============================================================================
# VYOM SURAKSHA - Cyber Air Shield Daemon Installer
# Works on Debian, Ubuntu, and Parrot OS (Live or Persistent)
# ==============================================================================

set -e

# Colors for layout output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================================${NC}"
echo -e "${CYAN}             VYOM SURAKSHA DAEMON INSTALLER SYSTEM                  ${NC}"
echo -e "${CYAN}====================================================================${NC}"

# Check for root privilege
if [ "$EUID" -ne 0 ]; then
  echo -e "${YELLOW}[!] This installer requires root permissions to configure systemd and install dependencies.${NC}"
  echo -e "${YELLOW}[*] Re-running installer with sudo...${NC}"
  exec sudo bash "$0" "$@"
fi

# Detect actual user
ACTUAL_USER=${SUDO_USER:-$(logname 2>/dev/null || whoami)}
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

# Resolve project path relative to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

echo -e "[*] Target username: ${GREEN}${ACTUAL_USER}${NC}"
echo -e "[*] Project directory: ${GREEN}${SCRIPT_DIR}${NC}"

# 1. Installing System Dependencies
echo -e "\n[*] Checking system-level alert dependencies..."
if command -v apt-get >/dev/null; then
  echo -e "[*] Installing notify-send and paplay dependencies via apt..."
  apt-get update -qq || true
  apt-get install -y -qq libnotify-bin pulseaudio-utils x11-utils
else
  echo -e "${YELLOW}[!] Warning: apt package manager not detected. Ensure 'libnotify-bin' and 'pulseaudio-utils' are installed manually.${NC}"
fi

# 2. Verifying Virtual Environment
echo -e "\n[*] Verifying Python Virtual Environment..."
if [ ! -f "${SCRIPT_DIR}/venv/bin/python" ]; then
  echo -e "${YELLOW}[!] Python virtual environment not found in ${SCRIPT_DIR}/venv${NC}"
  echo -e "[*] Attempting to create virtual environment..."
  apt-get install -y -qq python3-venv python3-pip
  su - "$ACTUAL_USER" -c "python3 -m venv ${SCRIPT_DIR}/venv"
  su - "$ACTUAL_USER" -c "${SCRIPT_DIR}/venv/bin/pip install --upgrade pip"
fi

# Install requirements
if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
  echo -e "[*] Installing python requirements inside venv..."
  su - "$ACTUAL_USER" -c "${SCRIPT_DIR}/venv/bin/pip install -r ${SCRIPT_DIR}/requirements.txt"
else
  # Install necessary packages directly if requirements.txt is missing
  echo -e "[*] Requirements file missing, installing package dependencies directly..."
  su - "$ACTUAL_USER" -c "${SCRIPT_DIR}/venv/bin/pip install PyYAML Flask psutil cryptography pycryptodome"
fi

# 3. Create baseline directories if missing
echo -e "\n[*] Ensuring baseline directories exist..."
mkdir -p "${SCRIPT_DIR}/logs/alerts"
mkdir -p "${SCRIPT_DIR}/logs/audit"
mkdir -p "${SCRIPT_DIR}/logs/backup"
mkdir -p "${SCRIPT_DIR}/logs/beacon"
mkdir -p "${SCRIPT_DIR}/logs/decisions"
mkdir -p "${SCRIPT_DIR}/logs/remote_storage"
mkdir -p "${SCRIPT_DIR}/logs/runtime"
mkdir -p "${SCRIPT_DIR}/.secure_keys"
mkdir -p "${SCRIPT_DIR}/config"

# Fix permissions
chown -R "$ACTUAL_USER":"$ACTUAL_USER" "$SCRIPT_DIR"

# 4. Generate systemd service file
SERVICE_PATH="/etc/systemd/system/vyom_suraksha.service"
echo -e "\n[*] Creating systemd service unit: ${GREEN}${SERVICE_PATH}${NC}"

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Vyom Suraksha - Cyber Air Shield Daemon
After=network.target

[Service]
Type=simple
User=${ACTUAL_USER}
WorkingDirectory=${SCRIPT_DIR}
Environment="PYTHONPATH=${SCRIPT_DIR}"
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/vyom_suraksha.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 5. Reload and enable service
echo -e "[*] Reloading systemd manager configuration..."
systemctl daemon-reload

echo -e "[*] Enabling Vyom Suraksha daemon service on boot..."
systemctl enable vyom_suraksha.service

echo -e "${GREEN}[✓] Installer completed successfully!${NC}"
echo -e "\n------------------------------------------------------------------"
echo -e "You can manage the Vyom Suraksha Cyber Air Shield Daemon service:"
echo -e "  - Start service:   ${CYAN}sudo systemctl start vyom_suraksha${NC}"
echo -e "  - Stop service:    ${CYAN}sudo systemctl stop vyom_suraksha${NC}"
echo -e "  - Restart service: ${CYAN}sudo systemctl restart vyom_suraksha${NC}"
echo -e "  - Check status:    ${CYAN}sudo systemctl status vyom_suraksha${NC}"
echo -e "  - View live logs:  ${CYAN}sudo journalctl -u vyom_suraksha -f${NC}"
echo -e "------------------------------------------------------------------"
echo -e "The Cyber Shield Dashboard will be available at: ${GREEN}http://127.0.0.1:5000${NC}"
echo -e "------------------------------------------------------------------"
