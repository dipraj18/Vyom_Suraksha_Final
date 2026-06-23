import os
import json
import hashlib
from datetime import datetime


class Beacon:
    def __init__(self,
                 node_id="VYOM_NODE_01",
                 beacon_dir="logs/beacon",
                 beacon_file="logs/beacon/central_log.jsonl",
                 ledger_file="logs/beacon/ledger.json"):

        self.node_id = node_id
        self.beacon_dir = beacon_dir
        self.beacon_file = beacon_file
        self.ledger_file = ledger_file

        os.makedirs(self.beacon_dir, exist_ok=True)

        if not os.path.exists(self.ledger_file):
            with open(self.ledger_file, "w") as f:
                json.dump({"last_hash": None}, f)

    def _hash_line(self, line):
        return hashlib.sha256(line.encode()).hexdigest()

    def send_heartbeat(self, risk_score, state, integrity_status):
        heartbeat = {
            "timestamp": datetime.utcnow().isoformat(),
            "node_id": self.node_id,
            "risk_score": risk_score,
            "state": state,
            "integrity_ok": integrity_status
        }

        line = json.dumps(heartbeat)

        # Append heartbeat
        with open(self.beacon_file, "a") as f:
            f.write(line + "\n")

        # Update ledger with last line hash
        last_hash = self._hash_line(line)

        with open(self.ledger_file, "w") as f:
            json.dump({"last_hash": last_hash}, f)

    def verify_integrity(self):
        if not os.path.exists(self.beacon_file):
            return False

        with open(self.beacon_file, "r") as f:
            lines = f.readlines()

        if not lines:
            return True

        last_line = lines[-1].strip()
        current_hash = self._hash_line(last_line)

        with open(self.ledger_file, "r") as f:
            ledger = json.load(f)

        stored_hash = ledger.get("last_hash")

        return current_hash == stored_hash