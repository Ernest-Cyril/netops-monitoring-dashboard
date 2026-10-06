/*
 * NetOps dashboard charts.
 *
 * Data flow:  SQLite -> Django view (build_chart_data) -> template json_script
 *             -> this file reads the JSON -> Chart.js draws the charts.
 * No chart values are hard-coded here.
 */
(function () {
  "use strict";

  const dataElement = document.getElementById("chart-data");
  if (!dataElement || typeof Chart === "undefined") {
    return; // nothing to draw (or Chart.js failed to load)
  }
  const data = JSON.parse(dataElement.textContent);

  const COLORS = {
    HEALTHY: "#22c55e",
    WARNING: "#f59e0b",
    CRITICAL: "#ef4444",
    OFFLINE: "#94a3b8",
  };

  Chart.defaults.color = "#8b9ab5";
  Chart.defaults.borderColor = "rgba(34, 48, 77, 0.8)";
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.maintainAspectRatio = false;

  // Colour a value by threshold: healthy / warning / critical
  function colourFor(value, warningFrom, criticalAbove) {
    if (value === null) return COLORS.OFFLINE;
    if (value > criticalAbove) return COLORS.CRITICAL;
    if (value >= warningFrom) return COLORS.WARNING;
    return COLORS.HEALTHY;
  }

  // Shorten long asset names for chart axes
  const shortLabel = (name) => (name.length > 18 ? name.slice(0, 17) + "…" : name);

  // ---------- Chart 1: Network Latency by Asset ----------
  const t = data.thresholds;
  new Chart(document.getElementById("latencyChart"), {
    type: "bar",
    data: {
      labels: data.latency.labels.map(shortLabel),
      datasets: [{
        label: "Latency (ms)",
        data: data.latency.values,
        backgroundColor: data.latency.values.map((v) => colourFor(v, t.latency_warning, t.latency_critical)),
        borderRadius: 6,
      }],
    },
    options: {
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => data.latency.labels[items[0].dataIndex],
            label: (item) => (item.raw === null ? "Offline — no data" : `${item.raw} ms`),
          },
        },
      },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: "ms" } },
        x: { ticks: { maxRotation: 45, minRotation: 30 } },
      },
    },
  });

  // ---------- Chart 2: Infrastructure Status Distribution ----------
  new Chart(document.getElementById("statusChart"), {
    type: "doughnut",
    data: {
      labels: data.status.labels,
      datasets: [{
        data: data.status.values,
        backgroundColor: [COLORS.HEALTHY, COLORS.WARNING, COLORS.CRITICAL, COLORS.OFFLINE],
        borderColor: "#111a2e",
        borderWidth: 3,
      }],
    },
    options: {
      cutout: "62%",
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, padding: 12 } } },
    },
  });

  // ---------- Chart 3: CPU Usage by Compute Asset ----------
  new Chart(document.getElementById("cpuChart"), {
    type: "bar",
    data: {
      labels: data.cpu.labels.map(shortLabel),
      datasets: [{
        label: "CPU (%)",
        data: data.cpu.values,
        backgroundColor: data.cpu.values.map((v) => colourFor(v, t.cpu_warning, t.cpu_critical)),
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: "y",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: (items) => data.cpu.labels[items[0].dataIndex], label: (item) => `${item.raw}%` } },
      },
      scales: { x: { min: 0, max: 100, title: { display: true, text: "%" } } },
    },
  });
})();
