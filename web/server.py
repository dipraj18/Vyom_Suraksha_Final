import os
import json
import time
import psutil
import logging
import hashlib
import yaml
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response, send_from_directory

# Setup Flask App
app = Flask(__name__, template_folder='templates', static_folder='static')

# Global references to engine components
orchestrator = None
policy_engine = None
trust_core = None
risk_engine = None
secret_guard = None
audit = None
stealth = None
state_controller = None
canary = None

# Cache directory for this web server
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def get_status():
    global orchestrator, policy_engine, trust_core, risk_engine, secret_guard, stealth, state_controller, canary
    
    # Read last evaluation result cached on orchestrator
    last_result = getattr(orchestrator, "last_result", {})
    tampered_files = last_result.get("tampered_files", [])
    reasons = last_result.get("reasons", [])

    status_data = {
        "state": state_controller.get_state().value if state_controller else "UNKNOWN",
        "risk_score": risk_engine.get_risk() if risk_engine else 0,
        "trust_score": trust_core.get_trust() if trust_core else 100,
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "backup_enabled": (orchestrator is not None and orchestrator.backup is not None),
        "stealth_level": stealth.get_level() if stealth else "NORMAL",
        "secret_allowed": secret_guard.can_access_secret() if secret_guard else False,
        "tampered_files": tampered_files,
        "active_threats": reasons,
        "monitored_files": list(orchestrator.integrity_guard.baseline_hashes.keys()) if (orchestrator and orchestrator.integrity_guard) else []
    }
    return jsonify(status_data)


@app.route("/api/logs")
def get_logs():
    limit = request.args.get("limit", default=100, type=int)
    log_entries = []
    
    audit_file = "logs/audit/audit_ledger.jsonl"
    if os.path.exists(audit_file):
        try:
            with open(audit_file, "r") as f:
                lines = f.readlines()
                # Return the last N lines in reverse order (newest first)
                for line in reversed(lines[-limit:]):
                    if line.strip():
                        log_entries.append(json.loads(line.strip()))
        except Exception as e:
            logging.error(f"[Dashboard API] Failed to read audit logs: {e}")
            
    return jsonify(log_entries)


@app.route("/api/stream")
def sse_stream():
    def event_stream():
        # Keep track of last line read in audit log
        last_line_idx = 0
        audit_file = "logs/audit/audit_ledger.jsonl"
        
        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r") as f:
                    last_line_idx = len(f.readlines())
            except Exception:
                pass

        while True:
            # Check for new audit log lines
            new_logs = []
            if os.path.exists(audit_file):
                try:
                    with open(audit_file, "r") as f:
                        lines = f.readlines()
                        if len(lines) > last_line_idx:
                            for line in lines[last_line_idx:]:
                                if line.strip():
                                    new_logs.append(json.loads(line.strip()))
                            last_line_idx = len(lines)
                except Exception:
                    pass

            last_result = getattr(orchestrator, "last_result", {})
            tampered_files = last_result.get("tampered_files", [])
            reasons = last_result.get("reasons", [])

            data = {
                "state": state_controller.get_state().value if state_controller else "UNKNOWN",
                "risk_score": risk_engine.get_risk() if risk_engine else 0,
                "trust_score": trust_core.get_trust() if trust_core else 100,
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "backup_enabled": (orchestrator is not None and orchestrator.backup is not None),
                "stealth_level": stealth.get_level() if stealth else "NORMAL",
                "secret_allowed": secret_guard.can_access_secret() if secret_guard else False,
                "new_logs": new_logs,
                "tampered_files": tampered_files,
                "active_threats": reasons
            }

            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/control", methods=["POST"])
def post_control():
    global orchestrator, risk_engine, state_controller, stealth, secret_guard, audit
    
    data = request.json or {}
    action = data.get("action")
    
    if not action:
        return jsonify({"success": False, "error": "No action provided"}), 400

    try:
        if action == "reset_risk":
            if risk_engine:
                risk_engine.reset()
            if state_controller:
                # Reset back to NORMAL state
                state_controller.current_state = state_controller.get_state().__class__.NORMAL
            if secret_guard:
                secret_guard.allowed = True
            if audit:
                audit.log_event("MANUAL_STATE_RESET", {"user": "web_dashboard"})
            logging.info("[Dashboard Control] Risk reset triggered manually.")
            return jsonify({"success": True, "message": "System risk reset to 0 and state restored to NORMAL"})

        elif action == "rebaseline":
            if orchestrator and orchestrator.integrity_guard:
                orchestrator.integrity_guard.create_baseline()
            if risk_engine:
                risk_engine.reset()
            if state_controller:
                state_controller.current_state = state_controller.get_state().__class__.NORMAL
            if secret_guard:
                secret_guard.allowed = True
            if audit:
                audit.log_event("MANUAL_REBASELINE", {"user": "web_dashboard"})
            logging.info("[Dashboard Control] Baseline re-creation and state reset triggered.")
            return jsonify({"success": True, "message": "New baseline created and system state reset to NORMAL"})

        elif action == "trigger_backup":
            if orchestrator and orchestrator.backup:
                orchestrator.backup.create_backup({"trigger": "manual_web_dashboard"})
                if audit:
                    audit.log_event("MANUAL_BACKUP_CREATED", {})
                return jsonify({"success": True, "message": "Manual encrypted backup successfully created"})
            else:
                return jsonify({"success": False, "error": "Backup subsystem is disabled. Generate an encryption key first."}), 400

        elif action == "generate_key":
            key_path = os.path.expanduser("~/secure_keys/vyom_backup.key")
            # Import Backup class inside to prevent circular import issues
            from bhairava.backup import Backup
            
            # Generate the key file
            Backup.generate_key_file(key_path)
            
            # Re-initialize backup subsystem
            new_backup = Backup(key_path=key_path)
            if orchestrator:
                orchestrator.backup = new_backup
                orchestrator.defense.backup = new_backup
            
            if audit:
                audit.log_event("BACKUP_KEY_GENERATED", {"path": key_path})
            
            # Reset any penalty from missing backup key
            if risk_engine and risk_engine.get_risk() >= 70:
                # Subtract risk penalty or just reset it
                risk_engine.reset()
                if state_controller:
                    state_controller.current_state = state_controller.get_state().__class__.NORMAL
                    
            logging.info(f"[Dashboard Control] Backup encryption key generated at {key_path}")
            return jsonify({"success": True, "message": f"Secure encryption key generated at {key_path}. Backup subsystem active."})

        elif action == "set_stealth":
            level = data.get("level", "NORMAL")
            if stealth:
                stealth.set_level(level)
                if audit:
                    audit.log_event("STEALTH_LEVEL_CHANGED", {"level": level})
                return jsonify({"success": True, "message": f"Stealth level changed to {level}"})
            return jsonify({"success": False, "error": "Stealth component not available"}), 400

        elif action == "trigger_lockdown":
            if risk_engine:
                risk_engine.add_event(100)
            if state_controller:
                state_controller.update_state(100, {"lockdown": 90, "containment": 60, "alert": 30})
            if secret_guard:
                secret_guard.allowed = False
            if audit:
                audit.log_event("MANUAL_LOCKDOWN_TRIGGERED", {"user": "web_dashboard"})
            logging.warning("[Dashboard Control] Manual LOCKDOWN triggered!")
            return jsonify({"success": True, "message": "Manual lockdown successfully triggered"})

        elif action == "trigger_containment":
            if risk_engine:
                risk_engine.add_event(70)
            if state_controller:
                state_controller.update_state(70, {"lockdown": 90, "containment": 60, "alert": 30})
            if secret_guard:
                secret_guard.allowed = False
            if audit:
                audit.log_event("MANUAL_CONTAINMENT_TRIGGERED", {"user": "web_dashboard"})
            logging.warning("[Dashboard Control] Manual CONTAINMENT triggered!")
            return jsonify({"success": True, "message": "Manual containment successfully triggered"})

        else:
            return jsonify({"success": False, "error": f"Unknown action: {action}"}), 400

    except Exception as e:
        logging.error(f"[Dashboard Control] Action {action} failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config_api():
    sec_config = {}
    env_config = {}
    if os.path.exists("config/security.yaml"):
        try:
            with open("config/security.yaml", "r") as f:
                sec_config = yaml.safe_load(f) or {}
        except Exception:
            pass
    if os.path.exists("config/environment.yaml"):
        try:
            with open("config/environment.yaml", "r") as f:
                env_config = yaml.safe_load(f) or {}
        except Exception:
            pass

    key_path = ""
    backup_dir = "logs/backup"
    remote_dir = "logs/remote_storage"
    retention_limit = 5

    if orchestrator and orchestrator.backup:
        key_path = orchestrator.backup.key_path
        backup_dir = orchestrator.backup.backup_dir
        remote_dir = orchestrator.backup.remote_dir
        retention_limit = orchestrator.backup.retention_limit
    else:
        backup_cfg = sec_config.get("backup", {})
        key_path = backup_cfg.get("key_path", ".secure_keys/vyom_backup.key")
        backup_dir = backup_cfg.get("backup_dir", "logs/backup")
        remote_dir = backup_cfg.get("remote_dir", "logs/remote_storage")
        retention_limit = backup_cfg.get("retention_limit", 5)

    integrity_cfg = sec_config.get("integrity", {})
    monitored_paths = integrity_cfg.get("monitored_paths", ["bhairava", "bhairavi", "config"])

    webhook_cfg = sec_config.get("webhook", {})
    webhook_enabled = webhook_cfg.get("enabled", False)
    webhook_url = webhook_cfg.get("url", "")

    return jsonify({
        "risk_thresholds": sec_config.get("risk_thresholds", {"alert": 30, "containment": 60, "lockdown": 90}),
        "mode": env_config.get("mode", "development"),
        "key_path": key_path,
        "backup_dir": backup_dir,
        "remote_dir": remote_dir,
        "retention_limit": retention_limit,
        "monitored_paths": ",".join(monitored_paths),
        "webhook_enabled": webhook_enabled,
        "webhook_url": webhook_url
    })


@app.route("/api/config", methods=["POST"])
def post_config_api():
    global orchestrator, audit
    data = request.json or {}
    thresholds = data.get("risk_thresholds")
    key_path = data.get("key_path")
    backup_dir = data.get("backup_dir")
    remote_dir = data.get("remote_dir")
    retention_limit = data.get("retention_limit")
    monitored_paths = data.get("monitored_paths")
    webhook_enabled = data.get("webhook_enabled")
    webhook_url = data.get("webhook_url")
    mode = data.get("mode")

    try:
        # Update security config
        sec_config = {}
        if os.path.exists("config/security.yaml"):
            with open("config/security.yaml", "r") as f:
                sec_config = yaml.safe_load(f) or {}

        if thresholds:
            sec_config["risk_thresholds"] = {
                "alert": int(thresholds.get("alert", 30)),
                "containment": int(thresholds.get("containment", 60)),
                "lockdown": int(thresholds.get("lockdown", 90))
            }

        # Backup options
        backup_cfg = sec_config.setdefault("backup", {})
        if key_path:
            backup_cfg["key_path"] = key_path
        if backup_dir:
            backup_cfg["backup_dir"] = backup_dir
        if remote_dir:
            backup_cfg["remote_dir"] = remote_dir
        if retention_limit is not None:
            backup_cfg["retention_limit"] = int(retention_limit)

        # Integrity options
        if monitored_paths is not None:
            if isinstance(monitored_paths, str):
                paths_list = [p.strip() for p in monitored_paths.split(",") if p.strip()]
            else:
                paths_list = list(monitored_paths)
            sec_config.setdefault("integrity", {})["monitored_paths"] = paths_list

        # Webhook options
        webhook_cfg = sec_config.setdefault("webhook", {})
        if webhook_enabled is not None:
            webhook_cfg["enabled"] = bool(webhook_enabled)
        if webhook_url is not None:
            webhook_cfg["url"] = webhook_url

        with open("config/security.yaml", "w") as f:
            yaml.safe_dump(sec_config, f)

        # Update environment config
        if mode:
            env_config = {"mode": mode}
            with open("config/environment.yaml", "w") as f:
                yaml.safe_dump(env_config, f)

        # Dynamically re-initialize backup subsystem
        if orchestrator:
            from bhairava.backup import Backup
            
            # Resolve current active values
            act_key_path = os.path.abspath(os.path.expanduser(backup_cfg.get("key_path", ".secure_keys/vyom_backup.key")))
            act_backup_dir = backup_cfg.get("backup_dir", "logs/backup")
            act_remote_dir = backup_cfg.get("remote_dir", "logs/remote_storage")
            act_ret_limit = int(backup_cfg.get("retention_limit", 5))

            # Ensure parent directories exist for the key
            key_dir = os.path.dirname(act_key_path)
            if key_dir:
                os.makedirs(key_dir, exist_ok=True)
            
            # Re-init or create new key if it doesn't exist
            if not os.path.exists(act_key_path):
                Backup.generate_key_file(act_key_path)
            
            new_backup = Backup(
                backup_dir=act_backup_dir,
                remote_dir=act_remote_dir,
                key_path=act_key_path,
                retention_limit=act_ret_limit
            )
            orchestrator.backup = new_backup
            orchestrator.defense.backup = new_backup

        # Dynamically update Integrity Guard targets
        if monitored_paths is not None and orchestrator and orchestrator.integrity_guard:
            paths_list = sec_config["integrity"]["monitored_paths"]
            orchestrator.integrity_guard.target_dirs = paths_list
            orchestrator.integrity_guard.create_baseline()

        # Dynamically update Webhook alert configuration
        if orchestrator and orchestrator.alert:
            act_webhook_enabled = webhook_cfg.get("enabled", False)
            act_webhook_url = webhook_cfg.get("url", "")
            orchestrator.alert.webhook_url = act_webhook_url if act_webhook_enabled else None

        if audit:
            audit.log_event("CONFIGURATION_UPDATED", data)

        return jsonify({"success": True, "message": "Configuration successfully updated and persisted"})
    except Exception as e:
        logging.error(f"[Dashboard API] Failed to update config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/verify-ledger", methods=["POST"])
def verify_ledger_api():
    global audit
    if not audit:
        return jsonify({"success": False, "error": "Audit subsystem not available"}), 400
    
    is_secure = audit.verify_chain()
    if is_secure:
        return jsonify({"success": True, "message": "Cryptographic signature chain verification: SECURE. No tampering detected."})
    else:
        return jsonify({"success": False, "error": "LEDGER VERIFICATION FAILURE: Chain signature mismatch detected! Logs may have been altered."}), 200


@app.route("/api/backups", methods=["GET"])
def list_backups_api():
    backup_dir = "logs/backup"
    backups = []
    if os.path.exists(backup_dir):
        try:
            for file in os.listdir(backup_dir):
                if file.endswith(".enc"):
                    path = os.path.join(backup_dir, file)
                    stat = os.stat(path)
                    
                    sha256 = hashlib.sha256()
                    with open(path, "rb") as f:
                         while chunk := f.read(4096):
                             sha256.update(chunk)
                    file_hash = sha256.hexdigest()

                    backups.append({
                        "filename": file,
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "sha256": file_hash
                    })
            backups.sort(key=lambda x: x["mtime"], reverse=True)
        except Exception as e:
            logging.error(f"[Dashboard API] Error listing backups: {e}")
    return jsonify(backups)


@app.route("/api/backups/download/<filename>", methods=["GET"])
def download_backup_api(filename):
    backup_dir = os.path.abspath("logs/backup")
    if ".." in filename or filename.startswith("/") or not filename.endswith(".enc"):
        return jsonify({"success": False, "error": "Invalid filename"}), 400
    return send_from_directory(backup_dir, filename, as_attachment=True)


@app.route("/api/canary", methods=["GET"])
def get_canary_config():
    global canary
    if not canary:
        return jsonify({"success": False, "error": "Canary subsystem not available"}), 400
    
    content = ""
    if os.path.exists(canary.canary_path):
        try:
            with open(canary.canary_path, "r") as f:
                content = f.read()
        except Exception:
            pass

    return jsonify({
        "canary_path": canary.canary_path,
        "state_file": canary.state_file,
        "content": content
    })


@app.route("/api/canary", methods=["POST"])
def post_canary_config():
    global canary, audit
    if not canary:
        return jsonify({"success": False, "error": "Canary subsystem not available"}), 400

    data = request.json or {}
    new_path = data.get("canary_path")
    new_content = data.get("content")

    try:
        if new_path and new_path != canary.canary_path:
            old_path = canary.canary_path
            target_dir = os.path.dirname(new_path)
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            
            content_to_write = new_content if new_content is not None else "DO NOT ACCESS - CONFIDENTIAL SYSTEM FILE"
            with open(new_path, "w") as f:
                f.write(content_to_write)
            
            if os.path.exists(old_path):
                os.remove(old_path)
            
            canary.canary_path = new_path
            canary._initialize_state()
            
            if audit:
                audit.log_event("CANARY_PATH_CHANGED", {"from": old_path, "to": new_path})
        elif new_content is not None:
            with open(canary.canary_path, "w") as f:
                f.write(new_content)
            canary._initialize_state()
            if audit:
                audit.log_event("CANARY_CONTENT_UPDATED", {"path": canary.canary_path})

        return jsonify({"success": True, "message": "Canary decoy configuration updated successfully"})
    except Exception as e:
        logging.error(f"[Dashboard API] Failed to update canary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def start_dashboard(orch, policy, tc, risk, sg, aud, st, sc, can, host="127.0.0.1", port=5000):
    global orchestrator, policy_engine, trust_core, risk_engine, secret_guard, audit, stealth, state_controller, canary
    
    orchestrator = orch
    policy_engine = policy
    trust_core = tc
    risk_engine = risk
    secret_guard = sg
    audit = aud
    stealth = st
    state_controller = sc
    canary = can
    
    logging.info(f"Starting Vyom_Suraksha Web Dashboard on http://{host}:{port}")
    # Disable flask output logging for cleaner system output (quiet mode)
    cli_logger = logging.getLogger('werkzeug')
    cli_logger.setLevel(logging.ERROR)
    
    app.run(host=host, port=port, debug=False, use_reloader=False)
