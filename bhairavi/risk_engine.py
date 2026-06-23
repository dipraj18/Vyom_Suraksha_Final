class RiskEngine:
    def __init__(self):
        self.risk_score = 0
        self.max_risk = 100
        self.decay_rate = 5  # risk decreases per safe cycle

    def add_event(self, severity):
        self.risk_score += severity
        if self.risk_score > self.max_risk:
            self.risk_score = self.max_risk

    def decay(self):
        if self.risk_score > 0:
            self.risk_score -= self.decay_rate
            if self.risk_score < 0:
                self.risk_score = 0

    def get_risk(self):
        return self.risk_score

    def reset(self):
        self.risk_score = 0