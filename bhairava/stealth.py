"""
Module: Stealth (Execution Utility Layer)

Purpose:
- Controls visibility of system behavior
- Reduces unnecessary output/log exposure
- Prepares system for stealth-oriented deployment

NOTE:
- This module does NOT alter detection or response logic
- It only manages visibility and logging behavior
"""

import logging


class Stealth:
    VALID_LEVELS = {"NORMAL", "QUIET", "SILENT"}

    def __init__(self, level="NORMAL"):
        """
        Stealth levels:
        - NORMAL   → Standard logging (INFO and above)
        - QUIET    → Warnings and errors only
        - SILENT   → Critical logs only
        """
        self.level = self._normalize(level)
        self._apply_level()

    def _normalize(self, level):
        """Ensure level is valid and normalized"""
        level = str(level).upper()
        if level not in self.VALID_LEVELS:
            logging.warning(f"Invalid stealth level '{level}', defaulting to NORMAL")
            return "NORMAL"
        return level

    def _apply_level(self):
        """Apply logging level based on stealth mode"""
        logger = logging.getLogger()

        if self.level == "NORMAL":
            logger.setLevel(logging.INFO)

        elif self.level == "QUIET":
            logger.setLevel(logging.WARNING)

        elif self.level == "SILENT":
            logger.setLevel(logging.CRITICAL)

    def set_level(self, level):
        """Dynamically change stealth level"""
        self.level = self._normalize(level)
        self._apply_level()

    def get_level(self):
        """Return current stealth level"""
        return self.level