import os
import json
from datetime import datetime

class DecisionStore:
    def __init__(self, log_dir="logs/decisions"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def save_decision(self, decision_data):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.log_dir}/decision_{timestamp}.json"

        with open(filename, "w") as file:
            json.dump(decision_data, file, indent=4)

        return filename