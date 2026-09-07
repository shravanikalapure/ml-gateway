// Configuration
const API_BASE_URL = "http://localhost:8000";

// DOM Elements
const statusGateway = document.getElementById("status-gateway");
const statusGrpc = document.getElementById("status-grpc");
const btnRefreshAll = document.getElementById("btn-refresh-all");

// Sync Elements
const formSync = document.getElementById("form-sync");
const syncReqId = document.getElementById("sync-req-id");
const syncModelName = document.getElementById("sync-model-name");
const syncTensor = document.getElementById("sync-tensor");
const btnSync = document.getElementById("btn-sync");
const syncResultBox = document.getElementById("sync-result-box");
const syncResId = document.getElementById("sync-res-id");
const syncResWorker = document.getElementById("sync-res-worker");
const syncResExectime = document.getElementById("sync-res-exectime");
const syncResGwlatency = document.getElementById("sync-res-gwlatency");
const syncResType = document.getElementById("sync-res-type");
const syncResOutput = document.getElementById("sync-res-output");

// ----------------------------------------------------
// 1. Health Checks
// ----------------------------------------------------
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) throw new Error("Gateway HTTP error");
        const data = await response.json();
        
        updateBadge(statusGateway, data.components.api_gateway === "healthy" ? "healthy" : "error", "ONLINE");
        updateBadge(statusGrpc, data.components.grpc_worker === "connected" ? "connected" : "error", data.components.grpc_worker === "connected" ? "CONNECTED" : "DISCONNECTED");
    } catch (err) {
        updateBadge(statusGateway, "error", "OFFLINE");
        updateBadge(statusGrpc, "error", "DISCONNECTED");
    }
}

function updateBadge(elem, type, text) {
    if (!elem) return;
    elem.textContent = text;
    if (type === "healthy" || type === "connected") {
        elem.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
    } else {
        elem.className = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30";
    }
}

// ----------------------------------------------------
// 2. Synchronous ML Inference
// ----------------------------------------------------
formSync.addEventListener("submit", async (e) => {
    e.preventDefault();
    const reqId = syncReqId.value.trim();
    const model = syncModelName.value.trim();
    const tensorValues = syncTensor.value.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));

    if (tensorValues.length === 0) {
        alert("Please enter a valid comma-separated numeric tensor (e.g. 1, 2, 3, 4)");
        return;
    }

    btnSync.disabled = true;
    btnSync.innerHTML = `<span>Predicting...</span>`;

    try {
        const response = await fetch(`${API_BASE_URL}/predict/sync`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                request_id: reqId,
                model_name: model,
                input_tensor: tensorValues
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "gRPC inference failed");
        }

        const data = await response.json();
        
        syncResultBox.classList.remove("hidden");
        syncResId.textContent = data.request_id;
        syncResWorker.textContent = data.worker_id;
        syncResExectime.textContent = `${data.execution_time_ms} ms`;
        syncResGwlatency.textContent = `${data.gateway_latency_ms} ms`;
        syncResType.textContent = data.processing_type;
        syncResOutput.textContent = JSON.stringify(data.output_tensor);

        // Auto increment request ID for user convenience
        syncReqId.value = generateNextReqId(reqId, "req");
        checkSystemHealth();
    } catch (err) {
        alert(`Synchronous Inference Error: ${err.message}`);
    } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = `<span>Predict</span><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>`;
    }
});

// Helper to auto-increment request IDs
function generateNextReqId(current, prefix) {
    const num = parseInt(current.replace(/\D/g, '')) || 1;
    const nextNum = num + 1;
    return `${prefix}-${String(nextNum).padStart(3, '0')}`;
}

// ----------------------------------------------------
// Init
// ----------------------------------------------------
btnRefreshAll.addEventListener("click", checkSystemHealth);
checkSystemHealth();
setInterval(checkSystemHealth, 5000);
