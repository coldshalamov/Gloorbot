async function fetchStatus() {
  const res = await fetch("/api/v1/status");
  if (!res.ok) return null;
  return await res.json();
}

function setStatus(status) {
  const el = document.getElementById("status");
  if (!status) {
    el.innerHTML = `<div class="row"><span class="k">Server</span><span>offline</span></div>`;
    return;
  }
  const rows = [
    ["UTC", status.utc],
    ["Active clients", String(status.clients.active)],
    ["Tasks total", String(status.tasks.total)],
    ["Tasks leased", String(status.tasks.leased)],
    ["Tasks completed", String(status.tasks.completed)],
  ];
  el.innerHTML = rows.map(([k, v]) => `<div class="row"><span class="k">${k}</span><span>${v}</span></div>`).join("");
}

function fmtMoney(n) {
  try { return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(n); }
  catch { return `$${n.toFixed(2)}`; }
}

function renderDeals(deals) {
  const tbody = document.getElementById("deals");
  tbody.innerHTML = deals.map(d => {
    const pct = Math.round(d.pct_off * 100);
    const normalizedStore = d.store_name?.replace(/Lowe's of /i, "") || d.store_id;
    return `<tr>
      <td><span class="pill" title="${d.store_name || d.store_id}">${normalizedStore.slice(0, 20)}</span></td>  
      <td class="item"><a target="_blank" rel="noreferrer" href="${d.product_url}">${escapeHtml(d.title).slice(0, 110)}</a></td>
      <td>${fmtMoney(d.price)}</td>
      <td>${fmtMoney(d.was_price)}</td>
      <td><span class="pill good">${pct}%</span></td>
      <td>${d.last_seen_at}</td>
    </tr>`;
  }).join("");
}

function escapeHtml(s) {
  return (s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

async function refresh() {
  const status = await fetchStatus();
  setStatus(status);
  if (status?.recent_deals) renderDeals(status.recent_deals);
}

refresh();
setInterval(refresh, 5000);

const es = new EventSource("/api/v1/events");
es.addEventListener("deals", () => refresh());
es.addEventListener("task", () => refresh());
es.addEventListener("client", () => refresh());

