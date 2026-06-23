# service/daemon.py

"""
Module: Daemon (Service Layer)

Purpose:
- Runs Vyom_Suraksha in continuous background mode
"""

import logging
import time


class Daemon:
    def __init__(self, target_function, interval=5):
        self.target_function = target_function
        self.interval = interval
        self.running = False

    def start(self):
        logging.info("Daemon started.")
        self.running = True

        try:
            while self.running:
                self.target_function()
                time.sleep(self.interval)

        except KeyboardInterrupt:
            logging.info("Daemon stopped manually.")

        except Exception as e:
            logging.error(f"Daemon error: {e}")

    def stop(self):
        self.running = False
        logging.info("Daemon stopping...")