import psutil
import logging


class Monitor:
    def __init__(self,
                 cpu_threshold=40,   # tuned for real systems
                 memory_threshold=80):

        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold

    def detect_anomaly(self):
        # Take smoother CPU reading
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        severity = 0
        reasons = []

        # CPU Detection
        if cpu_usage > self.cpu_threshold:
            severity += 30
            reasons.append(f"High CPU usage: {cpu_usage:.1f}%")

        # Memory Detection
        if memory_usage > self.memory_threshold:
            severity += 30
            reasons.append(f"High Memory usage: {memory_usage:.1f}%")

        if severity > 0:
            logging.debug(f"[Monitor] Anomaly detected: {reasons}")

            return {
                "severity": severity,
                "cpu": cpu_usage,
                "memory": memory_usage,
                "reasons": reasons
            }

        return None