// Distributed ML Inference Gateway - Unified Dashboard Client

// Dynamically determine API base URL (works seamlessly on port 8000 or port 3000)
const API_BASE_URL = window.location.origin === "http://localhost:3000" || window.location.origin === "http://127.0.0.1:3000"
    ? "http://localhost:8000"
    : window.location.origin;

// ----------------------------------------------------
// DOM Elements Cache
// ----------------------------------------------------
const btnRefreshAll = document.getElementById("btn-refresh-all");

// Section A: Overview Elements
const overviewAppStatusBadge = document.getElementById("overview-app-status-badge");
const overviewTotalRequests = document.getElementById("overview-total-requests");
const overviewActiveWorkers = document.getElementById("overview-active-workers");
const overviewTotalWorkers = document.getElementById("overview-total-workers");
const overviewCoordinatorName = document.getElementById("overview-coordinator-name");
const overviewCoordinatorId = document.getElementById("overview-coordinator-id");
const overviewCsStatus = document.getElementById("overview-cs-status");

// Section B: Sync Inference Elements
const formSync = document.getElementById("form-sync");
const syncReqId = document.getElementById("sync-req-id");
const syncModelName = document.getElementById("sync-model-name");
const syncTensor = document.getElementById("sync-tensor");
const btnSync = document.getElementById("btn-sync");
const syncErrorMsg = document.getElementById("sync-error-msg");
const syncResultBox = document.getElementById("sync-result-box");
const syncResId = document.getElementById("sync-res-id");
const syncResWorker = document.getElementById("sync-res-worker");
const syncResExectime = document.getElementById("sync-res-exectime");
const syncResGwlatency = document.getElementById("sync-res-gwlatency");
const syncResType = document.getElementById("sync-res-type");
const syncResOutput = document.getElementById("sync-res-output");

// Section C: Bully Election Elements
const electionInitiatorSelect = document.getElementById("election-initiator-select");
const btnStartElection = document.getElementById("btn-start-election");
const electionNodesContainer = document.getElementById("election-nodes-container");
const electionLogBox = document.getElementById("election-log-box");
const btnRefreshElectionLog = document.getElementById("btn-refresh-election-log");

// Section D: Ricart-Agrawala Elements
const btnResetRa = document.getElementById("btn-reset-ra");
const raCsBanner = document.getElementById("ra-cs-banner");
const raCsPulse = document.getElementById("ra-cs-pulse");
const raCsBadge = document.getElementById("ra-cs-badge");
const raProcessesContainer = document.getElementById("ra-processes-container");
const raLogBox = document.getElementById("ra-log-box");
const btnRefreshRaLog = document.getElementById("btn-refresh-ra-log");

// Section E: Multi-Worker Cluster Elements
const workersContainer = document.getElementById("workers-container");

// Section F: Serverless FaaS Elements
const faasInputTensor = document.getElementById("faas-input-tensor");
const btnInvokeFaas = document.getElementById("btn-invoke-faas");
const btnResetFaas = document.getElementById("btn-reset-faas");
const faasLastResult = document.getElementById("faas-last-result");
const faasResColdBadge = document.getElementById("faas-res-cold-badge");
const faasResInitTime = document.getElementById("faas-res-init-time");
const faasResExecTime = document.getElementById("faas-res-exec-time");
const faasStateBadge = document.getElementById("faas-state-badge");
const faasCountTotal = document.getElementById("faas-count-total");
const faasCountCold = document.getElementById("faas-count-cold");
const faasCountWarm = document.getElementById("faas-count-warm");
const faasIdleTimer = document.getElementById("faas-idle-timer");
const faasContainerId = document.getElementById("faas-container-id");
const faasMemoryMb = document.getElementById("faas-memory-mb");
const faasLifecycleLog = document.getElementById("faas-lifecycle-log");

// ----------------------------------------------------
// 1. System Overview & Health
// ----------------------------------------------------
async function fetchSystemOverview() {
    try {
        const res = await fetch(`${API_BASE_URL}/system/overview`);
        if (!res.ok) throw new Error("Overview HTTP error");
        const data = await res.json();

        overviewTotalRequests.textContent = data.total_inference_requests;
        overviewActiveWorkers.textContent = data.active_workers;
        overviewTotalWorkers.textContent = `/ ${data.total_workers} Online`;

        if (data.current_coordinator && data.current_coordinator.name !== "None") {
            overviewCoordinatorName.textContent = data.current_coordinator.name;
            overviewCoordinatorId.textContent = `Node ID: ${data.current_coordinator.id}`;
        } else {
            overviewCoordinatorName.textContent = "None (Requires Election)";
            overviewCoordinatorId.textContent = "Coordinator offline";
        }

        if (data.critical_section && data.critical_section.occupied) {
            overviewCsStatus.textContent = `OCCUPIED by ${data.critical_section.holder}`;
            overviewCsStatus.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40";
        } else {
            overviewCsStatus.textContent = "FREE (Idle)";
            overviewCsStatus.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700";
        }

        overviewAppStatusBadge.textContent = "ONLINE";
        overviewAppStatusBadge.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
    } catch (err) {
        overviewAppStatusBadge.textContent = "OFFLINE";
        overviewAppStatusBadge.className = "inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30";
    }
}

// ----------------------------------------------------
// 2. Synchronous Inference Gateway
// ----------------------------------------------------
document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
        syncTensor.value = btn.getAttribute("data-val");
    });
});

formSync.addEventListener("submit", async (e) => {
    e.preventDefault();
    syncErrorMsg.classList.add("hidden");

    const reqId = syncReqId.value.trim();
    const model = syncModelName.value;
    const tensorVals = syncTensor.value.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));

    if (tensorVals.length === 0) {
        syncErrorMsg.textContent = "Please enter valid comma-separated numeric values.";
        syncErrorMsg.classList.remove("hidden");
        return;
    }

    btnSync.disabled = true;
    btnSync.innerHTML = `<span class="animate-pulse">Routing & Processing...</span>`;

    try {
        const response = await fetch(`${API_BASE_URL}/predict/sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                request_id: reqId,
                model_name: model,
                input_tensor: tensorVals
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Prediction request failed.");
        }

        const data = await response.json();

        syncResultBox.classList.remove("hidden");
        syncResId.textContent = data.request_id;
        syncResWorker.textContent = `${data.worker_name || data.worker_id} (${data.worker_id})`;
        syncResExectime.textContent = `${data.execution_time_ms} ms`;
        syncResGwlatency.textContent = `${data.gateway_latency_ms} ms`;
        syncResType.textContent = `${data.processing_type} (Failovers: ${data.routing ? data.routing.failover_attempts : 0})`;
        syncResOutput.textContent = JSON.stringify(data.output_tensor);

        syncReqId.value = generateNextReqId(reqId, "req");
        refreshAllData();
    } catch (err) {
        syncErrorMsg.textContent = `Error: ${err.message}`;
        syncErrorMsg.classList.remove("hidden");
    } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = `<span>Predict (Synchronous)</span><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>`;
    }
});

function generateNextReqId(current, prefix) {
    const num = parseInt(current.replace(/\D/g, "")) || 1;
    return `${prefix}-${String(num + 1).padStart(3, "0")}`;
}

// ----------------------------------------------------
// 3. Bully Election Algorithm
// ----------------------------------------------------
async function fetchElectionData() {
    try {
        const [statusRes, historyRes] = await Promise.all([
            fetch(`${API_BASE_URL}/election/status`),
            fetch(`${API_BASE_URL}/election/history?limit=30`)
        ]);

        if (statusRes.ok) {
            const status = await statusRes.json();
            renderElectionNodes(status.nodes, status.coordinator_id);
        }

        if (historyRes.ok) {
            const history = await historyRes.json();
            renderElectionLog(history);
        }
    } catch (err) {
        console.error("Failed to fetch election data:", err);
    }
}

function renderElectionNodes(nodes, coordId) {
    electionNodesContainer.innerHTML = nodes.map(node => {
        const isCoord = node.is_coordinator && node.is_alive;
        const isAlive = node.is_alive;

        return `
            <div class="p-4 rounded-xl ${isCoord ? 'bg-amber-950/30 border-amber-600/50' : 'bg-slate-950 border-slate-800'} border transition space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-xs font-mono font-bold text-slate-400">Node ID: ${node.id}</span>
                    <div class="flex items-center gap-1.5">
                        ${isCoord ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">COORDINATOR</span>' : ''}
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isAlive ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}">
                            ${isAlive ? 'ALIVE' : 'OFFLINE'}
                        </span>
                    </div>
                </div>

                <div>
                    <div class="text-sm font-bold text-white">${node.name}</div>
                    <div class="text-[11px] text-slate-400 mt-0.5">Bully Priority: ${node.id}</div>
                </div>

                <div class="pt-1">
                    ${isAlive ? `
                        <button onclick="failElectionNode(${node.id})" class="w-full py-1.5 px-3 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-700/50 text-rose-300 text-xs font-medium transition">
                            Simulate Node Failure
                        </button>
                    ` : `
                        <button onclick="recoverElectionNode(${node.id})" class="w-full py-1.5 px-3 rounded bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-700/50 text-emerald-300 text-xs font-medium transition">
                            Recover Node (Reclaim)
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join("");
}

function renderElectionLog(events) {
    if (!events || events.length === 0) {
        electionLogBox.innerHTML = `<div class="text-slate-500 italic">No election events recorded yet.</div>`;
        return;
    }

    electionLogBox.innerHTML = events.map(e => {
        let badgeColor = "bg-slate-800 text-slate-300";
        if (e.event_type === "ELECTION") badgeColor = "bg-cyan-950 text-cyan-300 border border-cyan-800/40";
        if (e.event_type === "ANSWER") badgeColor = "bg-blue-950 text-blue-300 border border-blue-800/40";
        if (e.event_type === "COORDINATOR" || e.event_type === "COORDINATOR_ELECTED") badgeColor = "bg-amber-950 text-amber-300 border border-amber-700/50";
        if (e.event_type === "COORDINATOR_FAIL" || e.event_type === "NODE_FAIL") badgeColor = "bg-rose-950 text-rose-300 border border-rose-800/40";
        if (e.event_type === "NODE_RECOVER") badgeColor = "bg-emerald-950 text-emerald-300 border border-emerald-800/40";

        return `
            <div class="flex items-start gap-2 py-0.5 border-b border-slate-900 last:border-0">
                <span class="text-slate-500 shrink-0">[${e.time_str}]</span>
                <span class="px-1.5 py-0.2 rounded text-[10px] font-bold ${badgeColor} shrink-0">${e.event_type}</span>
                <span class="text-slate-200">${e.message}</span>
            </div>
        `;
    }).join("");
}

window.failElectionNode = async (nodeId) => {
    try {
        const res = await fetch(`${API_BASE_URL}/election/nodes/${nodeId}/fail`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to mark node inactive");
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

window.recoverElectionNode = async (nodeId) => {
    try {
        const res = await fetch(`${API_BASE_URL}/election/nodes/${nodeId}/recover`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to recover node");
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

btnStartElection.addEventListener("click", async () => {
    btnStartElection.disabled = true;
    const initiatorId = electionInitiatorSelect.value ? parseInt(electionInitiatorSelect.value) : null;

    try {
        const res = await fetch(`${API_BASE_URL}/election/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ initiator_id: initiatorId })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Election failed");
        }
        refreshAllData();
    } catch (err) {
        alert(`Election error: ${err.message}`);
    } finally {
        btnStartElection.disabled = false;
    }
});

btnRefreshElectionLog.addEventListener("click", fetchElectionData);

// ----------------------------------------------------
// 4. Ricart–Agrawala Mutual Exclusion
// ----------------------------------------------------
async function fetchRicartAgrawalaData() {
    try {
        const [statusRes, historyRes] = await Promise.all([
            fetch(`${API_BASE_URL}/ricart-agrawala/status`),
            fetch(`${API_BASE_URL}/ricart-agrawala/history?limit=30`)
        ]);

        if (statusRes.ok) {
            const status = await statusRes.json();
            renderRicartAgrawalaStatus(status);
        }

        if (historyRes.ok) {
            const history = await historyRes.json();
            renderRicartAgrawalaLog(history);
        }
    } catch (err) {
        console.error("Failed to fetch Ricart-Agrawala data:", err);
    }
}

function renderRicartAgrawalaStatus(status) {
    // Banner update
    if (status.cs_occupied) {
        raCsPulse.className = "w-3.5 h-3.5 rounded-full bg-emerald-400 animate-pulse";
        raCsBadge.textContent = `OCCUPIED by ${status.current_cs_holder}`;
        raCsBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
    } else {
        raCsPulse.className = "w-3.5 h-3.5 rounded-full bg-slate-600";
        raCsBadge.textContent = "FREE (Critical Section Idle)";
        raCsBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700";
    }

    // Process Cards
    const procs = Object.values(status.processes);
    raProcessesContainer.innerHTML = procs.map(p => {
        let stateBadge = "bg-slate-800 text-slate-400 border-slate-700";
        let cardBg = "bg-slate-950 border-slate-800";

        if (p.state === "WANTED") {
            stateBadge = "bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse";
            cardBg = "bg-amber-950/20 border-amber-700/50";
        } else if (p.state === "HELD") {
            stateBadge = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse";
            cardBg = "bg-emerald-950/20 border-emerald-600/50";
        }

        const deferredStr = p.deferred_queue && p.deferred_queue.length > 0
            ? p.deferred_queue.join(", ")
            : "None";

        const pendingStr = p.pending_replies && p.pending_replies.length > 0
            ? p.pending_replies.join(", ")
            : "None";

        return `
            <div class="p-4 rounded-xl ${cardBg} border transition space-y-3">
                <div class="flex items-center justify-between">
                    <div class="text-base font-bold text-white font-mono">${p.id}</div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${stateBadge} border">
                        ${p.state}
                    </span>
                </div>

                <div class="space-y-1.5 font-mono text-xs">
                    <div class="flex justify-between py-1 border-b border-slate-800/80">
                        <span class="text-slate-400">Lamport Clock:</span>
                        <span class="text-cyan-400 font-bold">L = ${p.clock}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-800/80">
                        <span class="text-slate-400">Req Timestamp:</span>
                        <span class="text-white">${p.request_timestamp !== null ? p.request_timestamp : '-'}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-800/80">
                        <span class="text-slate-400">Pending Replies:</span>
                        <span class="text-amber-400">${pendingStr}</span>
                    </div>
                    <div class="flex justify-between py-1 border-b border-slate-800/80">
                        <span class="text-slate-400">Deferred Queue:</span>
                        <span class="text-rose-400 font-bold">[${deferredStr}]</span>
                    </div>
                    <div class="flex justify-between py-1">
                        <span class="text-slate-400">CS Entries:</span>
                        <span class="text-emerald-400 font-bold">${p.cs_entries}</span>
                    </div>
                </div>

                <div class="pt-1">
                    ${p.state === "RELEASED" ? `
                        <button onclick="requestRA('${p.id}')" class="w-full py-1.5 px-3 rounded bg-cyan-700 hover:bg-cyan-600 text-white text-xs font-medium transition shadow">
                            Request Critical Section
                        </button>
                    ` : p.state === "HELD" ? `
                        <button onclick="releaseRA('${p.id}')" class="w-full py-1.5 px-3 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition shadow">
                            Release Critical Section
                        </button>
                    ` : `
                        <button disabled class="w-full py-1.5 px-3 rounded bg-amber-900/40 border border-amber-700/40 text-amber-300 text-xs font-medium cursor-not-allowed">
                            Awaiting Peer Replies...
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join("");
}

function renderRicartAgrawalaLog(events) {
    if (!events || events.length === 0) {
        raLogBox.innerHTML = `<div class="text-slate-500 italic">No mutual exclusion events logged yet.</div>`;
        return;
    }

    raLogBox.innerHTML = events.map(e => {
        let badgeColor = "bg-slate-800 text-slate-300";
        if (e.event_type === "REQUEST_CS") badgeColor = "bg-amber-950 text-amber-300 border border-amber-700/50";
        if (e.event_type === "REPLY") badgeColor = "bg-cyan-950 text-cyan-300 border border-cyan-800/40";
        if (e.event_type === "REPLY_DEFERRED") badgeColor = "bg-blue-950 text-blue-300 border border-blue-800/40";
        if (e.event_type === "DEFERRED") badgeColor = "bg-rose-950 text-rose-300 border border-rose-800/40";
        if (e.event_type === "ENTER_CS") badgeColor = "bg-emerald-950 text-emerald-300 border border-emerald-600/60";
        if (e.event_type === "RELEASE_CS") badgeColor = "bg-slate-800 text-slate-300 border border-slate-700";

        return `
            <div class="flex items-start gap-2 py-0.5 border-b border-slate-900 last:border-0">
                <span class="text-slate-500 shrink-0">[${e.time_str}]</span>
                <span class="px-1.5 py-0.2 rounded text-[10px] font-bold ${badgeColor} shrink-0">${e.event_type}</span>
                <span class="text-cyan-400 shrink-0">[L=${e.clock}]</span>
                <span class="text-slate-200">${e.message}</span>
            </div>
        `;
    }).join("");
}

window.requestRA = async (pid) => {
    try {
        const res = await fetch(`${API_BASE_URL}/ricart-agrawala/request`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ process_id: pid })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to request CS");
        }
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

window.releaseRA = async (pid) => {
    try {
        const res = await fetch(`${API_BASE_URL}/ricart-agrawala/release`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ process_id: pid })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to release CS");
        }
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

btnResetRa.addEventListener("click", async () => {
    try {
        await fetch(`${API_BASE_URL}/ricart-agrawala/reset`, { method: "POST" });
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
});

btnRefreshRaLog.addEventListener("click", fetchRicartAgrawalaData);

// ----------------------------------------------------
// 5. Distributed Web-Based System & Worker Pool
// ----------------------------------------------------
async function fetchWorkersData() {
    try {
        const res = await fetch(`${API_BASE_URL}/system/workers`);
        if (!res.ok) throw new Error("Failed to fetch workers");
        const workers = await res.json();
        renderWorkers(workers);
    } catch (err) {
        console.error("Failed to fetch workers data:", err);
    }
}

function renderWorkers(workers) {
    workersContainer.innerHTML = workers.map(w => {
        const isHealthy = w.is_healthy;
        return `
            <div class="p-4 rounded-xl ${isHealthy ? 'bg-slate-950 border-slate-800' : 'bg-rose-950/20 border-rose-800/40'} border transition space-y-3">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="text-sm font-bold text-white">${w.name}</div>
                        <div class="text-[11px] font-mono text-slate-400">${w.worker_id}</div>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isHealthy ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}">
                        ${isHealthy ? 'HEALTHY' : 'FAILED'}
                    </span>
                </div>

                <div class="grid grid-cols-2 gap-2 text-xs font-mono">
                    <div class="p-2 bg-slate-900 rounded border border-slate-800/80">
                        <div class="text-[10px] text-slate-400">Total Requests</div>
                        <div class="text-white font-bold mt-0.5">${w.total_requests}</div>
                    </div>
                    <div class="p-2 bg-slate-900 rounded border border-slate-800/80">
                        <div class="text-[10px] text-slate-400">Successful</div>
                        <div class="text-emerald-400 font-bold mt-0.5">${w.successful_requests}</div>
                    </div>
                    <div class="p-2 bg-slate-900 rounded border border-slate-800/80">
                        <div class="text-[10px] text-slate-400">Last Latency</div>
                        <div class="text-cyan-400 font-bold mt-0.5">${w.last_latency_ms} ms</div>
                    </div>
                    <div class="p-2 bg-slate-900 rounded border border-slate-800/80">
                        <div class="text-[10px] text-slate-400">Avg Latency</div>
                        <div class="text-purple-400 font-bold mt-0.5">${w.avg_latency_ms} ms</div>
                    </div>
                </div>

                <div class="pt-1">
                    ${isHealthy ? `
                        <button onclick="failWorker('${w.worker_id}')" class="w-full py-1.5 px-3 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-700/50 text-rose-300 text-xs font-medium transition">
                            Simulate Worker Failure
                        </button>
                    ` : `
                        <button onclick="recoverWorker('${w.worker_id}')" class="w-full py-1.5 px-3 rounded bg-emerald-950/60 hover:bg-emerald-900 border border-emerald-700/50 text-emerald-300 text-xs font-medium transition">
                            Recover Worker
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join("");
}

window.failWorker = async (wId) => {
    try {
        const res = await fetch(`${API_BASE_URL}/system/workers/${wId}/fail`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to fail worker");
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

window.recoverWorker = async (wId) => {
    try {
        const res = await fetch(`${API_BASE_URL}/system/workers/${wId}/recover`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to recover worker");
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
};

// ----------------------------------------------------
// 6. Serverless Architecture & FaaS
// ----------------------------------------------------
async function fetchServerlessData() {
    try {
        const res = await fetch(`${API_BASE_URL}/serverless/metrics`);
        if (!res.ok) throw new Error("Failed to fetch FaaS metrics");
        const m = await res.json();
        renderServerlessMetrics(m);
    } catch (err) {
        console.error("Failed to fetch serverless data:", err);
    }
}

function renderServerlessMetrics(m) {
    faasStateBadge.textContent = m.runtime_state;
    if (m.runtime_state === "WARM") {
        faasStateBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
    } else if (m.runtime_state === "INITIALIZING" || m.runtime_state === "EXECUTING") {
        faasStateBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 animate-pulse";
    } else {
        faasStateBadge.className = "px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700";
    }

    faasCountTotal.textContent = m.total_invocations;
    faasCountCold.textContent = m.cold_starts;
    faasCountWarm.textContent = m.warm_starts;
    faasIdleTimer.textContent = m.is_initialized ? `${m.idle_seconds_until_teardown}s` : "Inactive";
    faasContainerId.textContent = m.container_id || "None (Cold)";
    faasMemoryMb.textContent = `${m.simulated_memory_mb} MB`;

    // Lifecycle event log
    if (!m.lifecycle_events || m.lifecycle_events.length === 0) {
        faasLifecycleLog.innerHTML = `<div class="text-slate-500 italic">No serverless lifecycle events yet.</div>`;
    } else {
        faasLifecycleLog.innerHTML = m.lifecycle_events.map(e => {
            let badge = "bg-slate-800 text-slate-300";
            if (e.is_cold_start || e.event === "CONTAINER_SPAWN") badge = "bg-rose-950 text-rose-300 border border-rose-800/40";
            if (e.event === "WARM_INVOCATION") badge = "bg-emerald-950 text-emerald-300 border border-emerald-800/40";
            if (e.event === "IDLE_TIMEOUT_TEARDOWN") badge = "bg-amber-950 text-amber-300 border border-amber-800/40";

            return `
                <div class="flex items-start gap-2 py-0.5 border-b border-slate-900 last:border-0">
                    <span class="text-slate-500 shrink-0">[${e.time_str}]</span>
                    <span class="px-1.5 py-0.2 rounded text-[10px] font-bold ${badge} shrink-0">${e.event}</span>
                    <span class="text-slate-200">${e.details}</span>
                </div>
            `;
        }).join("");
    }
}

btnInvokeFaas.addEventListener("click", async () => {
    btnInvokeFaas.disabled = true;
    btnInvokeFaas.innerHTML = `<span class="animate-pulse">Executing FaaS...</span>`;

    const tensorVals = faasInputTensor.value.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));

    try {
        const res = await fetch(`${API_BASE_URL}/serverless/invoke`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                input_tensor: tensorVals.length > 0 ? tensorVals : [1.0, 2.0, 3.0, 4.0, 5.0],
                model_name: "demo-model"
            })
        });

        if (!res.ok) throw new Error("FaaS invocation failed");
        const data = await res.json();

        faasLastResult.classList.remove("hidden");
        if (data.is_cold_start) {
            faasResColdBadge.textContent = "COLD START (~220ms init)";
            faasResColdBadge.className = "text-rose-400 font-bold";
        } else {
            faasResColdBadge.textContent = "WARM REUSE (0ms init)";
            faasResColdBadge.className = "text-emerald-400 font-bold";
        }

        faasResInitTime.textContent = `${data.initialization_time_ms} ms`;
        faasResExecTime.textContent = `${data.execution_time_ms} ms (Total: ${data.total_duration_ms} ms)`;

        refreshAllData();
    } catch (err) {
        alert(err.message);
    } finally {
        btnInvokeFaas.disabled = false;
        btnInvokeFaas.innerHTML = `<span>Invoke Serverless Function</span><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>`;
    }
});

btnResetFaas.addEventListener("click", async () => {
    try {
        await fetch(`${API_BASE_URL}/serverless/reset`, { method: "POST" });
        faasLastResult.classList.add("hidden");
        refreshAllData();
    } catch (err) {
        alert(err.message);
    }
});

// ----------------------------------------------------
// Global Refresh & Periodic Polling
// ----------------------------------------------------
async function refreshAllData() {
    await Promise.allSettled([
        fetchSystemOverview(),
        fetchElectionData(),
        fetchRicartAgrawalaData(),
        fetchWorkersData(),
        fetchServerlessData()
    ]);
}

btnRefreshAll.addEventListener("click", refreshAllData);

// Initial Load & 3-second live refresh interval
refreshAllData();
setInterval(refreshAllData, 3000);
