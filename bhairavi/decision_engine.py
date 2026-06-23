from datetime import datetime
from bhairavi.decision_store import DecisionStore

class DecisionEngine:
    def __init__(self):
        self.store = DecisionStore()

    def record_state_change(self, previous_state, current_state, risk_score, reason):
        decision_data = {
            "timestamp": datetime.now().isoformat(),
            "previous_state": previous_state.value,
            "current_state": current_state.value,
            "risk_score": risk_score,
            "reason": reason
        }

        filename = self.store.save_decision(decision_data)
        return filename