// Configuration
const API_BASE_URL = "http://localhost:8000";
const WS_BASE_URL = "ws://localhost:8000/ws/signaling";

// State
let wsClient = null;
let mediaStream = null;
let fpsFrameCount = 0;
let lastFpsCheck = performance.now();
let fpsAnimationId = null;

// DOM Elements
const statusGateway = document.getElementById("status-gateway");
const statusGrpc = document.getElementById("status-grpc");
const statusRabbitmq = document.getElementById("status-rabbitmq");
const statusConsumer = document.getElementById("status-consumer");
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

// Async Elements
const formAsync = document.getElementById("form-async");
const asyncReqId = document.getElementById("async-req-id");
const asyncModelName = document.getElementById("async-model-name");
const asyncTensor = document.getElementById("async-tensor");
const btnAsync = document.getElementById("btn-async");
const asyncLogBody = document.getElementById("async-log-body");

// Stream & WebRTC Elements
const videoElem = document.getElementById("webcam");
const videoPlaceholder = document.getElementById("video-placeholder");
const btnStartCam = document.getElementById("btn-start-cam");
const btnStopCam = document.getElementById("btn-stop-cam");
const btnConnectWs = document.getElementById("btn-connect-ws");
const btnSendPing = document.getElementById("btn-send-ping");
const statusWs = document.getElementById("status-ws");
const wsLog = document.getElementById("ws-log");
const streamRes = document.getElementById("stream-res");
const streamFps = document.getElementById("stream-fps");

// Metrics Elements
const metricSyncCount = document.getElementById("metric-sync-count");
const metricAsyncCount = document.getElementById("metric-async-count");
const metricAvgLatency = document.getElementById("metric-avg-latency");

// ----------------------------------------------------
// 1. Health Checks & System Metrics
// ----------------------------------------------------
async function checkSystemHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) throw new Error("Gateway HTTP error");
        const data = await response.json();
        
        updateBadge(statusGateway, data.components.api_gateway === "healthy" ? "healthy" : "error", "ONLINE");
        updateBadge(statusGrpc, data.components.grpc_worker === "connected" ? "connected" : "error", data.components.grpc_worker.toUpperCase());
        updateBadge(statusRabbitmq, data.components.rabbitmq === "connected" ? "connected" : "error", data.components.rabbitmq.toUpperCase());
        updateBadge(statusConsumer, data.components.batch_consumer === "active" ? "connected" : "error", data.components.batch_consumer.toUpperCase());
    } catch (err) {
        updateBadge(statusGateway, "error", "OFFLINE");
        updateBadge(statusGrpc, "error", "UNKNOWN");
        updateBadge(statusRabbitmq, "error", "UNKNOWN");
        updateBadge(statusConsumer, "error", "UNKNOWN");
    }

    // Fetch Performance Metrics
    try {
        const resStats = await fetch(`${API_BASE_URL}/stats`);
        if (resStats.ok) {
            const stats = await resStats.json();
            metricSyncCount.textContent = stats.total_sync_requests;
            metricAsyncCount.textContent = stats.total_async_requests;
            metricAvgLatency.textContent = `${stats.average_sync_latency_ms} ms`;
        }
    } catch (err) {
        console.warn("Failed to fetch stats:", err);
    }
}

function updateBadge(elem, type, text) {
    if (!elem) return;
    elem.textContent = text;
    if (type === "healthy" || type === "connected") {
        elem.className = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
    } else {
        elem.className = "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30";
    }
}

// ----------------------------------------------------
// 2. Synchronous Inference (gRPC)
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
    btnSync.innerHTML = `<span>Executing gRPC Predict...</span>`;

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
        btnSync.innerHTML = `<span>Run Synchronous Inference</span><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>`;
    }
});

// ----------------------------------------------------
// 3. Asynchronous Batch Inference (RabbitMQ)
// ----------------------------------------------------
formAsync.addEventListener("submit", async (e) => {
    e.preventDefault();
    const reqId = asyncReqId.value.trim();
    const model = asyncModelName.value.trim();
    const tensorValues = asyncTensor.value.split(",").map(v => parseFloat(v.trim())).filter(v => !isNaN(v));

    if (tensorValues.length === 0) {
        alert("Please enter a valid comma-separated numeric tensor");
        return;
    }

    btnAsync.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/predict/async`, {
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
            throw new Error(errData.detail || "Enqueue batch job failed");
        }

        const data = await response.json();
        addAsyncLogRow(data.request_id, data.queue, data.status.toUpperCase());
        
        asyncReqId.value = generateNextReqId(reqId, "batch");
        checkSystemHealth();
    } catch (err) {
        alert(`Asynchronous Inference Error: ${err.message}`);
    } finally {
        btnAsync.disabled = false;
    }
});

let isFirstLog = true;
function addAsyncLogRow(reqId, queue, status) {
    if (isFirstLog) {
        asyncLogBody.innerHTML = "";
        isFirstLog = false;
    }
    const timeStr = new Date().toLocaleTimeString();
    const row = document.createElement("tr");
    row.innerHTML = `
        <td class="p-2 text-slate-400">${timeStr}</td>
        <td class="p-2 font-bold text-white">${reqId}</td>
        <td class="p-2 text-amber-400">${queue}</td>
        <td class="p-2 text-right"><span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30">${status}</span></td>
    `;
    asyncLogBody.prepend(row);
}

// Helper to auto-increment request IDs
function generateNextReqId(current, prefix) {
    const num = parseInt(current.replace(/\D/g, '')) || 1;
    const nextNum = num + 1;
    return `${prefix}-${String(nextNum).padStart(3, '0')}`;
}

// ----------------------------------------------------
// 4. Live Webcam Stream & WebRTC (getUserMedia)
// ----------------------------------------------------
btnStartCam.addEventListener("click", async () => {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        videoElem.srcObject = mediaStream;
        videoElem.classList.remove("hidden");
        videoPlaceholder.classList.add("hidden");
        
        btnStartCam.disabled = true;
        btnStopCam.disabled = false;

        videoElem.onloadedmetadata = () => {
            streamRes.textContent = `${videoElem.videoWidth}x${videoElem.videoHeight}`;
            startFpsCounter();
        };
    } catch (err) {
        alert(`Webcam access denied or unavailable: ${err.message}`);
    }
});

btnStopCam.addEventListener("click", () => {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    videoElem.srcObject = null;
    videoElem.classList.add("hidden");
    videoPlaceholder.classList.remove("hidden");
    
    btnStartCam.disabled = false;
    btnStopCam.disabled = true;
    streamRes.textContent = "N/A";
    streamFps.textContent = "0.0";
    if (fpsAnimationId) cancelAnimationFrame(fpsAnimationId);
});

function startFpsCounter() {
    fpsFrameCount++;
    const now = performance.now();
    const elapsed = now - lastFpsCheck;
    if (elapsed >= 1000) {
        const fps = (fpsFrameCount * 1000 / elapsed).toFixed(1);
        streamFps.textContent = fps;
        fpsFrameCount = 0;
        lastFpsCheck = now;
    }
    fpsAnimationId = requestAnimationFrame(startFpsCounter);
}

// ----------------------------------------------------
// 5. WebSocket Signaling Client
// ----------------------------------------------------
btnConnectWs.addEventListener("click", () => {
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
        logWsMessage("WebSocket is already connected.", "info");
        return;
    }

    updateWsBadge("CONNECTING", "bg-amber-500/10 text-amber-400 border-amber-500/30");
    wsClient = new WebSocket(WS_BASE_URL);

    wsClient.onopen = () => {
        updateWsBadge("CONNECTED", "bg-emerald-500/10 text-emerald-400 border-emerald-500/30");
        btnSendPing.disabled = false;
        logWsMessage("WebSocket signaling channel established.", "success");
    };

    wsClient.onmessage = (event) => {
        logWsMessage(`Rx: ${event.data}`, "rx");
    };

    wsClient.onerror = (err) => {
        logWsMessage(`WebSocket Error`, "error");
    };

    wsClient.onclose = () => {
        updateWsBadge("DISCONNECTED", "bg-slate-800 text-slate-400");
        btnSendPing.disabled = true;
        logWsMessage("WebSocket connection closed.", "info");
    };
});

btnSendPing.addEventListener("click", () => {
    if (wsClient && wsClient.readyState === WebSocket.OPEN) {
        const offerPayload = {
            type: "offer",
            sdp: "v=0\r\no=- 123456 2 IN IP4 127.0.0.1\r\ns=ML-Gateway-WebRTC-Demo...",
            timestamp: Date.now()
        };
        const str = JSON.stringify(offerPayload);
        wsClient.send(str);
        logWsMessage(`Tx (Offer): ${str}`, "tx");
    }
});

function updateWsBadge(text, classes) {
    statusWs.textContent = text;
    statusWs.className = `px-2 py-0.5 rounded text-[10px] font-bold border ${classes}`;
}

function logWsMessage(msg, type) {
    const div = document.createElement("div");
    div.className = "p-1.5 rounded text-[11px] font-mono break-all ";
    if (type === "tx") div.className += "bg-cyan-950/60 text-cyan-300 border border-cyan-800/40";
    else if (type === "rx") div.className += "bg-emerald-950/60 text-emerald-300 border border-emerald-800/40";
    else if (type === "success") div.className += "bg-emerald-950/30 text-emerald-400";
    else if (type === "error") div.className += "bg-rose-950/60 text-rose-300";
    else div.className += "bg-slate-900 text-slate-400";
    
    div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    wsLog.appendChild(div);
    wsLog.scrollTop = wsLog.scrollHeight;
}

// ----------------------------------------------------
// Init
// ----------------------------------------------------
btnRefreshAll.addEventListener("click", checkSystemHealth);
checkSystemHealth();
setInterval(checkSystemHealth, 5000);
