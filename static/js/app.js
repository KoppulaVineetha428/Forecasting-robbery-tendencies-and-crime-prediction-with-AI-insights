// CrimeSense AI (India) - frontend logic

function fmtNum(n) {
  return new Intl.NumberFormat("en-IN").format(n);
}

async function getJSON(url, opts) {
  const res = await fetch(url, opts);
  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = window.PAGE;
  const ready = window.__libsReady || Promise.resolve();
  ready.then(() => {
    if (page === "dashboard") initDashboard();
    if (page === "dataset") initDataset();
    if (page === "train") initTrain();
    if (page === "predict") initPredict();
    if (page === "hotspot") initHotspot();
    if (page === "reports") initReports();
    if (page === "model_insights") initModelInsights();
    if (page === "sos") initSOS();
    if (page === "contacts") initContacts();
  });
});

// ---------------- Dashboard ----------------
async function initDashboard() {
  const stats = await getJSON("/api/stats");
  document.getElementById("kpi-total").textContent = fmtNum(stats.total_crimes);
  document.getElementById("kpi-robberies").textContent = fmtNum(stats.robberies);
  document.getElementById("kpi-highrisk").textContent = fmtNum(stats.high_risk_areas);
  document.getElementById("kpi-accuracy").textContent = stats.accuracy + "%";

  new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: {
      labels: stats.month_labels,
      datasets: [{
        label: "Incidents",
        data: stats.month_counts,
        borderColor: "#22d3ee",
        backgroundColor: "rgba(34,211,238,0.15)",
        fill: true, tension: 0.35, pointRadius: 3
      }]
    },
    options: chartBaseOptions()
  });

  new Chart(document.getElementById("typeChart"), {
    type: "doughnut",
    data: {
      labels: stats.crime_labels,
      datasets: [{
        data: stats.crime_counts,
        backgroundColor: ["#ef4444", "#f59e0b", "#3b82f6", "#818cf8", "#22c55e"]
      }]
    },
    options: { plugins: { legend: { labels: { color: "#cbd5e1" } } } }
  });

  new Chart(document.getElementById("cityChart"), {
    type: "bar",
    data: {
      labels: stats.cities,
      datasets: [{
        label: "Avg Risk Score",
        data: stats.city_scores,
        backgroundColor: "#818cf8"
      }]
    },
    options: chartBaseOptions()
  });
}

function chartBaseOptions() {
  return {
    plugins: { legend: { labels: { color: "#cbd5e1" } } },
    scales: {
      x: { ticks: { color: "#94a3b8" }, grid: { color: "#1f2937" } },
      y: { ticks: { color: "#94a3b8" }, grid: { color: "#1f2937" } }
    }
  };
}

// ---------------- Dataset ----------------
let currentPage = 1;
async function loadDatasetPage(p) {
  const data = await getJSON(`/api/dataset?page=${p}`);
  const body = document.getElementById("dataset-body");
  body.innerHTML = "";
  data.rows.forEach(r => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${r.id}</td><td>${r.date}</td><td>${r.time}</td><td>${r.day}</td>
      <td>${r.city}</td><td>${r.area}</td><td>${r.area_type}</td><td>${r.weather}</td>
      <td>${r.crime_type}</td><td>${r.risk_score}</td><td>${r.risk_level}</td>`;
    body.appendChild(tr);
  });
  const totalPages = Math.ceil(data.total / data.per_page);
  const pag = document.getElementById("pagination");
  pag.innerHTML = `
    <button id="prev-btn" ${p<=1?"disabled":""}>← Prev</button>
    <span class="muted">Page ${p} of ${totalPages} (${fmtNum(data.total)} rows)</span>
    <button id="next-btn" ${p>=totalPages?"disabled":""}>Next →</button>`;
  document.getElementById("prev-btn").onclick = () => { currentPage--; loadDatasetPage(currentPage); };
  document.getElementById("next-btn").onclick = () => { currentPage++; loadDatasetPage(currentPage); };
}
function initDataset() { loadDatasetPage(1); }

// ---------------- Train ----------------
function initTrain() {
  const btn = document.getElementById("retrain-btn");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    document.getElementById("progress-wrap").style.display = "block";
    document.getElementById("train-status").textContent = "Training...";
    document.getElementById("train-status").className = "";
    const fill = document.getElementById("progress-fill");
    let pct = 0;
    const timer = setInterval(() => {
      pct = Math.min(pct + 8, 92);
      fill.style.width = pct + "%";
    }, 200);

    const res = await getJSON("/api/train", { method: "POST" });
    clearInterval(timer);
    fill.style.width = "100%";
    if (res.success) {
      document.getElementById("train-accuracy").textContent = res.accuracy + "%";
      document.getElementById("train-status").textContent = "Trained Successfully";
      document.getElementById("train-status").className = "status-ok";
      document.getElementById("train-log").textContent = "Model retrained on latest dataset.";
    } else {
      document.getElementById("train-status").textContent = "Training Failed";
      document.getElementById("train-log").textContent = res.error || "Unknown error";
    }
    btn.disabled = false;
  });
}

// ---------------- Predict ----------------
function populateSelect(id, options) {
  const el = document.getElementById(id);
  el.innerHTML = options.map(o => `<option value="${o}">${o}</option>`).join("");
}

function initPredict() {
  const cities = Object.keys(window.CITIES_MAP || {});
  populateSelect("f-city", cities);
  populateSelect("f-areatype", window.AREA_TYPES || []);
  populateSelect("f-weather", window.WEATHER_OPTIONS || []);
  populateSelect("f-day", window.DAYS || []);

  function refreshAreas() {
    const city = document.getElementById("f-city").value;
    const areas = (window.CITIES_MAP && window.CITIES_MAP[city]) || [];
    populateSelect("f-area", areas);
  }
  document.getElementById("f-city").addEventListener("change", refreshAreas);
  refreshAreas();

  const dateInput = document.getElementById("f-date");
  dateInput.value = new Date().toISOString().split("T")[0];

  let probChart = null;
  document.getElementById("predict-btn").addEventListener("click", async () => {
    const payload = {
      city: document.getElementById("f-city").value,
      area: document.getElementById("f-area").value,
      area_type: document.getElementById("f-areatype").value,
      weather: document.getElementById("f-weather").value,
      day: document.getElementById("f-day").value,
      date: document.getElementById("f-date").value,
      time: document.getElementById("f-time").value,
    };
    const res = await getJSON("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.success) {
      alert("Prediction failed: " + res.error);
      return;
    }
    document.getElementById("result-empty").style.display = "none";
    document.getElementById("result-box").style.display = "block";
    document.getElementById("res-crime").textContent = res.predicted_crime_type;
    document.getElementById("res-score").textContent = res.risk_score + "%";
    document.getElementById("res-level").textContent = res.risk_level;
    document.getElementById("res-action").textContent = res.suggested_action;

    const ctx = document.getElementById("probChart");
    const labels = Object.keys(res.probabilities);
    const values = Object.values(res.probabilities);
    if (probChart) probChart.destroy();
    probChart = new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label: "Probability %", data: values, backgroundColor: "#22d3ee" }] },
      options: chartBaseOptions()
    });

    renderLocationSection(res.similar_cases, res.location_stats, payload.city);
  });
}

let locMonthChart = null, locTypeChart = null, locTopAreasChart = null;
function renderLocationSection(cases, stats, cityName) {
  const section = document.getElementById("location-section");
  section.style.display = "block";

  const casesBody = document.getElementById("cases-body");
  if (cases.length) {
    casesBody.innerHTML = cases.map(c => `
      <tr><td>${c.date}</td><td>${c.time}</td><td>${c.day}</td><td>${c.crime_type}</td>
      <td>${c.risk_level} (${c.risk_score}%)</td><td class="muted">${c.narrative}</td></tr>
    `).join("");
  } else {
    casesBody.innerHTML = `<tr><td colspan="6" class="muted">No previous cases found for this exact area in the dataset.</td></tr>`;
  }

  document.getElementById("loc-city-name").textContent = cityName;

  if (locMonthChart) locMonthChart.destroy();
  locMonthChart = new Chart(document.getElementById("locMonthChart"), {
    type: "line",
    data: { labels: stats.month_labels, datasets: [{ label: "Incidents", data: stats.month_counts, borderColor: "#22d3ee", backgroundColor: "rgba(34,211,238,0.15)", fill: true, tension: 0.35 }] },
    options: chartBaseOptions()
  });

  if (locTypeChart) locTypeChart.destroy();
  locTypeChart = new Chart(document.getElementById("locTypeChart"), {
    type: "doughnut",
    data: { labels: stats.type_labels, datasets: [{ data: stats.type_counts, backgroundColor: ["#ef4444","#f59e0b","#3b82f6","#818cf8","#22c55e"] }] },
    options: { plugins: { legend: { labels: { color: "#cbd5e1", font: { size: 10 } } } } }
  });

  if (locTopAreasChart) locTopAreasChart.destroy();
  locTopAreasChart = new Chart(document.getElementById("locTopAreasChart"), {
    type: "bar",
    data: { labels: stats.top_areas_labels, datasets: [{ label: "Avg Risk Score", data: stats.top_areas_scores, backgroundColor: "#818cf8" }] },
    options: { ...chartBaseOptions(), indexAxis: "y" }
  });
}

// ---------------- Hotspot ----------------
let leafletMap = null;
let heatLayer = null;
let markerLayer = null;
async function loadHeat(city) {
  const data = await getJSON(`/api/hotspot-points${city ? "?city=" + encodeURIComponent(city) : ""}`);
  const pts = data.points.map(p => [p[0], p[1], Math.min(p[2] / 100, 1)]);
  if (heatLayer) leafletMap.removeLayer(heatLayer);
  heatLayer = L.heatLayer(pts, { radius: 22, blur: 18, maxZoom: 12 }).addTo(leafletMap);

  if (markerLayer) leafletMap.removeLayer(markerLayer);
  markerLayer = L.layerGroup();
  const riskColor = { High: "#ef4444", Medium: "#f59e0b", Low: "#22c55e" };
  data.incidents.forEach(inc => {
    const marker = L.circleMarker([inc.latitude, inc.longitude], {
      radius: 5,
      color: riskColor[inc.risk_level] || "#3b82f6",
      fillColor: riskColor[inc.risk_level] || "#3b82f6",
      fillOpacity: 0.7,
      weight: 1,
    });
    marker.bindPopup(`
      <div style="font-family:inherit; min-width:200px;">
        <b>${inc.area}, ${inc.city}</b><br/>
        <span style="color:${riskColor[inc.risk_level]}; font-weight:600;">${inc.crime_type} · ${inc.risk_level} risk (${inc.risk_score}%)</span><br/>
        <span style="font-size:12px;">${inc.date} at ${inc.time}</span><br/>
        <span style="font-size:12px; color:#555;">${inc.narrative}</span>
      </div>
    `);
    markerLayer.addLayer(marker);
  });
  markerLayer.addTo(leafletMap);

  if (pts.length) {
    const bounds = L.latLngBounds(pts.map(p => [p[0], p[1]]));
    leafletMap.fitBounds(bounds, { padding: [20, 20] });
  }
}
function initHotspot() {
  leafletMap = L.map("map").setView([22.9734, 78.6569], 5); // India center
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 18
  }).addTo(leafletMap);
  loadHeat("");
  document.getElementById("hotspot-city").addEventListener("change", (e) => loadHeat(e.target.value));
}

// ---------------- Model Insights ----------------
async function initModelInsights() {
  const data = await getJSON("/api/model-insights");
  if (!data.available) {
    document.querySelector(".page").innerHTML = "<p class='muted'>No evaluation data found. Retrain the model from the Train Model page first.</p>";
    return;
  }

  document.getElementById("mi-accuracy").textContent = data.accuracy + "%";
  document.getElementById("mi-macrof1").textContent = data.macro_f1 + "%";
  document.getElementById("mi-weightedf1").textContent = data.weighted_f1 + "%";

  const fi = data.feature_importance;
  new Chart(document.getElementById("importanceChart"), {
    type: "bar",
    data: {
      labels: fi.map(f => f.feature),
      datasets: [{ label: "Importance %", data: fi.map(f => f.importance), backgroundColor: "#22d3ee" }]
    },
    options: { ...chartBaseOptions(), indexAxis: "y" }
  });

  const metricsBody = document.getElementById("metrics-body");
  metricsBody.innerHTML = data.class_labels.map(label => {
    const m = data.per_class_metrics[label];
    return `<tr><td>${label}</td><td>${m.precision}%</td><td>${m.recall}%</td><td>${m.f1}%</td><td>${m.support}</td></tr>`;
  }).join("");

  // Confusion matrix as a colored HTML table
  const labels = data.class_labels;
  const cm = data.confusion_matrix;
  const maxVal = Math.max(...cm.flat());
  let html = '<table class="data-table cm-table"><thead><tr><th>Actual \\ Predicted</th>';
  labels.forEach(l => html += `<th>${l}</th>`);
  html += "</tr></thead><tbody>";
  cm.forEach((row, i) => {
    html += `<tr><td><b>${labels[i]}</b></td>`;
    row.forEach((val, j) => {
      const intensity = maxVal ? val / maxVal : 0;
      const isDiag = i === j;
      const bg = isDiag
        ? `rgba(34,197,94,${0.15 + intensity * 0.6})`
        : `rgba(239,68,68,${intensity * 0.35})`;
      html += `<td style="background:${bg}; text-align:center;">${val}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  document.getElementById("cm-wrap").innerHTML = html;
}

// ---------------- SOS ----------------
let sosLat = null, sosLon = null, sosAddress = "";

function requestLocation() {
  const statusEl = document.getElementById("loc-status");
  if (!navigator.geolocation) {
    statusEl.textContent = "Location: geolocation not supported by this browser";
    return;
  }
  statusEl.textContent = "Location: requesting permission...";
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      sosLat = pos.coords.latitude;
      sosLon = pos.coords.longitude;
      statusEl.textContent = `Location: captured (${sosLat.toFixed(4)}, ${sosLon.toFixed(4)})`;
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${sosLat}&lon=${sosLon}`);
        const data = await res.json();
        sosAddress = data.display_name || "";
        if (sosAddress) statusEl.textContent = `Location: ${sosAddress}`;
      } catch (e) { /* reverse geocoding is best-effort; ignore failures */ }
    },
    (err) => { statusEl.textContent = "Location: permission denied or unavailable — " + err.message; },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

async function loadSOSHistory() {
  const rows = await getJSON("/api/sos/history");
  const body = document.getElementById("sos-history-body");
  if (rows.length) {
    body.innerHTML = rows.map(r => `
      <tr><td>${new Date(r.created_at).toLocaleString()}</td><td>${r.note || "-"}</td>
      <td class="muted">${r.address || (r.latitude ? r.latitude.toFixed(3)+","+r.longitude.toFixed(3) : "-")}</td>
      <td>${r.email_status}</td><td>${r.sms_status}</td></tr>
    `).join("");
  }
}

function initSOS() {
  requestLocation();
  loadSOSHistory();

  document.getElementById("sos-btn").addEventListener("click", async () => {
    document.getElementById("sos-idle").style.display = "none";
    document.getElementById("sos-sending").style.display = "block";

    const note = document.getElementById("sos-note").value;
    const res = await getJSON("/api/sos/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude: sosLat, longitude: sosLon, note, address: sosAddress })
    });

    document.getElementById("sos-sending").style.display = "none";
    document.getElementById("sos-result").style.display = "block";
    document.getElementById("sos-contacts-count").textContent = res.contacts_notified;
    document.getElementById("sos-email-status").textContent = res.email_status;
    document.getElementById("sos-sms-status").textContent = res.sms_status;
    loadSOSHistory();
  });

  document.getElementById("sos-reset-btn").addEventListener("click", () => {
    document.getElementById("sos-result").style.display = "none";
    document.getElementById("sos-idle").style.display = "block";
    document.getElementById("sos-note").value = "";
  });
}

// ---------------- Contacts ----------------
async function loadContacts() {
  const contacts = await getJSON("/api/contacts");
  const list = document.getElementById("contacts-list");
  if (!contacts.length) {
    list.innerHTML = '<p class="muted">No contacts added yet.</p>';
    return;
  }
  list.innerHTML = contacts.map(c => `
    <div class="contact-item">
      <div class="c-info">
        <b>${c.name} ${c.relation ? "(" + c.relation + ")" : ""}</b>
        <span>${c.phone || "no phone"} · ${c.email || "no email"}</span>
      </div>
      <button class="c-delete" data-id="${c.id}">Remove</button>
    </div>
  `).join("");
  list.querySelectorAll(".c-delete").forEach(btn => {
    btn.addEventListener("click", async () => {
      await fetch(`/api/contacts/${btn.dataset.id}`, { method: "DELETE" });
      loadContacts();
    });
  });
}

function initContacts() {
  loadContacts();
  document.getElementById("add-contact-btn").addEventListener("click", async () => {
    const name = document.getElementById("c-name").value.trim();
    if (!name) { alert("Name is required"); return; }
    await fetch("/api/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        relation: document.getElementById("c-relation").value.trim(),
        phone: document.getElementById("c-phone").value.trim(),
        email: document.getElementById("c-email").value.trim(),
      })
    });
    document.getElementById("c-name").value = "";
    document.getElementById("c-relation").value = "";
    document.getElementById("c-phone").value = "";
    document.getElementById("c-email").value = "";
    loadContacts();
  });
}

// ---------------- Reports ----------------
async function initReports() {
  const rep = await getJSON("/api/reports");
  new Chart(document.getElementById("yearChart"), {
    type: "bar",
    data: { labels: rep.years, datasets: [{ label: "Crimes", data: rep.year_counts, backgroundColor: "#3b82f6" }] },
    options: chartBaseOptions()
  });
  new Chart(document.getElementById("timeChart"), {
    type: "pie",
    data: {
      labels: rep.time_labels,
      datasets: [{ data: rep.time_counts, backgroundColor: ["#1e293b", "#f59e0b", "#3b82f6", "#818cf8"] }]
    },
    options: { plugins: { legend: { labels: { color: "#cbd5e1", font: { size: 10 } } } } }
  });
  new Chart(document.getElementById("areaChart"), {
    type: "bar",
    data: { labels: rep.top_area_labels, datasets: [{ label: "Incidents", data: rep.top_area_counts, backgroundColor: "#22c55e" }] },
    options: { ...chartBaseOptions(), indexAxis: "y" }
  });

  const recents = await getJSON("/api/recent-predictions");
  const body = document.getElementById("recent-body");
  if (recents.length) {
    body.innerHTML = recents.map(r => `
      <tr><td>${r.city}</td><td>${r.area}</td><td>${r.date}</td><td>${r.time}</td>
      <td>${r.predicted_crime_type}</td><td>${r.risk_level} (${r.risk_score}%)</td></tr>
    `).join("");
  }
}
