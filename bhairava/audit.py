import os
import json
import hashlib
from datetime import datetime


class Audit:
    def __init__(self, audit_file="logs/audit/audit_ledger.jsonl"):
        self.audit_file = audit_file
        os.makedirs(os.path.dirname(self.audit_file), exist_ok=True)

        if not os.path.exists(self.audit_file):
            open(self.audit_file, "w").close()

    def _get_last_hash(self):
        try:
            with open(self.audit_file, "r") as f:
                lines = f.readlines()
                if not lines:
                    return "GENESIS"
                last_entry = json.loads(lines[-1])
                return last_entry["entry_hash"]
        except Exception:
            return "GENESIS"

    def _compute_hash(self, entry_data):
        serialized = json.dumps(entry_data, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()

    def prune_ledger(self, max_size_bytes=5*1024*1024, min_lines=200):
        """
        Prunes the ledger if it exceeds max_size_bytes.
        Keeps the last 50% of logs and inserts a ledger truncation marker.
        """
        try:
            if not os.path.exists(self.audit_file):
                return
            if os.path.getsize(self.audit_file) <= max_size_bytes:
                return

            with open(self.audit_file, "r") as f:
                lines = f.readlines()

            if len(lines) <= min_lines:
                return

            prune_count = len(lines) // 2
            pruned_lines = lines[:prune_count]
            remaining_lines = lines[prune_count:]

            # Get hash of the last pruned entry
            last_pruned_entry = json.loads(pruned_lines[-1].strip())
            last_pruned_hash = last_pruned_entry.get("entry_hash", "UNKNOWN")

            # Create truncation marker
            timestamp = datetime.utcnow().isoformat()
            truncation_entry = {
                "timestamp": timestamp,
                "event_type": "LEDGER_TRUNCATION",
                "details": {
                    "reason": "Log size exceeded limit, truncated to preserve space",
                    "pruned_count": prune_count,
                    "last_pruned_hash": last_pruned_hash
                },
                "previous_hash": last_pruned_hash
            }
            truncation_entry["entry_hash"] = self._compute_hash(truncation_entry)

            # Rewrite log with truncation marker and remaining lines
            with open(self.audit_file, "w") as f:
                f.write(json.dumps(truncation_entry) + "\n")
                for line in remaining_lines:
                    f.write(line)

        except Exception as e:
            print(f"[Audit] Pruning failed: {e}")

    def log_event(self, event_type, details):
        self.prune_ledger()
        timestamp = datetime.utcnow().isoformat()
        previous_hash = self._get_last_hash()

        entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "details": details,
            "previous_hash": previous_hash
        }

        entry_hash = self._compute_hash(entry)
        entry["entry_hash"] = entry_hash

        with open(self.audit_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def verify_chain(self):
        try:
            with open(self.audit_file, "r") as f:
                lines = f.readlines()

            if not lines:
                return True

            first_entry = json.loads(lines[0])
            previous_hash = first_entry.get("previous_hash", "GENESIS")

            for line in lines:
                entry = json.loads(line)

                expected_hash = entry["entry_hash"]

                temp_entry = dict(entry)
                del temp_entry["entry_hash"]

                recalculated_hash = self._compute_hash(temp_entry)

                if recalculated_hash != expected_hash:
                    return False

                if entry["previous_hash"] != previous_hash:
                    return False

                if entry.get("event_type") == "LEDGER_TRUNCATION":
                    pass
                else:
                    previous_hash = expected_hash

            return True

        except Exception:
            return False