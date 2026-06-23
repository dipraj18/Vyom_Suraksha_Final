from enum import Enum


class SystemState(Enum):
    NORMAL = "NORMAL"
    ALERT = "ALERT"
    CONTAINMENT = "CONTAINMENT"
    LOCKDOWN = "LOCKDOWN"


class StateController:
    def __init__(self):
        self.current_state = SystemState.NORMAL

    def update_state(self, risk_score, thresholds):
        previous_state = self.current_state

        if risk_score >= thresholds["lockdown"]:
            self.current_state = SystemState.LOCKDOWN
        elif risk_score >= thresholds["containment"]:
            self.current_state = SystemState.CONTAINMENT
        elif risk_score >= thresholds["alert"]:
            self.current_state = SystemState.ALERT
        else:
            self.current_state = SystemState.NORMAL

        return previous_state, self.current_state

    def get_state(self):
        return self.current_state