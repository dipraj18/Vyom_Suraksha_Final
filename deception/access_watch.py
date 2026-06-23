# deception/access_watch.py

"""
Module: AccessWatch (Deception Layer)

Purpose:
- Monitors access to decoy/canary files
- Detects unauthorized interactions

NOTE:
- Passive detection only
- No system modification
"""

import os
import time
import logging


class AccessWatch:
    def __init__(self, watch_path):
        self.watch_path = watch_path
        self.last_access_time = None

        if os.path.exists(watch_path):
            self.last_access_time = os.path.getatime(watch_path)

    def check_access(self):
        """Check if file was accessed"""
        try:
            if not os.path.exists(self.watch_path):
                return False

            current_access = os.path.getatime(self.watch_path)

            if self.last_access_time is None:
                self.last_access_time = current_access
                return False

            if current_access != self.last_access_time:
                logging.warning(f"[AccessWatch] Decoy file accessed: {self.watch_path}")
                self.last_access_time = current_access
                return True

        except Exception as e:
            logging.error(f"[AccessWatch] Error: {e}")

        return False