"""
Module: Alert (Bhairava - Alert System)

Purpose:
- Sends system alerts (popup + sound)
- Stores alert logs
- Handles severity-based notifications

NOTE:
- Passive notification layer
- Does NOT affect system logic
"""

import json
import os
import subprocess
import time
import logging
from datetime import datetime


class Alert:
    def __init__(self,
                 alert_dir="logs/alerts",
                 desktop_notify=True,
                 sound_enabled=True,
                 rate_limit_seconds=10,
                 webhook_url=None):

        self.alert_dir = alert_dir
        self.desktop_notify = desktop_notify
        self.sound_enabled = sound_enabled
        self.rate_limit_seconds = rate_limit_seconds
        self.webhook_url = webhook_url

        self.last_notification_time = 0

        os.makedirs(self.alert_dir, exist_ok=True)

    # -----------------------------
    # Notification Settings
    # -----------------------------
    def _get_notification_settings(self, severity):
        if severity >= 80:
            return {"urgency": "critical", "icon": "dialog-error"}
        elif severity >= 40:
            return {"urgency": "normal", "icon": "dialog-warning"}
        else:
            return {"urgency": "low", "icon": "dialog-information"}

    # -----------------------------
    # Sound Playback
    # -----------------------------
    def _play_sound(self, severity):
        if not self.sound_enabled:
            return

        # Trigger sound for medium+ severity
        if severity >= 40:
            sound_path = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"

            if not os.path.exists(sound_path):
                logging.warning("[Alert] Sound file not found")
                return

            try:
                subprocess.Popen(["paplay", sound_path])
            except FileNotFoundError:
                logging.error("[Alert] paplay not installed")
            except Exception as e:
                logging.error(f"[Alert] Sound failed: {e}")

    # -----------------------------
    # Rate Limiting
    # -----------------------------
    def _rate_limited(self):
        current_time = time.time()

        if current_time - self.last_notification_time < self.rate_limit_seconds:
            return True

        self.last_notification_time = current_time
        return False

    # -----------------------------
    # Main Alert Function
    # -----------------------------
    def send_alert(self, severity, reason, details):

        timestamp = datetime.utcnow().isoformat()

        alert_data = {
            "timestamp": timestamp,
            "severity": severity,
            "reason": reason,
            "details": details
        }

        filename = os.path.join(
            self.alert_dir,
            f"alert_{timestamp.replace(':', '_')}.json"
        )

        # Save alert log
        try:
            with open(filename, "w") as f:
                json.dump(alert_data, f, indent=4)
        except Exception as e:
            logging.error(f"[Alert] Failed to write alert log: {e}")

        logging.warning(f"[ALERT] Incident recorded: {filename}")

        # -----------------------------
        # Desktop Notification
        # -----------------------------
        if self.desktop_notify and not self._rate_limited():

            settings = self._get_notification_settings(severity)

            try:
                subprocess.Popen([
                    "notify-send",
                    "-u", settings["urgency"],
                    "-i", settings["icon"],
                    "Vyom_Suraksha Alert",
                    f"Severity: {severity}\n{reason}"
                ])
            except FileNotFoundError:
                logging.error("[Alert] notify-send not installed")
            except Exception as e:
                logging.error(f"[Alert] Notification failed: {e}")

            # -----------------------------
            # Sound Alert
            # -----------------------------
            self._play_sound(severity)

        # -----------------------------
        # Webhook Notification
        # -----------------------------
        if self.webhook_url:
            try:
                import urllib.request
                req = urllib.request.Request(
                    self.webhook_url,
                    data=json.dumps(alert_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Vyom-Suraksha-Cyber-Shield"
                    }
                )
                import threading
                def _dispatch():
                    try:
                        with urllib.request.urlopen(req, timeout=5) as response:
                            pass
                    except Exception as err:
                        logging.error(f"[Alert] Webhook HTTP post failed: {err}")
                
                threading.Thread(target=_dispatch, daemon=True).start()
            except Exception as e:
                logging.error(f"[Alert] Webhook setup failed: {e}")