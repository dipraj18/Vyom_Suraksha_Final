"""
Module: TrustCore (Bhairavi - Trust Evaluation Layer)

Purpose:
- Evaluates overall system trustworthiness
- Aggregates signals from multiple subsystems
- Provides a trust score for policy decisions

NOTE:
- Does NOT trigger actions
- Does NOT modify system state directly
"""

import logging


class TrustCore:
    def __init__(self):
        self.trust_score = 100  # Start fully trusted

    def evaluate(self, integrity_ok, anomaly_detected, tampered_files):
        """
        Evaluate trust score based on system signals.

        Args:
            integrity_ok (bool): Integrity status
            anomaly_detected (bool): Resource anomaly flag
            tampered_files (list): List of tampered files

        Returns:
            int: trust score (0–100)
        """

        score = 100

        # Integrity impact
        if not integrity_ok:
            score -= 40

        # Tampered files impact
        if tampered_files:
            score -= min(len(tampered_files) * 5, 30)

        # Anomaly impact
        if anomaly_detected:
            score -= 20

        # Bound score
        score = max(min(score, 100), 0)

        self.trust_score = score

        logging.debug(f"[TrustCore] Trust score evaluated: {score}")

        return score

    def get_trust(self):
        """Return last computed trust score"""
        return self.trust_score