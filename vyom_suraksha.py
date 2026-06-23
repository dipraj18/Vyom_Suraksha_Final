import time
import yaml
import logging
import argparse
import threading
import os

from bhairavi.state_controller import StateController
from bhairavi.risk_engine import RiskEngine
from bhairavi.decision_engine import DecisionEngine
from bhairavi.integrity_guard import IntegrityGuard
from bhairavi.secret_guard import SecretGuard
from bhairavi.policy_engine import PolicyEngine
from bhairavi.trust_core import TrustCore

from bhairava.monitor import Monitor
from bhairava.alert import Alert
from bhairava.backup import Backup
from bhairava.orchestrator import Orchestrator
from bhairava.audit import Audit
from bhairava.stealth import Stealth

from deception.canary import Canary
from service.beacon import Beacon
from web.server import start_dashboard


# ---------------- LOGGING SETUP ----------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


def load_config(path):
    try:
        with open(path, "r") as file:
            data = yaml.safe_load(file)
            if data is None:
                raise ValueError("Empty configuration")
            return data
    except Exception as e:
        logging.error(f"[FAIL-SAFE] Configuration error in {path}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Vyom Suraksha - Cyber Air Shield Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard host IP")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard port")
    parser.add_argument("--no-web", action="store_true", help="Disable web dashboard")
    args = parser.parse_args()

    logging.info("Vyom_Suraksha Auto Mode Starting...")

    env_config = load_config("config/environment.yaml")
    sec_config = load_config("config/security.yaml")

    if env_config is None or sec_config is None:
        logging.warning("Using fail-safe configuration defaults.")
        env_config = {"mode": "fail-safe"}
        sec_config = {
            "risk_thresholds": {
                "alert": 30,
                "containment": 60,
                "lockdown": 90
            }
        }

    # ----------- Bhairavi (Policy Layer) -----------
    state_controller = StateController()
    risk_engine = RiskEngine()
    decision_engine = DecisionEngine()
    
    # Load custom integrity guard targets if configured
    integrity_cfg = sec_config.get("integrity", {})
    monitored_paths = integrity_cfg.get("monitored_paths", ["bhairava", "bhairavi", "config"])
    integrity_guard = IntegrityGuard(target_dirs=monitored_paths)
    
    secret_guard = SecretGuard()
    trust_core = TrustCore()

    policy_engine = PolicyEngine(
        risk_engine,
        state_controller,
        decision_engine
    )

    # ----------- Bhairava (Execution Layer) -----------
    monitor = Monitor()
    webhook_cfg = sec_config.get("webhook", {})
    webhook_url = webhook_cfg.get("url", "") if webhook_cfg.get("enabled", False) else None
    alert = Alert(webhook_url=webhook_url)
    canary = Canary()
    beacon = Beacon()
    audit = Audit()
    stealth = Stealth("NORMAL")

    # --- Safe Backup Initialization ---
    backup = None
    try:
        backup_cfg = sec_config.get("backup", {})
        key_path = os.path.abspath(os.path.expanduser(backup_cfg.get("key_path", ".secure_keys/vyom_backup.key")))
        
        # Auto-generate key file if missing to enable backup subsystem immediately
        if not os.path.exists(key_path):
            logging.info(f"Backup encryption key not found. Automatically generating at: {key_path}")
            Backup.generate_key_file(key_path)

        backup = Backup(
            backup_dir=backup_cfg.get("backup_dir", "logs/backup"),
            remote_dir=backup_cfg.get("remote_dir", "logs/remote_storage"),
            key_path=key_path,
            retention_limit=int(backup_cfg.get("retention_limit", 5))
        )
        audit.log_event("BACKUP_INITIALIZED", {})
    except Exception as e:
        logging.critical(
            "Backup subsystem disabled: encryption key file not found. "
            "Continuing without backup."
        )
        audit.log_event("BACKUP_KEY_MISSING", {"error": str(e)})
        # Reduce risk penalty from 70 to 10 to avoid auto-containment loop
        risk_engine.add_event(10)

    orchestrator = Orchestrator(
        integrity_guard,
        canary,
        beacon,
        monitor,
        alert,
        backup
    )

    # Cache initial state
    orchestrator.last_result = {
        "severity": 0,
        "reasons": [],
        "details": {},
        "tampered_files": []
    }

    # Start Dashboard Web Server Thread
    if not args.no_web:
        db_thread = threading.Thread(
            target=start_dashboard,
            args=(orchestrator, policy_engine, trust_core, risk_engine, secret_guard, audit, stealth, state_controller, canary),
            kwargs={"host": args.host, "port": args.port},
            daemon=True
        )
        db_thread.start()

    integrity_guard.create_baseline()
    audit.log_event("SYSTEM_START", {"mode": env_config["mode"]})

    cycle = 0
    prev_state_value = None

    try:
        while True:
            cycle += 1

            try:
                # Reload configuration dynamically in case user edited thresholds/paths via dashboard
                updated_sec_config = load_config("config/security.yaml")
                if updated_sec_config and "risk_thresholds" in updated_sec_config:
                    sec_config = updated_sec_config

                # ---------------- Evaluation ----------------
                result = orchestrator.evaluate()
                orchestrator.last_result = result
                severity = result["severity"]

                # ---------------- Trust Evaluation ----------------
                trust_score = trust_core.evaluate(
                    integrity_ok=(len(result["tampered_files"]) == 0),
                    anomaly_detected=("monitor" in result["details"]),
                    tampered_files=result["tampered_files"]
                )

                # ---------------- Policy Engine ----------------
                policy_result = policy_engine.evaluate(
                    severity=severity,
                    reasons=result["reasons"],
                    thresholds=sec_config["risk_thresholds"]
                )

                risk_score = policy_result["risk_score"]
                prev_state = policy_result["previous_state"]
                current_state = policy_result["current_state"]

                # ---------------- Logging ----------------
                if prev_state_value != current_state.value:
                    logging.warning(
                        f"State changed → {current_state.value} "
                        f"(Risk: {risk_score}, Trust: {trust_score})"
                    )
                    prev_state_value = current_state.value

                if cycle % 10 == 0:
                    logging.info(
                        f"System active | State: {current_state.value} | "
                        f"Risk: {risk_score} | Trust: {trust_score}"
                    )

                # ---------------- Audit ----------------
                if prev_state != current_state:
                    audit.log_event("STATE_CHANGE", {
                        "from": prev_state.value,
                        "to": current_state.value,
                        "risk_score": risk_score,
                        "trust_score": trust_score
                    })

                if severity > 0:
                    audit.log_event("ALERT_TRIGGERED", {
                        "severity": severity,
                        "reasons": result["reasons"]
                    })

                # ---------------- Response ----------------
                orchestrator.trigger_response(
                    current_state.value,
                    severity,
                    result["reasons"],
                    result["details"]
                )

                # ---------------- Secret Control ----------------
                secret_guard.update_permission(current_state)

                # ---------------- Beacon ----------------
                beacon.send_heartbeat(
                    risk_score=risk_score,
                    state=current_state.value,
                    integrity_status=(len(result["tampered_files"]) == 0)
                )

                time.sleep(5)

            except Exception as runtime_error:
                logging.error(f"Runtime error: {runtime_error}")
                audit.log_event("RUNTIME_ERROR", {"error": str(runtime_error)})
                risk_engine.add_event(90)

    except KeyboardInterrupt:
        audit.log_event("SYSTEM_STOP", {})
        logging.info("Vyom_Suraksha Auto Mode Stopped Safely.")


if __name__ == "__main__":
    main()