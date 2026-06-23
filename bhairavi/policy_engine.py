"""
Module: PolicyEngine (Bhairavi - Policy Layer)

Purpose:
- Centralizes all decision-making logic
- Handles risk updates, decay, and state transitions
- Records decisions through DecisionEngine

NOTE:
- This module does NOT execute actions
- It only evaluates and decides system state
"""

import logging


class PolicyEngine:
    def __init__(self, risk_engine, state_controller, decision_engine):
        self.risk_engine = risk_engine
        self.state_controller = state_controller
        self.decision_engine = decision_engine

    # ---------------------------
    # Core Evaluation Method
    # ---------------------------
    def evaluate(self, severity, reasons, thresholds):
        """
        Evaluate system state based on severity input.

        Args:
            severity (int): Severity score from orchestrator
            reasons (list): Reasons for detected events
            thresholds (dict): Risk thresholds

        Returns:
            dict: {
                "risk_score": int,
                "previous_state": State,
                "current_state": State
            }
        """

        # ---------------------------
        # Risk Update / Decay
        # ---------------------------
        if severity > 0:
            self.risk_engine.add_event(min(severity, 100))
        else:
            current_state = self.state_controller.get_state().value

            # No decay during LOCKDOWN
            if current_state != "LOCKDOWN":
                self.risk_engine.decay()

        # ---------------------------
        # Risk Score
        # ---------------------------
        risk_score = self.risk_engine.get_risk()

        # ---------------------------
        # State Transition
        # ---------------------------
        prev_state, current_state = self.state_controller.update_state(
            risk_score,
            thresholds
        )

        # ---------------------------
        # Decision Recording
        # ---------------------------
        if prev_state != current_state:
            reason_text = ", ".join(reasons) if reasons else "No active threat"

            self.decision_engine.record_state_change(
                prev_state,
                current_state,
                risk_score,
                reason_text
            )

            logging.debug(
                f"[Policy] {prev_state.value} → {current_state.value} "
                f"(Risk: {risk_score})"
            )

        # ---------------------------
        # Return Decision Output
        # ---------------------------
        return {
            "risk_score": risk_score,
            "previous_state": prev_state,
            "current_state": current_state
        }