import logging
from bhairava.defense import Defense


class Orchestrator:
    def __init__(self,
                 integrity_guard,
                 canary,
                 beacon,
                 monitor,
                 alert,
                 backup=None):

        self.integrity_guard = integrity_guard
        self.canary = canary
        self.beacon = beacon
        self.monitor = monitor
        self.alert = alert
        self.backup = backup

        # Defense layer (NEW - abstraction only)
        self.defense = Defense(alert, backup)

    # ---------------------------
    # Evaluation Phase
    # ---------------------------
    def evaluate(self):
        severity = 0
        reasons = []
        details = {}
        tampered_files = []

        # Integrity Check
        tampered = self.integrity_guard.verify_integrity()
        if tampered:
            severity += 80
            reasons.append("Integrity violation detected")
            tampered_files = tampered
            details["tampered_files"] = tampered

        # Canary Check
        if self.canary.check_access():
            severity += 60
            reasons.append("Canary file modification detected")

        # Beacon Tamper Check
        if not self.beacon.verify_integrity():
            severity += 70
            reasons.append("Beacon log tampering detected")

        # System Resource Monitoring
        anomaly = self.monitor.detect_anomaly()
        if anomaly:
            severity += anomaly["severity"]
            reasons.append("System anomaly detected")
            details["monitor"] = anomaly

        return {
            "severity": severity,
            "reasons": reasons,
            "details": details,
            "tampered_files": tampered_files
        }

    # ---------------------------
    # Response Phase
    # ---------------------------
    def trigger_response(self,
                         current_state,
                         severity,
                         reasons,
                         details):

        if severity <= 0:
            return

        # Delegate to Defense layer
        self.defense.handle(
            state=current_state,
            severity=severity,
            reasons=reasons,
            details=details
        )