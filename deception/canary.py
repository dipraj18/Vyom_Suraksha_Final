import os
import json


class Canary:
    def __init__(self, canary_path="deception/decoy_secret.txt",
                 state_file="deception/canary_state.json"):

        self.canary_path = canary_path
        self.state_file = state_file

        # Create decoy file if not exists
        if not os.path.exists(self.canary_path):
            with open(self.canary_path, "w") as f:
                f.write("DO NOT ACCESS - CONFIDENTIAL SYSTEM FILE")

        # Initialize state file if not exists
        if not os.path.exists(self.state_file):
            self._initialize_state()

    def _initialize_state(self):
        mod_time = os.path.getmtime(self.canary_path)
        with open(self.state_file, "w") as f:
            json.dump({"last_mod_time": mod_time}, f)

    def check_access(self):
        current_mod_time = os.path.getmtime(self.canary_path)

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            last_time = state.get("last_mod_time")

            if last_time is None:
                # Old schema detected, reset state
                self._initialize_state()
                return False

            if current_mod_time != last_time:
                with open(self.state_file, "w") as f:
                    json.dump({"last_mod_time": current_mod_time}, f)
                return True

        except Exception:
            # If state file corrupted, reset safely
            self._initialize_state()
            return False

        return False