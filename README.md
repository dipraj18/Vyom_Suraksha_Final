# Vyom Suraksha // Active Cyber Air Shield Daemon

Vyom Suraksha is a Cyber Air Shield daemon and real-time security telemetry dashboard. Designed for system monitoring, integrity verification, and active incident response containment. It is optimized for portable execution (including transient environments like Parrot OS Live USB).

---

## Key Features

- **Bhairavi Policy Layer**: Real-time evaluation of threat parameters, trust ratios, and automated lockdown transitions.
- **Bhairava Execution Engine**: Performs system resource tracking, logs chained cryptographic event ledgers, and runs active deception canaries.
- **Automated Backup Containment**: On high-alert trigger levels, creates AES-CBC-128 encrypted backups of your configuration assets.
- **Deception Honeypots**: Active canary monitoring that triggers alerts on unauthorized file accesses.
- **Dynamic Dashboard Configuration**: Web UI to modify backup directories, retention limit, alert thresholds, and target folders.
- **Outbound Webhooks**: Live alert dispatching to external platforms (Slack, Discord, custom API endpoints).

---

## Installation & Setup (Step B: Local Run)

### 1. Prerequisite Packages (Parrot OS / Debian)
Install system alert dependencies (for desktop warnings and alarm audio playback):
```bash
sudo apt-get update
sudo apt-get install -y libnotify-bin pulseaudio-utils x11-utils
```

### 2. Set Up Virtual Environment
Initialize the Python environment and install package dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Daemon & Dashboard
Run the start command:
```bash
PYTHONPATH=. ./venv/bin/python vyom_suraksha.py --host 127.0.0.1 --port 5000
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## Running in the Background (Systemd Service)

To run the daemon silently in the background without keeping terminals open:

1. **Install the Systemd Service**:
   ```bash
   sudo ./install.sh
   ```
2. **Start the Service**:
   ```bash
   sudo systemctl start vyom_suraksha.service
   ```
3. **Monitor Status & Logs**:
   - Check service status: `sudo systemctl status vyom_suraksha`
   - Read live daemon logs: `sudo journalctl -u vyom_suraksha -f`

---

## Deploying Remotely (Step C: Web Deployment)

### Deploying on Render (Free Hosting)
If you want to host the web dashboard interface online:

1. Push this repository to your GitHub account.
2. Sign up on [Render.com](https://render.com/) and create a new **Web Service**.
3. Select your `vyom_suraksha` repository.
4. Set configuration parameters:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn web.server:app`
5. Click **Deploy Web Service** to receive your public dashboard URL.
