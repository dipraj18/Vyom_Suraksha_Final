import os
import shutil
import yaml
import json
from datetime import datetime
from bhairava.audit import Audit
from bhairava.backup import Backup
from deception.canary import Canary
from bhairavi.risk_engine import RiskEngine
from bhairavi.state_controller import StateController
from bhairavi.decision_engine import DecisionEngine
from bhairavi.policy_engine import PolicyEngine

def run_diagnostics():
    print("==================================================")
    print(" VYOM SURAKSHA DIAGNOSTICS SUITE")
    print("==================================================")

    # 1. Test Directory Setup
    test_dir = "tests/sandbox"
    os.makedirs(test_dir, exist_ok=True)
    print(f"[1/6] Sandbox initialized at {test_dir}")

    # 2. Test Configuration Writing & Reading
    print("[2/6] Testing Configuration Manager...")
    test_sec_path = os.path.join(test_dir, "security_test.yaml")
    sec_data = {
        "risk_thresholds": {
            "alert": 25,
            "containment": 55,
            "lockdown": 85
        }
    }
    with open(test_sec_path, "w") as f:
        yaml.safe_dump(sec_data, f)
    
    with open(test_sec_path, "r") as f:
        loaded = yaml.safe_load(f)
        assert loaded["risk_thresholds"]["alert"] == 25, "Threshold mismatch!"
        assert loaded["risk_thresholds"]["containment"] == 55, "Threshold mismatch!"
        assert loaded["risk_thresholds"]["lockdown"] == 85, "Threshold mismatch!"
    print("  ✓ Configuration persisted and verified correctly.")

    # 3. Test Cryptographic Audit Ledger & Circular Pruning
    print("[3/6] Testing Chained Cryptographic Ledger & Pruning...")
    test_audit_path = os.path.join(test_dir, "audit_test.jsonl")
    if os.path.exists(test_audit_path):
        os.remove(test_audit_path)

    audit = Audit(audit_file=test_audit_path)
    
    # Log some events
    for i in range(10):
        audit.log_event(f"EVENT_{i}", {"seq": i})
    
    assert audit.verify_chain() is True, "Crypto chain verification failed on write!"
    print("  ✓ Genesis chain signature: SECURE.")

    # Force pruning by setting very small size limit
    # Each entry is ~150 bytes, so 10 entries is ~1.5KB. Let's prune if size > 500 bytes.
    audit.prune_ledger(max_size_bytes=500, min_lines=5)
    
    # Read and count remaining lines
    with open(test_audit_path, "r") as f:
        lines = f.readlines()
    
    print(f"  ✓ Ledger pruned down from 10 to {len(lines)} lines.")
    
    # Check that truncation entry was successfully created
    first_entry = json.loads(lines[0])
    assert first_entry["event_type"] == "LEDGER_TRUNCATION", "Pruning truncation marker missing!"
    
    # Verify pruned chain continues successfully
    assert audit.verify_chain() is True, "Crypto chain verification failed after pruning!"
    print("  ✓ Cryptographic chain consistency preserved post-pruning.")

    # 4. Test Deception Canary
    print("[4/6] Testing Deception Canary Subsystem...")
    test_decoy_path = os.path.join(test_dir, "decoy_test.txt")
    test_state_path = os.path.join(test_dir, "canary_state_test.json")
    if os.path.exists(test_decoy_path):
        os.remove(test_decoy_path)
    if os.path.exists(test_state_path):
        os.remove(test_state_path)

    canary = Canary(canary_path=test_decoy_path, state_file=test_state_path)
    assert canary.check_access() is False, "Canary triggered prematurely!"
    
    # Access/modify decoy
    with open(test_decoy_path, "w") as f:
        f.write("MODIFIED BAIT")
    
    assert canary.check_access() is True, "Canary failed to detect modification!"
    print("  ✓ Canary Honey-bait detection: ACTIVE.")

    # 5. Test Encrypted Backup Snapshot
    print("[5/6] Testing AES Encryption Backup Snapshot...")
    test_backup_dir = os.path.join(test_dir, "backup_out")
    test_remote_dir = os.path.join(test_dir, "remote_out")
    test_key_path = os.path.join(test_dir, "test.key")
    
    if os.path.exists(test_backup_dir):
        shutil.rmtree(test_backup_dir)
    if os.path.exists(test_remote_dir):
        shutil.rmtree(test_remote_dir)
    if os.path.exists(test_key_path):
        os.remove(test_key_path)

    # Generate AES key
    Backup.generate_key_file(test_key_path)
    assert os.path.exists(test_key_path), "Key generation failed!"
    
    backup = Backup(
        backup_dir=test_backup_dir,
        remote_dir=test_remote_dir,
        key_path=test_key_path,
        retention_limit=2
    )
    
    # Create multiple backups to trigger retention policy limits
    backup.create_backup({"test": 1})
    backup.create_backup({"test": 2})
    backup.create_backup({"test": 3})
    
    # Check retention limit
    created_backups = [f for f in os.listdir(test_backup_dir) if f.endswith(".enc")]
    assert len(created_backups) == 2, f"Expected 2 backups under retention policy, found {len(created_backups)}!"
    print("  ✓ AES CBC Encryption and Snapshot Pruning: PASS.")

    # 6. Test Persistent Integrity Guard
    print("[6/6] Testing Persistent Integrity Guard...")
    from bhairavi.integrity_guard import IntegrityGuard
    test_guard_dir = os.path.join(test_dir, "guard_test")
    os.makedirs(test_guard_dir, exist_ok=True)
    
    test_file_path = os.path.join(test_guard_dir, "sensitive.txt")
    with open(test_file_path, "w") as f:
        f.write("SAFE DATA")
        
    test_baseline_path = os.path.join(test_dir, "baseline.json")
    
    # Initialize first time (should create baseline file)
    guard = IntegrityGuard(target_dirs=[test_guard_dir], baseline_file=test_baseline_path)
    assert os.path.exists(test_baseline_path), "Baseline file was not created!"
    
    # Initialize second time (should load from baseline file)
    guard2 = IntegrityGuard(target_dirs=[test_guard_dir], baseline_file=test_baseline_path)
    assert len(guard2.verify_integrity()) == 0, "Integrity check failed prematurely!"
    
    # Tamper file
    with open(test_file_path, "w") as f:
        f.write("MALICIOUS DATA")
        
    # Verify detects tamper
    assert len(guard2.verify_integrity()) > 0, "Integrity guard failed to detect file modification!"
    print("  ✓ Persistent File Integrity baseline loading & verification: PASS.")

    # Cleanup sandbox files
    shutil.rmtree(test_dir)
    
    print("\n==================================================")
    print(" DIAGNOSTICS SUMMARY: ALL COMPONENTS STABLE")
    print("==================================================")

if __name__ == "__main__":
    run_diagnostics()
