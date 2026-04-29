const API_BASE = window.location.origin;

// === KPI ===
async function fetchOverview() {
    const res = await fetch(`${API_BASE}/api/stats/overview`);
    const data = await res.json();

    document.getElementById("total-requests").textContent =
        data.total_requests.toLocaleString();
    document.getElementById("success-rate").textContent =
        data.success_rate + "%";
    document.getElementById("p95-latency").textContent =
        data.p95_duration_ms ? data.p95_duration_ms.toFixed(0) + "ms" : "-";
}

// === Chart ===
let nodeChart = null;

async function fetchNodeStats() {
    const res = await fetch(`${API_BASE}/api/stats/nodes`);
    const data = await res.json();

    if (!data.length) return;

    const labels = data.map(d => d.node_name);
    const durations = data.map(d => d.avg_duration_ms);
    const errors = data.map(d => d.error_count);

    if (nodeChart) {
        nodeChart.data.labels = labels;
        nodeChart.data.datasets[0].data = durations;
        nodeChart.data.datasets[1].data = errors;
        nodeChart.update();
        return;
    }

    nodeChart = new Chart(document.getElementById("node-chart"), {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Avg Duration (ms)",
                    data: durations,
                    backgroundColor: "#38bdf8",
                    borderRadius: 4,
                },
                {
                    label: "Errors",
                    data: errors,
                    backgroundColor: "#f87171",
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            scales: {
                x: { grid: { color: "#334155" }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "#334155" }, ticks: { color: "#94a3b8" } },
            },
            plugins: {
                legend: { labels: { color: "#e2e8f0" } },
            },
        },
    });
}

// === Traces ===
async function fetchTraces() {
    const res = await fetch(`${API_BASE}/api/stats/traces?limit=50`);
    const data = await res.json();

    const tbody = document.getElementById("traces-body");
    tbody.innerHTML = "";

    data.forEach(trace => {
        const tr = document.createElement("tr");
        tr.className = "trace-row";
        tr.onclick = () => showTraceDetail(trace.trace_id);

        const time = trace.created_at
            ? new Date(trace.created_at + "Z").toLocaleTimeString()
            : "-";
        const statusClass = trace.status === "success" ? "status-success" : "status-error";

        tr.innerHTML = `
            <td>${time}</td>
            <td>${trace.input_type}</td>
            <td>${escapeHtml(trace.user_text || "-")}</td>
            <td>${trace.total_duration_ms ? trace.total_duration_ms.toFixed(0) + "ms" : "-"}</td>
            <td class="${statusClass}">${trace.status}</td>
        `;
        tbody.appendChild(tr);
    });
}

// === Trace Detail ===
async function showTraceDetail(traceId) {
    const res = await fetch(`${API_BASE}/api/stats/traces/${traceId}`);
    const data = await res.json();
    if (data.error) { alert(data.error); return; }

    const detail = document.getElementById("trace-detail");
    const time = data.created_at
        ? new Date(data.created_at + "Z").toLocaleString()
        : "-";

    detail.innerHTML = `
        <div class="trace-meta">
            <div class="trace-meta-item">
                <label>Trace ID</label>
                <span>${data.trace_id.slice(0, 8)}...</span>
            </div>
            <div class="trace-meta-item">
                <label>Total Duration</label>
                <span>${data.total_duration_ms ? data.total_duration_ms.toFixed(0) + "ms" : "-"}</span>
            </div>
            <div class="trace-meta-item">
                <label>Status</label>
                <span class="${data.status === 'success' ? 'status-success' : 'status-error'}">${data.status}</span>
            </div>
            <div class="trace-meta-item">
                <label>Time</label>
                <span>${time}</span>
            </div>
        </div>
        <h3>Spans (${data.spans.length})</h3>
        <ul class="span-list">
            ${data.spans.map(s => `
                <li class="span-item">
                    <span class="span-name">${s.node_name}</span>
                    <span class="span-duration">${s.duration_ms ? s.duration_ms.toFixed(1) + "ms" : "-"}</span>
                    <span class="span-summary">${escapeHtml(s.output_summary || s.input_summary || "-")}</span>
                </li>
            `).join("")}
        </ul>
    `;

    document.getElementById("trace-modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("trace-modal").classList.add("hidden");
}

// Close modal on background click
document.getElementById("trace-modal").addEventListener("click", function(e) {
    if (e.target === this) closeModal();
});

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// === Auto Refresh ===
async function refreshAll() {
    try {
        await Promise.all([fetchOverview(), fetchNodeStats(), fetchTraces()]);
    } catch (e) {
        console.error("Refresh failed:", e);
    }
}

// Init
refreshAll();
setInterval(refreshAll, 5000);
