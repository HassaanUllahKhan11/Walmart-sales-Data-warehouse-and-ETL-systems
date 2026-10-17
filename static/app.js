(() => {
  const $ = (id) => document.getElementById(id);
  const initial = JSON.parse($("initial-data").textContent);
  let current = initial;
  const charts = {};
  const tables = {};

  const fmt = {
    money: (v) => "$" + Math.round(v).toLocaleString("en-US"),
    money2: (v) => "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    int: (v) => Math.round(v).toLocaleString("en-US"),
    pct: (v) => Math.round(v * 100) + "%",
    short: (v) => (Math.abs(v) >= 1000 ? "$" + +(v / 1000).toFixed(v >= 10000 ? 0 : 1) + "k" : "$" + Math.round(v)),
  };
  const date = (iso, opts = { month: "short", day: "numeric" }) =>
    new Date(iso + "T00:00:00").toLocaleDateString("en-US", opts);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function renderHeader(d) {
    $("store-name").textContent = d.source.name;
    $("store-meta").textContent =
      `${date(d.first_day, { month: "short", day: "numeric", year: "numeric" })} to ` +
      `${date(d.as_of, { month: "short", day: "numeric", year: "numeric" })} · ` +
      `${d.source.orders.toLocaleString("en-US")} orders`;
    $("reset").hidden = d.source.sample;
    $("week-label").textContent = `Week of ${date(d.week.start)} to ${date(d.week.end)}`;
  }

  function renderNotes(d) {
    const marks = { up: "▲", down: "▼", neutral: "•" };
    $("notes").innerHTML = d.insights
      .map((n) => `<li class="${n.tone}"><span class="mark" aria-hidden="true">${marks[n.tone]}</span>` +
        `<div><strong>${esc(n.title)}</strong><p>${esc(n.text)}</p></div></li>`)
      .join("");
  }

  function renderKpis(d) {
    $("kpis").innerHTML = d.kpis.map((k) => {
      let delta = "";
      if (k.note) {
        delta = esc(k.note);
      } else if (k.delta !== null && k.delta !== undefined) {
        const up = k.delta >= 0;
        const n = Math.abs(Math.round(k.delta * 100));
        const size = k.format === "pct" ? n + (n === 1 ? " pt" : " pts") : n + "%";
        delta = `<b class="${up ? "good" : "bad"}">${up ? "▲" : "▼"} ${size}</b> vs previous 30 days`;
      } else {
        delta = "No earlier period to compare";
      }
      return `<div class="kpi"><div class="label">${esc(k.label)}</div>` +
        `<div class="value">${fmt[k.format](k.value)}</div><div class="delta">${delta}</div></div>`;
    }).join("");
  }

  function renderProducts(d) {
    const max = Math.max(...d.top_products.map((p) => p.revenue), 1);
    const rows = d.top_products.map((p) => {
      let chg = "<td class=\"chg\">new</td>";
      if (p.change !== null) {
        const up = p.change >= 0;
        chg = `<td class="chg ${up ? "good" : "bad"}">${up ? "▲" : "▼"} ${Math.abs(Math.round(p.change * 100))}%</td>`;
      }
      return `<tr><td class="name">${esc(p.product)}<div class="bar" style="width:${(p.revenue / max) * 100}%"></div></td>` +
        `<td>${fmt.money(p.revenue)}</td><td>${p.units.toLocaleString("en-US")}</td>${chg}</tr>`;
    }).join("");
    $("products").innerHTML = `<thead><tr><th>Product</th><th>Revenue</th><th>Units</th><th>Change</th></tr></thead><tbody>${rows}</tbody>`;
  }

  function legend(id, items) {
    $(id).innerHTML = items
      .map((it) => `<span><i class="${it.cls || ""}" style="background:${it.color}"></i>${esc(it.label)}</span>`)
      .join("");
  }

  function table(id, head, rows) {
    tables[id] = `<table><thead><tr>${head.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>` +
      rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("") + "</tbody></table>";
    const el = $(id + "-table");
    if (!el.hidden) el.innerHTML = tables[id];
  }

  function baseOptions(extra = {}) {
    const muted = css("--muted");
    const grid = css("--grid");
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: css("--surface"),
          titleColor: css("--ink"),
          bodyColor: css("--ink-2"),
          borderColor: css("--axis"),
          borderWidth: 1,
          padding: 10,
          boxPadding: 4,
          usePointStyle: true,
          callbacks: { label: (c) => ` ${c.dataset.label}: ${c.parsed.y === null ? "n/a" : fmt.money(c.parsed.y)}` },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: muted, maxRotation: 0, autoSkipPadding: 12 } },
        y: { beginAtZero: true, grid: { color: grid }, border: { display: false }, ticks: { color: muted, callback: fmt.short, maxTicksLimit: 5 } },
      },
      ...extra,
    };
  }

  function draw(id, config) {
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart($(id), config);
  }

  function renderCharts(d) {
    const s1 = css("--series-1"), s2 = css("--series-2"), s3 = css("--series-3"), ly = css("--last-year"), surface = css("--surface");

    // weekly trend
    const w = d.weekly;
    const hasLy = w.last_year.some((v) => v !== null);
    draw("trend", {
      type: "line",
      data: {
        labels: w.labels.map((l) => date(l)),
        datasets: [
          { label: "This year", data: w.revenue, borderColor: s1, backgroundColor: s1, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, pointHoverBorderColor: surface, pointHoverBorderWidth: 2, tension: 0.25 },
          ...(hasLy ? [{ label: "Same week last year", data: w.last_year, borderColor: ly, backgroundColor: ly, borderWidth: 2, borderDash: [4, 3], pointRadius: 0, pointHoverRadius: 4, tension: 0.25 }] : []),
        ],
      },
      options: baseOptions({ plugins: { ...baseOptions().plugins, tooltip: { ...baseOptions().plugins.tooltip, callbacks: { ...baseOptions().plugins.tooltip.callbacks, title: (items) => "Week of " + items[0].label } } } }),
    });
    legend("trend-legend", [{ label: "This year", color: s1 }, ...(hasLy ? [{ label: "Same week last year", color: ly, cls: "dash" }] : [])]);
    table("trend", ["Week of", "Revenue", "Same week last year"],
      w.labels.map((l, i) => [date(l), fmt.money(w.revenue[i]), w.last_year[i] === null ? "–" : fmt.money(w.last_year[i])]).reverse());

    // new vs returning
    const m = d.customer_mix;
    draw("mix", {
      type: "bar",
      data: {
        labels: m.labels,
        datasets: [
          { label: "New customers", data: m.new, backgroundColor: s1, borderColor: surface, borderWidth: { top: 2 }, borderRadius: 0, borderSkipped: false, stack: "s" },
          { label: "Returning customers", data: m.returning, backgroundColor: s2, borderColor: surface, borderWidth: { bottom: 2 }, borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: false, stack: "s" },
        ],
      },
      options: baseOptions({
        scales: { ...baseOptions().scales, x: { ...baseOptions().scales.x, stacked: true }, y: { ...baseOptions().scales.y, stacked: true } },
        datasets: { bar: { maxBarThickness: 28, categoryPercentage: 0.7 } },
      }),
    });
    legend("mix-legend", [{ label: "New customers", color: s1, cls: "box" }, { label: "Returning customers", color: s2, cls: "box" }]);
    table("mix", ["Month", "New", "Returning", "Returning share"], m.labels.map((l, i) => {
      const t = m.new[i] + m.returning[i];
      return [l, fmt.money(m.new[i]), fmt.money(m.returning[i]), t ? fmt.pct(m.returning[i] / t) : "–"];
    }));

    // seasonality: newest year takes slot 1, so colour follows the year, not its rank
    const se = d.seasonality;
    const slots = [s1, s2, s3];
    const years = [...se.series].reverse();
    draw("season", {
      type: "line",
      data: {
        labels: se.labels,
        datasets: years.map((y, i) => ({
          label: String(y.year), data: y.values, borderColor: slots[i], backgroundColor: slots[i],
          borderWidth: 2, pointRadius: 3, pointHoverRadius: 5, pointBorderColor: surface, pointBorderWidth: 1, tension: 0.25, spanGaps: false,
        })),
      },
      options: baseOptions(),
    });
    legend("season-legend", years.map((y, i) => ({ label: String(y.year), color: slots[i] })));
    table("season", ["Month", ...years.map((y) => String(y.year))],
      se.labels.map((l, mi) => [l, ...years.map((y) => (y.values[mi] === null ? "–" : fmt.money(y.values[mi])))]));

    // weekday
    const wd = d.weekday;
    const best = wd.avg_revenue.indexOf(Math.max(...wd.avg_revenue));
    draw("weekday", {
      type: "bar",
      data: {
        labels: wd.labels,
        datasets: [{
          label: "Average revenue", data: wd.avg_revenue,
          backgroundColor: wd.avg_revenue.map((_, i) => (i === best ? s1 : css("--axis"))),
          borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: false, maxBarThickness: 44,
        }],
      },
      options: baseOptions({ interaction: { mode: "nearest", intersect: true } }),
    });
    $("weekday-sub").textContent = `Average revenue by day of week over the last ${wd.weeks} weeks. ${["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][best]} is highlighted as your best day.`;
    table("weekday", ["Day", "Average revenue"], wd.labels.map((l, i) => [l, fmt.money(wd.avg_revenue[i])]));
  }

  function render(d) {
    current = d;
    renderHeader(d);
    renderNotes(d);
    renderKpis(d);
    renderProducts(d);
    renderCharts(d);
  }

  // table toggles
  document.querySelectorAll("[data-table]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.table;
      const el = $(id + "-table");
      el.hidden = !el.hidden;
      if (!el.hidden) el.innerHTML = tables[id];
      btn.textContent = el.hidden ? "Show table" : "Hide table";
    });
  });

  // upload
  const status = $("status");
  function setStatus(msg, isError = false) {
    status.textContent = msg;
    status.classList.toggle("error", isError);
  }
  $("file-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    document.body.classList.add("loading");
    setStatus(`Reading ${file.name}…`);
    try {
      const res = await fetch("/api/upload", { method: "POST", body });
      const data = await res.json().catch(() => ({ error: "The server couldn't read that file." }));
      if (!res.ok) throw new Error(data.error || "Upload failed.");
      render(data);
      const skipped = data.source.skipped_rows ? ` (${data.source.skipped_rows} rows skipped)` : "";
      setStatus(`Showing ${file.name}: ${data.source.orders.toLocaleString("en-US")} orders${skipped}. Nothing was saved.`);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      document.body.classList.remove("loading");
      e.target.value = "";
    }
  });
  $("reset").addEventListener("click", () => { render(initial); setStatus(""); });

  // redraw charts with the right palette when the colour scheme flips
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderCharts(current));

  render(initial);
})();
