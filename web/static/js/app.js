// Vyom Suraksha UI Logic

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const stateDisplay = document.getElementById("state-display");
    const stateDot = document.querySelector(".state-indicator-dot");
    const riskScore = document.getElementById("risk-score");
    const riskGauge = document.getElementById("risk-gauge");
    const trustScore = document.getElementById("trust-score");
    const trustGauge = document.getElementById("trust-gauge");
    const cpuPercent = document.getElementById("cpu-percent");
    const cpuBar = document.getElementById("cpu-bar");
    const memoryPercent = document.getElementById("memory-percent");
    const memoryBar = document.getElementById("memory-bar");
    const stealthBadge = document.getElementById("stealth-badge");
    const stealthSelect = document.getElementById("stealth-select");
    const sysTime = document.getElementById("sys-time");
    const connStatus = document.getElementById("connection-status");
    
    // Backup elements
    const backupWrapper = document.getElementById("backup-status-wrapper");
    const backupKeyDesc = document.getElementById("backup-key-desc");
    const btnBackup = document.getElementById("btn-backup");
    const btnGenerateKey = document.getElementById("btn-generate-key");
    
    // Integrity elements
    const monitoredFilesList = document.getElementById("monitored-files-list");
    const canaryStatus = document.getElementById("canary-status");
    const canaryStateText = canaryStatus.querySelector(".canary-state-text");
    const tamperedBox = document.getElementById("tampered-files-box");
    const tamperedList = document.getElementById("tampered-files-list");
    
    // Log console elements
    const logTerminal = document.getElementById("log-terminal");
    const logSearch = document.getElementById("log-search");
    const logFilter = document.getElementById("log-filter");
    
    // Banner
    const lockdownBanner = document.getElementById("lockdown-banner");

    // Local state variables
    let cachedMonitoredFiles = [];
    const historyData = { risk: [], trust: [] };
    const maxChartHistory = 30;
    
    // Canvas Trend Chart Setup
    const canvas = document.getElementById("security-trend-chart");
    const ctx = canvas.getContext("2d");

    // Update local clock
    setInterval(() => {
        const now = new Date();
        sysTime.textContent = now.toTimeString().split(' ')[0];
    }, 1000);

    // Initial page load fetch
    fetchInitialData();
    fetchConfig();
    fetchBackups();
    fetchCanary();

    // Setup real-time updates via EventSource (SSE)
    setupEventStream();

    // Setup event listeners for control actions
    setupControlListeners();

    // Resize canvas dynamically
    window.addEventListener("resize", drawTrendChart);

    // ----------------------------------------------------
    // API / Stream Functions
    // ----------------------------------------------------

    function fetchInitialData() {
        // Fetch current status
        fetch("/api/status")
            .then(res => res.json())
            .then(data => {
                updateUIState(data);
                
                // Render monitored files baseline list
                if (data.monitored_files && data.monitored_files.length > 0) {
                    cachedMonitoredFiles = data.monitored_files;
                    renderMonitoredFiles(data.monitored_files, data.tampered_files || []);
                }
            })
            .catch(err => console.error("Error fetching initial status:", err));

        // Fetch log history
        fetch("/api/logs?limit=100")
            .then(res => res.json())
            .then(logs => {
                logTerminal.innerHTML = ""; // Clear loader
                if (logs.length === 0) {
                    logTerminal.innerHTML = `<div class="terminal-line t-dim">[LEDGER] No audit history found.</div>`;
                } else {
                    logs.reverse().forEach(log => {
                        appendLogLine(log, false); // append at end
                    });
                    scrollToBottom();
                }
            })
            .catch(err => {
                console.error("Error fetching log history:", err);
                logTerminal.innerHTML = `<div class="terminal-line t-red">[ERROR] Failed to load ledger history.</div>`;
            });
    }

    function setupEventStream() {
        const source = new EventSource("/api/stream");

        source.onopen = () => {
            connStatus.innerHTML = `STREAM CONNECTION: <span class="text-success">ONLINE</span>`;
        };

        source.onerror = (e) => {
            connStatus.innerHTML = `STREAM CONNECTION: <span class="text-danger">DISCONNECTED</span>`;
            console.error("SSE stream connection closed or error occurred. Retrying...");
        };

        source.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateUIState(data);

            // Append any new log lines received
            if (data.new_logs && data.new_logs.length > 0) {
                data.new_logs.forEach(log => {
                    appendLogLine(log, true); // append at end and notify / scroll
                });
                scrollToBottom();
            }

            // Sync integrity file lists if tampered files changed
            if (cachedMonitoredFiles.length > 0) {
                renderMonitoredFiles(cachedMonitoredFiles, data.tampered_files || []);
            }
        };
    }

    // ----------------------------------------------------
    // UI Rendering & Updating
    // ----------------------------------------------------

    function updateUIState(data) {
        // 1. Update State displays
        const state = data.state || "UNKNOWN";
        stateDisplay.textContent = state;
        
        // Remove existing state classes
        stateDisplay.className = "state-box";
        stateDot.className = "pulse-dot state-indicator-dot";
        
        // Reset warnings
        lockdownBanner.classList.add("hidden");
        
        if (state === "NORMAL") {
            stateDisplay.classList.add("text-success");
            stateDot.style.backgroundColor = "var(--color-green)";
            stateDot.style.boxShadow = "var(--glow-green)";
        } else if (state === "ALERT") {
            stateDisplay.classList.add("text-warning");
            stateDot.style.backgroundColor = "var(--color-orange)";
            stateDot.style.boxShadow = "var(--glow-orange)";
        } else if (state === "CONTAINMENT") {
            stateDisplay.classList.add("text-warning");
            stateDot.style.backgroundColor = "var(--color-orange)";
            stateDot.style.boxShadow = "var(--glow-orange)";
        } else if (state === "LOCKDOWN") {
            stateDisplay.classList.add("text-danger");
            stateDot.style.backgroundColor = "var(--color-red)";
            stateDot.style.boxShadow = "var(--glow-red)";
            lockdownBanner.classList.remove("hidden");
        }

        // 2. Gauges
        const riskVal = data.risk_score || 0;
        riskScore.textContent = riskVal;
        updateCircleGauge(riskGauge, riskVal);
        
        // Set gauge color based on risk levels
        riskGauge.className = "gauge-progress";
        if (riskVal < 30) riskGauge.classList.add("stroke-success");
        else if (riskVal < 60) riskGauge.classList.add("stroke-warning");
        else if (riskVal < 90) riskGauge.classList.add("stroke-warning");
        else riskGauge.classList.add("stroke-danger");

        const trustVal = data.trust_score !== undefined ? data.trust_score : 100;
        trustScore.textContent = trustVal;
        updateCircleGauge(trustGauge, trustVal);
        
        trustGauge.className = "gauge-progress";
        if (trustVal > 70) trustGauge.classList.add("stroke-info");
        else if (trustVal > 40) trustGauge.classList.add("stroke-warning");
        else trustGauge.classList.add("stroke-danger");

        // 3. Telemetry
        const cpu = data.cpu_usage || 0;
        cpuPercent.textContent = `${cpu.toFixed(1)}%`;
        cpuBar.style.width = `${cpu}%`;

        const mem = data.memory_usage || 0;
        memoryPercent.textContent = `${mem.toFixed(1)}%`;
        memoryBar.style.width = `${mem}%`;

        // 4. Stealth Level
        const level = data.stealth_level || "NORMAL";
        stealthBadge.textContent = level;
        stealthSelect.value = level;
        
        if (level === "NORMAL") stealthBadge.className = "value cyan-glow";
        else if (level === "QUIET") stealthBadge.className = "value text-warning";
        else if (level === "SILENT") stealthBadge.className = "value text-danger";

        // 5. Backup config status
        if (data.backup_enabled) {
            backupWrapper.className = "alert-status-box success-border";
            backupWrapper.querySelector(".icon").textContent = "🔒";
            backupWrapper.querySelector(".title").textContent = "Subsystem Active";
            btnBackup.classList.remove("hidden");
            btnGenerateKey.classList.add("hidden");
        } else {
            backupWrapper.className = "alert-status-box warning-border";
            backupWrapper.querySelector(".icon").textContent = "⚠️";
            backupWrapper.querySelector(".title").textContent = "Subsystem Disabled";
            btnBackup.classList.add("hidden");
            btnGenerateKey.classList.remove("hidden");
        }

        // 6. Canary Modification Alert
        const threats = data.active_threats || [];
        const isCanaryTriggered = threats.some(t => t.toLowerCase().includes("canary"));
        
        if (isCanaryTriggered) {
            canaryStatus.className = "canary-box status-triggered";
            canaryStatus.querySelector(".status-icon").textContent = "⚠️";
            canaryStateText.textContent = "ACCESS DETECTED (COMPROMISED!)";
        } else {
            canaryStatus.className = "canary-box status-ok";
            canaryStatus.querySelector(".status-icon").textContent = "🛡️";
            canaryStateText.textContent = "NO ACCESS DETECTED";
        }

        // 7. Tampered Files Alert
        const tampered = data.tampered_files || [];
        if (tampered.length > 0) {
            tamperedBox.classList.remove("hidden");
            tamperedList.innerHTML = tampered.map(file => `<li>${basename(file)}</li>`).join("");
        } else {
            tamperedBox.classList.add("hidden");
            tamperedList.innerHTML = "";
        }

        // 8. Update Historical Data & Draw Chart
        historyData.risk.push(riskVal);
        historyData.trust.push(trustVal);
        if (historyData.risk.length > maxChartHistory) {
            historyData.risk.shift();
            historyData.trust.shift();
        }
        drawTrendChart();

        // 9. Synchronize Topology visual indicators
        updateTopology(data);
    }

    function updateCircleGauge(circleElement, value) {
        const radius = circleElement.r.baseVal.value;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (circumference * value / 100);
        circleElement.style.strokeDashoffset = offset;
    }

    function renderMonitoredFiles(files, tampered) {
        monitoredFilesList.innerHTML = files.map(file => {
            const isTampered = tampered.includes(file);
            return `
                <div class="scroll-item ${isTampered ? 'tampered' : ''}">
                    <span class="file-name" title="${file}">${basename(file)}</span>
                    <span class="file-status">${isTampered ? '⚠️ TAMPERED' : '✓ OK'}</span>
                </div>
            `;
        }).join("");
    }

    // ----------------------------------------------------
    // Chart Drawing (HTML5 Canvas)
    // ----------------------------------------------------

    function drawTrendChart() {
        if (!canvas) return;
        const width = canvas.parentElement.clientWidth;
        const height = canvas.parentElement.clientHeight || 95;
        
        canvas.width = width;
        canvas.height = height;

        ctx.clearRect(0, 0, width, height);

        const count = historyData.risk.length;
        if (count < 2) return;

        // Draw horizontal grid lines
        ctx.strokeStyle = "rgba(0, 204, 255, 0.05)";
        ctx.lineWidth = 1;
        for (let i = 1; i <= 3; i++) {
            const y = (height / 4) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        // Draw Risk Line (Red)
        ctx.strokeStyle = "#ff3131";
        ctx.lineWidth = 2;
        ctx.shadowColor = "rgba(255, 49, 49, 0.4)";
        ctx.shadowBlur = 4;
        ctx.beginPath();
        for (let i = 0; i < count; i++) {
            const x = (width / (maxChartHistory - 1)) * (maxChartHistory - count + i);
            const y = height - (height * (historyData.risk[i] / 100)) * 0.9 - (height * 0.05); // margin offsets
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Draw Trust Line (Cyan)
        ctx.strokeStyle = "#00ccff";
        ctx.shadowColor = "rgba(0, 204, 255, 0.4)";
        ctx.shadowBlur = 4;
        ctx.beginPath();
        for (let i = 0; i < count; i++) {
            const x = (width / (maxChartHistory - 1)) * (maxChartHistory - count + i);
            const y = height - (height * (historyData.trust[i] / 100)) * 0.9 - (height * 0.05);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        ctx.shadowBlur = 0; // Reset shadow glow
    }

    // ----------------------------------------------------
    // Subsystem Topology HUD Coordinator
    // ----------------------------------------------------

    function updateTopology(data) {
        const state = data.state || "NORMAL";
        const threats = data.active_threats || [];
        const isCanaryTriggered = threats.some(t => t.toLowerCase().includes("canary"));
        const isResourceAnomaly = threats.some(t => t.toLowerCase().includes("anomaly") || t.toLowerCase().includes("cpu") || t.toLowerCase().includes("memory"));
        const backupEnabled = data.backup_enabled;

        const nodeState = document.getElementById("node-state");
        const nodeRisk = document.getElementById("node-risk");
        const nodeTrust = document.getElementById("node-trust");
        const nodePolicy = document.getElementById("node-policy");
        const nodeSecret = document.getElementById("node-secret");
        const nodeOrchestrator = document.getElementById("node-orchestrator");
        const nodeMonitor = document.getElementById("node-monitor");
        const nodeAlert = document.getElementById("node-alert");
        const nodeBackup = document.getElementById("node-backup");
        const nodeCanary = document.getElementById("node-canary");
        const nodeBeacon = document.getElementById("node-beacon");

        const nodes = [nodeState, nodeRisk, nodeTrust, nodePolicy, nodeSecret, nodeOrchestrator, nodeMonitor, nodeAlert, nodeBackup, nodeCanary, nodeBeacon];
        
        nodes.forEach(n => {
            if (n) n.className = "node-item active-node";
        });

        if (state === "ALERT") {
            [nodeState, nodeRisk, nodePolicy, nodeOrchestrator, nodeAlert].forEach(n => { if (n) n.className = "node-item warn-node"; });
        } else if (state === "CONTAINMENT") {
            [nodeState, nodeRisk, nodePolicy, nodeOrchestrator, nodeAlert, nodeBackup].forEach(n => { if (n) n.className = "node-item warn-node"; });
        } else if (state === "LOCKDOWN") {
            [nodeState, nodeRisk, nodePolicy, nodeOrchestrator, nodeAlert, nodeBackup, nodeSecret, nodeMonitor].forEach(n => { if (n) n.className = "node-item danger-node"; });
        }

        if (isCanaryTriggered && nodeCanary) {
            nodeCanary.className = "node-item danger-node";
        }
        if (isResourceAnomaly && nodeMonitor) {
            nodeMonitor.className = state === "LOCKDOWN" ? "node-item danger-node" : "node-item warn-node";
        }
        if (!backupEnabled && nodeBackup) {
            nodeBackup.className = "node-item warn-node";
        }
    }

    // ----------------------------------------------------
    // Configuration & Canary Forms Sync
    // ----------------------------------------------------

    function fetchConfig() {
        fetch("/api/config")
            .then(res => res.json())
            .then(data => {
                document.getElementById("input-key-path").value = data.key_path || "";
                document.getElementById("input-backup-dir").value = data.backup_dir || "logs/backup";
                document.getElementById("input-remote-dir").value = data.remote_dir || "logs/remote_storage";
                document.getElementById("input-retention").value = data.retention_limit || 5;
                document.getElementById("input-monitored-dirs").value = data.monitored_paths || "";
                document.getElementById("input-alert").value = data.risk_thresholds.alert || 30;
                document.getElementById("input-containment").value = data.risk_thresholds.containment || 60;
                document.getElementById("input-lockdown").value = data.risk_thresholds.lockdown || 90;
                document.getElementById("input-webhook-enabled").checked = data.webhook_enabled || false;
                document.getElementById("input-webhook-url").value = data.webhook_url || "";
                
                if (data.key_path) {
                    backupKeyDesc.textContent = `Key: ${basename(data.key_path)}`;
                    backupKeyDesc.title = data.key_path;
                }
            })
            .catch(err => console.error("Error fetching config:", err));
    }

    function fetchBackups() {
        const archiveList = document.getElementById("backups-archive-list");
        fetch("/api/backups")
            .then(res => res.json())
            .then(data => {
                if (data.length === 0) {
                    archiveList.innerHTML = `<div class="loading-text">No backups created yet.</div>`;
                    return;
                }
                archiveList.innerHTML = data.map(backup => {
                    const formattedSize = (backup.size / 1024).toFixed(1) + " KB";
                    const dateString = new Date(backup.mtime).toLocaleString();
                    return `
                        <div class="archive-item">
                            <div class="archive-meta">
                                <span class="archive-name" title="${backup.filename}">${basename(backup.filename)}</span>
                                <span class="archive-details" title="SHA-256: ${backup.sha256}">${dateString} | Size: ${formattedSize}</span>
                            </div>
                            <a href="/api/backups/download/${backup.filename}" class="btn-download-link" download>Download</a>
                        </div>
                    `;
                }).join("");
            })
            .catch(err => {
                console.error("Error loading backups archive:", err);
                archiveList.innerHTML = `<div class="loading-text text-danger">Failed to scan archive folder.</div>`;
            });
    }

    function fetchCanary() {
        fetch("/api/canary")
            .then(res => res.json())
            .then(data => {
                document.getElementById("input-canary-path").value = data.canary_path || "";
                document.getElementById("input-canary-content").value = data.content || "";
                document.getElementById("canary-file-path").textContent = data.canary_path || "";
            })
            .catch(err => console.error("Error fetching canary details:", err));
    }

    // ----------------------------------------------------
    // Log Terminal Functions
    // ----------------------------------------------------

    function appendLogLine(log, isLive) {
        if (!log || !log.timestamp) return;

        const line = document.createElement("div");
        line.className = "terminal-line";
        
        let typeColorClass = "t-white";
        const ev = log.event_type;
        
        if (ev === "ALERT_TRIGGERED") typeColorClass = "t-orange";
        else if (ev === "STATE_CHANGE") typeColorClass = "t-magenta";
        else if (ev.includes("ERROR") || ev.includes("MISSING") || ev.includes("FAILURE")) typeColorClass = "t-red";
        else if (ev.includes("START") || ev.includes("STOP") || ev.includes("INITIALIZED") || ev.includes("CHANGED") || ev.includes("UPDATED") || ev.includes("TRUNCATION")) typeColorClass = "t-cyan";
        else if (ev.includes("BACKUP")) typeColorClass = "t-green";

        let detailsStr = "";
        if (log.details && Object.keys(log.details).length > 0) {
            detailsStr = ` | details: ${JSON.stringify(log.details)}`;
        }

        line.setAttribute("data-event-type", ev);
        line.setAttribute("data-text", `${ev} ${detailsStr}`.toLowerCase());

        const localTime = new Date(log.timestamp).toLocaleTimeString();
        line.innerHTML = `
            <span class="t-dim">[${localTime}]</span> 
            <span class="${typeColorClass}">${ev}</span>
            <span class="t-dim">${detailsStr}</span>
        `;

        logTerminal.appendChild(line);
        applySingleLineFilter(line);

        if (isLive) {
            const card = document.querySelector(".log-console-card");
            card.style.borderColor = "var(--color-cyan)";
            setTimeout(() => {
                card.style.borderColor = "";
            }, 600);
        }
    }

    function scrollToBottom() {
        logTerminal.scrollTop = logTerminal.scrollHeight;
    }

    // Console Filtering and Searching
    logSearch.addEventListener("keyup", applyAllFilters);
    logFilter.addEventListener("change", applyAllFilters);

    function applyAllFilters() {
        const query = logSearch.value.toLowerCase().trim();
        const category = logFilter.value;
        const lines = logTerminal.querySelectorAll(".terminal-line");

        lines.forEach(line => {
            const text = line.getAttribute("data-text") || "";
            const type = line.getAttribute("data-event-type") || "";

            let queryMatch = text.includes(query);
            let categoryMatch = false;

            if (category === "ALL") {
                categoryMatch = true;
            } else if (category === "STATE_CHANGE") {
                categoryMatch = (type === "STATE_CHANGE" || type === "MANUAL_STATE_RESET");
            } else if (category === "ALERT_TRIGGERED") {
                categoryMatch = (type === "ALERT_TRIGGERED" || type === "MANUAL_LOCKDOWN_TRIGGERED" || type === "MANUAL_CONTAINMENT_TRIGGERED");
            } else if (category === "BACKUP") {
                categoryMatch = (type.includes("BACKUP") || type.includes("KEY"));
            } else if (category === "ERROR") {
                categoryMatch = (type.includes("ERROR") || type.includes("MISSING") || type.includes("FAIL") || type.includes("FAILURE"));
            }

            line.style.display = (queryMatch && categoryMatch) ? "" : "none";
        });
    }

    function applySingleLineFilter(line) {
        const query = logSearch.value.toLowerCase().trim();
        const category = logFilter.value;
        const text = line.getAttribute("data-text") || "";
        const type = line.getAttribute("data-event-type") || "";

        let queryMatch = text.includes(query);
        let categoryMatch = false;

        if (category === "ALL") {
            categoryMatch = true;
        } else if (category === "STATE_CHANGE") {
            categoryMatch = (type === "STATE_CHANGE" || type === "MANUAL_STATE_RESET");
        } else if (category === "ALERT_TRIGGERED") {
            categoryMatch = (type === "ALERT_TRIGGERED" || type === "MANUAL_LOCKDOWN_TRIGGERED" || type === "MANUAL_CONTAINMENT_TRIGGERED");
        } else if (category === "BACKUP") {
            categoryMatch = (type.includes("BACKUP") || type.includes("KEY"));
        } else if (category === "ERROR") {
            categoryMatch = (type.includes("ERROR") || type.includes("MISSING") || type.includes("FAIL") || type.includes("FAILURE"));
        }

        line.style.display = (queryMatch && categoryMatch) ? "" : "none";
    }

    // ----------------------------------------------------
    // Button Action Handlers
    // ----------------------------------------------------

    function setupControlListeners() {
        // Reset State button
        document.getElementById("btn-reset").addEventListener("click", () => {
            triggerAction("reset_risk");
        });

        // Force Containment button
        document.getElementById("btn-containment").addEventListener("click", () => {
            triggerAction("trigger_containment");
        });

        // Force Lockdown button
        document.getElementById("btn-lockdown").addEventListener("click", () => {
            triggerAction("trigger_lockdown");
        });

        // Create Backup button
        btnBackup.addEventListener("click", () => {
            btnBackup.disabled = true;
            btnBackup.textContent = "BACKING UP...";
            triggerAction("trigger_backup", {}, () => {
                btnBackup.disabled = false;
                btnBackup.textContent = "Create Backup";
                fetchBackups(); // Reload list
            });
        });

        // Generate Key button
        btnGenerateKey.addEventListener("click", () => {
            const keyPathVal = document.getElementById("input-key-path").value.trim() || ".secure_keys/vyom_backup.key";
            if (confirm(`Generate secure AES key inside folder? Target path: ${keyPathVal}`)) {
                btnGenerateKey.disabled = true;
                btnGenerateKey.textContent = "GENERATING KEY...";
                triggerAction("generate_key", {}, () => {
                    btnGenerateKey.disabled = false;
                    btnGenerateKey.textContent = "Generate AES Key";
                    fetchConfig();
                });
            }
        });

        // Stealth Select dropdown change
        stealthSelect.addEventListener("change", (e) => {
            triggerAction("set_stealth", { level: e.target.value });
        });

        // Save Configuration Changes
        document.getElementById("btn-save-config").addEventListener("click", () => {
            const key_path = document.getElementById("input-key-path").value.trim();
            const backup_dir = document.getElementById("input-backup-dir").value.trim();
            const remote_dir = document.getElementById("input-remote-dir").value.trim();
            const retention_limit = parseInt(document.getElementById("input-retention").value) || 5;
            const monitored_paths = document.getElementById("input-monitored-dirs").value.trim();
            const alert = parseInt(document.getElementById("input-alert").value) || 30;
            const containment = parseInt(document.getElementById("input-containment").value) || 60;
            const lockdown = parseInt(document.getElementById("input-lockdown").value) || 90;
            const webhook_enabled = document.getElementById("input-webhook-enabled").checked;
            const webhook_url = document.getElementById("input-webhook-url").value.trim();

            if (!key_path) {
                showToast("Key path is required", "error");
                return;
            }

            fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    key_path,
                    backup_dir,
                    remote_dir,
                    retention_limit,
                    monitored_paths,
                    webhook_enabled,
                    webhook_url,
                    risk_thresholds: { alert, containment, lockdown }
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast("System configuration updated", "success");
                    fetchConfig();
                } else {
                    showToast(data.error || "Save configuration failed", "error");
                }
            })
            .catch(err => {
                console.error("Error saving config:", err);
                showToast("Failed to save config options", "error");
            });
        });

        // Update Deception Canary Bait settings
        document.getElementById("btn-save-canary").addEventListener("click", () => {
            const canary_path = document.getElementById("input-canary-path").value.trim();
            const content = document.getElementById("input-canary-content").value;

            if (!canary_path) {
                showToast("Canary file path required", "error");
                return;
            }

            fetch("/api/canary", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ canary_path, content })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast("Canary bait config updated", "success");
                    fetchCanary();
                } else {
                    showToast(data.error || "Canary update failed", "error");
                }
            })
            .catch(err => {
                console.error("Error saving canary:", err);
                showToast("Failed to update canary decoy", "error");
            });
        });

        // Cryptographic Ledger Integrity Chain Verification
        const btnVerifyLedger = document.getElementById("btn-verify-ledger");
        const ledgerStatus = document.getElementById("ledger-verification-status");

        btnVerifyLedger.addEventListener("click", () => {
            btnVerifyLedger.disabled = true;
            btnVerifyLedger.textContent = "VERIFYING SIGNATURES...";
            ledgerStatus.className = "ledger-status-tag status-none";
            ledgerStatus.textContent = "// EVALUATING...";

            fetch("/api/verify-ledger", { method: "POST" })
                .then(res => res.json())
                .then(data => {
                    btnVerifyLedger.disabled = false;
                    btnVerifyLedger.textContent = "Verify Ledger Signature Chain";
                    if (data.success) {
                        ledgerStatus.className = "ledger-status-tag status-secure";
                        ledgerStatus.textContent = "✓ LEDGER SECURE";
                        showToast(data.message, "success");
                    } else {
                        ledgerStatus.className = "ledger-status-tag status-compromised";
                        ledgerStatus.textContent = "🚨 TAMPER DETECTED";
                        showToast(data.error, "error");
                    }
                })
                .catch(err => {
                    btnVerifyLedger.disabled = false;
                    btnVerifyLedger.textContent = "Verify Ledger Signature Chain";
                    ledgerStatus.className = "ledger-status-tag status-none";
                    ledgerStatus.textContent = "// ERROR";
                    console.error("Ledger validation failed:", err);
                    showToast("Signature check request failed", "error");
                });
        });

        // Re-baseline button event
        const btnRebaseline = document.getElementById("btn-rebaseline");
        if (btnRebaseline) {
            btnRebaseline.addEventListener("click", () => {
                btnRebaseline.disabled = true;
                btnRebaseline.textContent = "ESTABLISHING BASELINE...";
                triggerAction("rebaseline", {}, () => {
                    btnRebaseline.disabled = false;
                    btnRebaseline.textContent = "Accept Current State as Baseline";
                    fetchInitialData();
                });
            });
        }
    }

    function triggerAction(action, extraParams = {}, callback = null) {
        fetch("/api/control", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ action, ...extraParams })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast(data.message || "Action executed", "success");
            } else {
                showToast(data.error || "Action failed", "error");
            }
            if (callback) callback();
        })
        .catch(err => {
            console.error("Action dispatch failed:", err);
            showToast("System transmission error", "error");
            if (callback) callback();
        });
    }

    // Toast alerts helper
    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `cyber-toast ${type}`;
        toast.textContent = `// ${message.toUpperCase()}`;
        
        Object.assign(toast.style, {
            position: "fixed",
            bottom: "30px",
            right: "30px",
            backgroundColor: type === "success" ? "rgba(57, 255, 20, 0.9)" : "rgba(255, 49, 49, 0.9)",
            color: type === "success" ? "#000" : "#fff",
            boxShadow: type === "success" ? "0 0 15px rgba(57, 255, 20, 0.6)" : "0 0 15px rgba(255, 49, 49, 0.6)",
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: "12px",
            fontWeight: "bold",
            padding: "12px 20px",
            borderRadius: "3px",
            zIndex: "9999",
            transition: "all 0.3s ease",
            transform: "translateY(50px)",
            opacity: "0"
        });

        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.transform = "translateY(0)";
            toast.style.opacity = "1";
        }, 50);

        setTimeout(() => {
            toast.style.transform = "translateY(-50px)";
            toast.style.opacity = "0";
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function basename(path) {
        return path.split(/[\\/]/).pop();
    }
});
