(() => {
  const $ = (id) => document.getElementById(id);
  const D = JSON.parse($("dw-data").textContent);
  const O = D.overview;
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const slot = (i) => css(`--s${(i % 8) + 1}`);
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const charts = {};

  const fmt = {
    money: (v) => "$" + Math.round(v).toLocaleString("en-US"),
    money2: (v) => "$" + v.toFixed(2),
    short: (v) => {
      const a = Math.abs(v);
      if (a >= 1e6) return "$" + +(v / 1e6).toFixed(1) + "M";
      if (a >= 1e3) return "$" + +(v / 1e3).toFixed(a >= 1e4 ? 0 : 1) + "K";
      return "$" + Math.round(v);
    },
    int: (v) => Math.round(v).toLocaleString("en-US"),
    pct: (v) => { const r = Math.round(v); return (r > 0 ? "+" : "") + (r === 0 ? 0 : r) + "%"; },
    pctPlain: (v) => v.toFixed(0) + "%",
  };
  const tick = { money: fmt.short, money2: (v) => "$" + v, int: fmt.int, pct100: (v) => v + "%" };
  const tip = { money: fmt.money, money2: fmt.money2, int: fmt.int, pct100: (v) => v.toFixed(1) + "%" };

  const ICONS = {
    cart: '<path d="M3 4h2l2.2 10.2a1 1 0 0 0 1 .8h9.6a1 1 0 0 0 1-.8L21 8H6.2"/><circle cx="9" cy="19.5" r="1.4"/><circle cx="17" cy="19.5" r="1.4"/>',
    doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    people: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    box: '<path d="M12 3 3 7.5v9L12 21l9-4.5v-9zM3 7.5l9 4.5 9-4.5M12 12v9"/>',
    trend: '<path d="M3 17 9 11l4 4 8-8M15 7h6v6"/>',
    link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    csv: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    code: '<path d="m8 8-5 4 5 4M16 8l5 4-5 4"/>',
    rows: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  };
  const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;

  // ---------- chart helpers ----------
  function baseOptions(format = "money", extra = {}) {
    return {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: css("--surface"), titleColor: css("--ink"), bodyColor: css("--ink-2"),
          borderColor: css("--axis"), borderWidth: 1, padding: 10, boxPadding: 4, usePointStyle: true,
          callbacks: { label: (c) => ` ${c.dataset.label}: ${(tip[format] || fmt.money)(c.parsed[extra.indexAxis === "y" ? "x" : "y"])}` },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { color: css("--axis") }, ticks: { color: css("--muted"), maxRotation: 0, autoSkipPadding: 10 } },
        y: { beginAtZero: true, grid: { color: css("--grid") }, border: { display: false }, ticks: { color: css("--muted"), callback: tick[format] || fmt.short, maxTicksLimit: 5 } },
      },
      ...extra,
    };
  }

  function draw(canvas, config) {
    if (charts[canvas.id]) charts[canvas.id].destroy();
    charts[canvas.id] = new Chart(canvas, config);
  }

  function legendHTML(names) {
    return `<div class="legend">${names.map((n, i) => `<span><i style="background:${slot(i)}"></i>${esc(n)}</span>`).join("")}</div>`;
  }

  function barChart(canvas, spec) {
    const horizontal = !!spec.horizontal;
    const stacked = !!spec.stacked;
    const surface = css("--surface");
    const n = spec.series.length;
    const datasets = spec.series.map((s, i) => ({
      label: s.name, data: s.values, backgroundColor: n === 1 ? slot(0) : slot(i),
      borderColor: surface, borderWidth: stacked ? (horizontal ? { right: 2 } : { top: 2 }) : 0,
      borderSkipped: false,
      borderRadius: stacked ? (i === n - 1 ? (horizontal ? { topRight: 4, bottomRight: 4 } : { topLeft: 4, topRight: 4 }) : 0)
        : (horizontal ? { topRight: 4, bottomRight: 4 } : { topLeft: 4, topRight: 4 }),
      maxBarThickness: horizontal ? 22 : 36, categoryPercentage: 0.72, barPercentage: n > 1 && !stacked ? 0.9 : 0.8,
    }));
    const opts = baseOptions(spec.format, { indexAxis: horizontal ? "y" : "x" });
    const { x: catBase, y: valBase } = opts.scales;
    const value = { ...valBase, stacked, max: spec.format === "pct100" && stacked ? 100 : undefined };
    const cat = { ...catBase, stacked, ticks: { ...catBase.ticks, autoSkip: false } };
    if (horizontal) {
      value.grid = { color: css("--grid") };
      value.border = { display: false };
      cat.border = { color: css("--axis") };
      opts.scales = { x: value, y: cat };
      opts.interaction = { mode: "index", axis: "y", intersect: false };
    } else {
      opts.scales = { x: cat, y: value };
    }
    // wrap long category names onto two lines so every label fits
    const labels = horizontal ? spec.labels : spec.labels.map((l) => (l.length > 10 && l.includes(" ") ? l.split(/ (?=\S+$)/) : l));
    draw(canvas, { type: "bar", data: { labels, datasets }, options: opts });
  }

  // colour ramps for matrices (sequential = one blue hue; diverging = red / grey / blue)
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const rgb = (c) => `rgb(${c.join(",")})`;
  const lum = (c) => { const [r, g, b] = c.map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  function cellColor(v, scale, lo, hi) {
    const dark = document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    const mid = hex(dark ? "#383835" : "#f0efec");
    let c;
    if (scale === "div") {
      const cap = Math.max(Math.abs(lo), Math.abs(hi), 1);
      const t = Math.min(Math.abs(v) / Math.min(cap, 60), 1);
      c = mix(mid, hex(v >= 0 ? (dark ? "#3987e5" : "#256abf") : (dark ? "#e66767" : "#d03b3b")), t);
    } else {
      const t = hi > lo ? (v - lo) / (hi - lo) : 0;
      c = dark ? mix(hex("#1d2a3d"), hex("#5598e7"), t) : mix(hex("#e6f0fc"), hex("#184f95"), t);
    }
    return { bg: rgb(c), fg: lum(c) > 0.33 ? "#0e1a2b" : "#ffffff" };
  }

  function matrixHTML(spec) {
    const flat = spec.values.flat().filter((v) => v !== null);
    const lo = Math.min(...flat), hi = Math.max(...flat);
    const f = spec.format === "pct" ? (spec.scale === "div" ? fmt.pct : fmt.pctPlain) : fmt.short;
    const head = `<tr><th></th>${spec.cols.map((c) => `<th scope="col">${esc(c)}</th>`).join("")}</tr>`;
    const body = spec.rows.map((r, i) => `<tr><th scope="row">${esc(r)}</th>${spec.values[i].map((v, j) => {
      if (v === null) return `<td class="empty" title="${esc(r)} · ${esc(spec.cols[j])}: no value">–</td>`;
      const c = cellColor(v, spec.scale, lo, hi);
      return `<td style="background:${c.bg};color:${c.fg}" title="${esc(r)} · ${esc(spec.cols[j])}: ${f(v)}">${f(v)}</td>`;
    }).join("")}</tr>`).join("");
    const ends = spec.scale === "div"
      ? [cellColor(-60, "div", -60, 60).bg, cellColor(0, "div", -60, 60).bg, cellColor(60, "div", -60, 60).bg]
      : [cellColor(lo, "seq", lo, hi).bg, cellColor(hi, "seq", lo, hi).bg];
    const scaleLabel = spec.scale === "div" ? ["Decline", "Growth"] : [f(lo), f(hi)];
    return `<div class="matrix-scroll"><table class="matrix">${head}${body}</table></div>
      <div class="scale"><span>${scaleLabel[0]}</span><span class="bar" style="background:linear-gradient(90deg,${ends.join(",")})"></span><span>${scaleLabel[1]}</span></div>`;
  }

  function barlistHTML(items, format = "money", max) {
    const top = max || Math.max(...items.map((i) => i.value), 1);
    const f = format === "int" ? fmt.int : fmt.money;
    return items.map((it) => `<li><span class="name">${esc(it.label)}${it.sub ? `<small>${esc(it.sub)}</small>` : ""}</span>` +
      `<span class="val">${f(it.value)}</span><span class="track"><span class="fill" style="width:${(it.value / top) * 100}%;${it.color ? `background:${it.color}` : ""}"></span></span></li>`).join("");
  }

  // ---------- overview ----------
  function renderOverview() {
    const span = O.span.map((d) => new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" }));
    $("range").textContent = `${span[0]} – ${span[1]}`;

    const icons = ["cart", "doc", "people", "box"];
    $("kpis").innerHTML = O.kpis.map((k, i) => {
      const up = k.delta >= 0;
      return `<div class="card kpi"><div class="ico" style="background:${[slot(0), slot(6), slot(2), slot(3)][i]}">${icon(icons[i])}</div>` +
        `<div><div class="label">${esc(k.label)}</div><div class="value">${fmt[k.format](k.value)}</div>` +
        `<div class="delta"><b class="${up ? "good" : "bad"}">${up ? "▲" : "▼"} ${Math.abs(k.delta * 100).toFixed(1)}%</b> vs ${k.vs}</div></div></div>`;
    }).join("");

    const s1 = slot(0);
    draw($("ov-trend"), {
      type: "line",
      data: { labels: O.monthly.labels, datasets: [{
        label: "Sales", data: O.monthly.values, borderColor: s1, borderWidth: 2, tension: 0.3, pointRadius: 0, pointHoverRadius: 5,
        pointHoverBorderColor: css("--surface"), pointHoverBorderWidth: 2, fill: true,
        backgroundColor: (ctx) => {
          const { chart } = ctx; if (!chart.chartArea) return "transparent";
          const g = chart.ctx.createLinearGradient(0, chart.chartArea.top, 0, chart.chartArea.bottom);
          g.addColorStop(0, s1 + "33"); g.addColorStop(1, s1 + "00"); return g;
        },
      }] },
      options: baseOptions("money", { scales: { ...baseOptions().scales, x: { ...baseOptions().scales.x, ticks: { ...baseOptions().scales.x.ticks, maxTicksLimit: 8, callback(v) { const l = this.getLabelForValue(v); return l.startsWith("Jan") || l.startsWith("Jul") ? l.replace(/(\w+) (\d+)/, (m, a, b) => `${a} ${b.slice(2)}`) : ""; } } } } }),
    });

    const cats = O.categories;
    draw($("ov-donut"), {
      type: "doughnut",
      data: { labels: cats.map((c) => c.label), datasets: [{ data: cats.map((c) => c.value), backgroundColor: cats.map((_, i) => slot(i)), borderColor: css("--surface"), borderWidth: 2, hoverOffset: 4 }] },
      options: { responsive: true, maintainAspectRatio: true, animation: false, cutout: "58%", plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (c) => ` ${c.label}: ${fmt.money(c.parsed)} (${(cats[c.dataIndex].share * 100).toFixed(0)}%)` } } } },
    });
    $("ov-donut-legend").innerHTML = cats.map((c, i) => `<li><i style="background:${slot(i)}"></i><span>${esc(c.label)}</span><b>${(c.share * 100).toFixed(0)}%</b>` +
      (c.detail ? `<small>${esc(c.detail)}</small>` : "") + "</li>").join("");

    $("ov-products").innerHTML = barlistHTML(O.top_products.map((p) => ({ label: p.id, sub: p.category, value: p.value })));
    $("ov-stores").innerHTML = barlistHTML(O.stores.map((s) => ({ label: s.name, value: s.value })));
    $("ov-cities").innerHTML = barlistHTML(O.cities.map((c) => ({ label: c.name, sub: `${fmt.int(c.customers)} customers`, value: c.value })));

    $("ov-recent").innerHTML = `<thead><tr><th>Order ID</th><th>Customer</th><th class="num">Items</th><th class="num">Amount</th><th>Date</th></tr></thead><tbody>` +
      O.recent.map((r) => `<tr><td>${r.order}</td><td>${r.customer}</td><td class="num">${r.items}</td><td class="num">${fmt.money2(r.amount)}</td><td>${r.date}</td></tr>`).join("") + "</tbody>";

    const insightIcons = ["trend", "link", "people", "sun"];
    const insightColors = [slot(2), slot(6), slot(3), slot(0)];
    $("ov-insights").innerHTML = O.insights.map((n, i) => `<a class="insight" href="#${n.query}">` +
      `<span class="ico" style="color:${insightColors[i]}">${icon(insightIcons[i])}</span><strong>${esc(n.title)}</strong>` +
      `<p>${esc(n.text)}</p><span class="from">${n.query.toUpperCase()} →</span></a>`).join("");

    const st = D.stats;
    const dims = ["DIM_CUSTOMER", "DIM_PRODUCT", "DIM_TIME", "DIM_CITY", "DIM_STORE", "DIM_SUPPLIER"];
    $("ov-arch").innerHTML = [
      ["csv", "CSV files", "3 sources"],
      ["gear", "ETL", "Python join"],
      ["db", "Star schema", "SQLite"],
      ["chart", "OLAP", "20 queries"],
    ].map(([ic, t, s]) => `<li>${icon(ic)}<b>${t}</b><span>${s}</span></li>`).join("");
    $("ov-arch-foot").textContent = `${dims.length} dimension tables · 1 fact table · ${fmt.int(st.FACT_SALES)} sales rows · all 20 queries run in ${(D.query_ms / 1000).toFixed(1)} s`;
  }

  // ---------- query cards ----------
  const KW = /('[^']*')|\b(\d+(?:\.\d+)?)\b|\b(SELECT|FROM|JOIN|LEFT|ON|WHERE|GROUP|BY|ORDER|WITH|AS|CASE|WHEN|THEN|ELSE|END|SUM|COUNT|AVG|DISTINCT|ROW_NUMBER|OVER|PARTITION|UNION|ALL|AND|OR|COALESCE|ABS|DESC|CREATE|VIEW|SQRT|NULL|IS|LIMIT)\b/g;
  const highlight = (sql) => esc(sql).replace(KW, (m, str, num, kw) =>
    str ? `<span class="str">${str}</span>` : num ? `<span class="num">${num}</span>` : `<span class="kw">${kw}</span>`);

  const WIDE = new Set(["q1", "q3", "q5", "q9", "q13", "q14", "q15", "q20"]);
  const isNumCol = (c) => !/(_id|^year$|^month$|quarter|occupation|stay|rank|^age$)/.test(c);

  function cellText(v, col) {
    if (v === null) return "NULL";
    if (typeof v === "number" && isNumCol(col)) return Number.isInteger(v) ? v.toLocaleString("en-US") : v.toLocaleString("en-US", { maximumFractionDigits: 2 });
    return String(v);
  }

  function chartHTML(q) {
    const c = q.chart;
    if (!c) return "";
    const foot = c.footnote ? `<p class="foot">${esc(c.footnote)}</p>` : "";
    if (c.type === "bars") {
      const tall = c.horizontal ? Math.max(200, c.labels.length * 34 + 40) : 260;
      return (c.series.length > 1 ? legendHTML(c.series.map((s) => s.name)) : "") +
        `<div class="chart" style="height:${tall}px"><canvas id="chart-${q.id}" role="img" aria-label="${esc(q.title)}"></canvas></div>` + foot;
    }
    if (c.type === "matrix") return matrixHTML(c) + foot;
    if (c.type === "minilists") {
      return `<div class="minis">${c.groups.map((g) => `<div><h4>${esc(g.title)}</h4><ul class="barlist">${barlistHTML(g.items)}</ul></div>`).join("")}</div>`;
    }
    if (c.type === "pairs") {
      const max = c.items[0].value;
      return `<ol class="pairs">${c.items.map((p, i) => `<li><span class="n">${i + 1}</span>` +
        `<span class="who">${esc(p.a)} <small>${esc(p.a_cat)}</small><span class="plus">+</span>${esc(p.b)} <small>${esc(p.b_cat)}</small>` +
        `<span class="track" style="display:block;height:6px;background:var(--grid);border-radius:3px;margin-top:6px"><span style="display:block;height:100%;border-radius:3px;background:${slot(0)};width:${(p.value / max) * 100}%"></span></span></span>` +
        `<span class="val">${fmt.int(p.value)}<small>orders</small></span></li>`).join("")}</ol>`;
    }
    if (c.type === "ranking") {
      return `<div class="chips" role="group" aria-label="Month">${c.months.map((m, i) => `<button type="button" class="chip" data-month="${m}" aria-pressed="${i === c.months.length - 1}">${m}</button>`).join("")}</div>` +
        `<div class="rank-cols" id="rank-${q.id}"></div>`;
    }
    return "";
  }

  function renderRanking(q, month) {
    const c = q.chart;
    const max = Math.max(...c.groups.flatMap((g) => c.data[month][g].map((x) => x.value)));
    $(`rank-${q.id}`).innerHTML = c.groups.map((g, i) => `<div><h4><i style="background:${slot(i)}"></i>${g}s, ${month} 2020</h4>` +
      `<ul class="barlist">${barlistHTML(c.data[month][g].map((x) => ({ ...x, color: slot(i) })), "money", max)}</ul></div>`).join("");
  }

  function cardHTML(q) {
    const tags = q.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join("");
    return `<article class="card qcard${WIDE.has(q.id) ? " wide" : ""}" id="${q.id}" tabindex="-1">
      <div class="qmeta"><span class="qid">${q.id.toUpperCase()}</span>${tags}<span class="perf">${fmt.int(q.row_count)} rows · ${q.ms} ms</span></div>
      <h3>${esc(q.title)}</h3>
      <p class="question">${esc(q.question)}</p>
      <p class="answer"><span>Answer</span>${esc(q.headline)}</p>
      ${chartHTML(q)}
      <div class="qactions">
        <button type="button" class="btn" data-toggle="sql-${q.id}" aria-expanded="false" aria-controls="sql-${q.id}">${icon("code")}SQL</button>
        <button type="button" class="btn" data-toggle="rows-${q.id}" aria-expanded="false" aria-controls="rows-${q.id}">${icon("rows")}Result rows</button>
        <a class="btn" href="/warehouse/q/${q.id}.csv" download>${icon("csv")}CSV (${fmt.int(q.row_count)} rows)</a>
      </div>
      <div class="panel" id="sql-${q.id}" hidden>
        ${q.note ? `<p class="port-note"><b>Ported from MySQL:</b> ${esc(q.note)}</p>` : ""}
        ${q.setup ? `<pre class="sql"><code>${highlight(q.setup)};</code></pre>` : ""}
        <pre class="sql"><code>${highlight(q.sql)};</code></pre>
      </div>
      <div class="panel" id="rows-${q.id}" hidden>
        <div class="table-scroll"><table class="data"><thead><tr>${q.columns.map((c) => `<th class="${isNumCol(c) ? "num" : ""}">${esc(c)}</th>`).join("")}</tr></thead>
        <tbody>${q.preview.map((r) => `<tr>${r.map((v, i) => `<td class="${isNumCol(q.columns[i]) && typeof v === "number" ? "num" : ""}">${esc(cellText(v, q.columns[i]))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
        <p class="foot">Showing ${q.preview.length} of ${fmt.int(q.row_count)} rows. Download the CSV for all of them.</p>
      </div>
    </article>`;
  }

  const VIEWS = ["sales", "products", "customers", "stores"];
  const VIEW_NAME = { sales: "Sales", products: "Products", customers: "Customers", stores: "Stores & suppliers" };
  const drawn = new Set();

  function renderView(view) {
    if (drawn.has(view)) return;
    drawn.add(view);
    const qs = D.queries.filter((q) => q.view === view);
    $(`view-${view}`).innerHTML = `<div class="qgrid">${qs.map(cardHTML).join("")}</div>`;
    drawViewCharts(view);
  }

  function drawViewCharts(view) {
    D.queries.filter((q) => q.view === view).forEach((q) => {
      if (!q.chart) return;
      if (q.chart.type === "bars") barChart($(`chart-${q.id}`), q.chart);
      if (q.chart.type === "ranking") {
        renderRanking(q, q.chart.months[q.chart.months.length - 1]);
        $(q.id).querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
          $(q.id).querySelectorAll(".chip").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
          renderRanking(q, b.dataset.month);
        }));
      }
    });
  }

  function renderLibrary() {
    $("view-queries").innerHTML = `<div class="qlist">${D.queries.map((q) => `<a class="card qrow" href="#${q.id}">` +
      `<span class="qid">${q.id.toUpperCase()}</span><div><h3>${esc(q.title)}</h3><p>${esc(q.headline)}</p></div>` +
      `<span class="where">${VIEW_NAME[q.view]} →</span></a>`).join("")}</div>`;
  }

  // ---------- routing ----------
  function route() {
    const hash = location.hash.slice(1) || "overview";
    const q = D.queries.find((x) => x.id === hash);
    const view = q ? q.view : (["overview", "queries", ...VIEWS].includes(hash) ? hash : "overview");
    document.querySelectorAll(".view").forEach((s) => { s.hidden = s.id !== `view-${view}`; });
    document.querySelectorAll(".nav a").forEach((a) => { if (a.dataset.view === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
    const sec = $(`view-${view}`);
    $("view-title").innerHTML = sec.dataset.title;
    $("view-sub").textContent = sec.dataset.sub;
    document.title = view === "overview" ? "Walmart Sales Data Warehouse" : `${sec.dataset.title.replace("&amp;", "&")} · Walmart Sales Data Warehouse`;
    if (VIEWS.includes(view)) renderView(view);
    if (q) {
      const card = $(q.id);
      requestAnimationFrame(() => {
        card.scrollIntoView({ block: "start" });
        card.focus({ preventScroll: true });
        card.classList.remove("flash"); void card.offsetWidth; card.classList.add("flash");
      });
    } else {
      window.scrollTo(0, 0);
    }
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-toggle]");
    if (!btn) return;
    const panel = $(btn.dataset.toggle);
    panel.hidden = !panel.hidden;
    btn.setAttribute("aria-expanded", String(!panel.hidden));
  });

  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    renderOverview();
    const keep = [...drawn]; drawn.clear();
    keep.forEach(renderView);
  });

  renderOverview();
  renderLibrary();
  window.addEventListener("hashchange", route);
  route();
})();
