"""
Module: Defense (Execution Layer - Response Handler)

Purpose:
- Centralizes defensive actions triggered by system state
- Acts as an abstraction layer between decision and execution

NOTE:
- This module does NOT introduce new logic
- It only organizes existing response behavior
"""

import logging


class Defense:
    def __init__(self, alert, backup):
        self.alert = alert
        self.backup = backup

    def handle(self, state, severity, reasons, details):
        """
        Executes defensive actions based on current system state.
        """

        if state == "NORMAL":
            return

        if state == "ALERT":
            self._alert(severity, reasons, details)

        elif state == "CONTAINMENT":
            self._containment(severity, reasons, details)

        elif state == "LOCKDOWN":
            self._lockdown(severity, reasons, details)

    # ---------------- INTERNAL ACTIONS ----------------

    def _alert(self, severity, reasons, details):
        logging.info("Defense: ALERT triggered")

        reason_text = ", ".join(reasons)
        self.alert.send_alert(severity, reason_text, details)

    def _containment(self, severity, reasons, details):
        logging.warning("Defense: CONTAINMENT triggered")

        reason_text = ", ".join(reasons)
        self.alert.send_alert(severity, reason_text, details)

        if self.backup:
            try:
                self.backup.create_backup(details)
            except Exception as e:
                logging.error(f"Backup failed during containment: {e}")

    def _lockdown(self, severity, reasons, details):
        logging.critical("Defense: LOCKDOWN triggered")

        reason_text = ", ".join(reasons)
        self.alert.send_alert(severity, reason_text, details)

        if self.backup:
            try:
                self.backup.create_backup(details)
            except Exception as e:
                logging.error(f"Backup failed during lockdown: {e}")