/* Painel Merc — gráficos e tabelas.
   Lê projections.json (gerado por pipeline/projetar.py) e desenha tudo em SVG e
   HTML, sem bibliotecas. Convenção: P10, P5 e P1 estão sempre na direção ruim
   (USD/BRL mais alto; BTC mais baixo). P90f é o lado favorável, só referência. */
(function () {
  "use strict";

  var P = null;
  var estado = { ativoHeat: "usdbrl", dist: "base", dia: null };
  var NOMES = { usdbrl: "USD/BRL", btcusd: "BTC/USD", btcbrl: "BTC/BRL" };
  var DESC = { usdbrl: "reais por dólar (PTAX)", btcusd: "bitcoin em dólar", btcbrl: "derivado: BTC/USD × USD/BRL" };
  var QS = ["P1", "P5", "P10", "P50"];
  var HZ = ["30", "90", "180", "365"];

  /* ---------- tema ---------- */
  var raiz = document.documentElement;
  try { var t = localStorage.getItem("merc-tema"); if (t) raiz.setAttribute("data-theme", t); } catch (e) {}
  var btnTema = document.getElementById("tema");
  if (btnTema) btnTema.addEventListener("click", function () {
    var atual = raiz.getAttribute("data-theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var novo = atual === "dark" ? "light" : "dark";
    raiz.setAttribute("data-theme", novo);
    try { localStorage.setItem("merc-tema", novo); } catch (e) {}
  });

  /* ---------- formatação ---------- */
  var nf = function (d) { return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }); };
  var F0 = nf(0), F1 = nf(1), F2 = nf(2);
  function moeda(a, v) {
    if (a === "usdbrl") return "R$ " + F2.format(v);
    var pre = a === "btcusd" ? "US$ " : "R$ ";
    if (v >= 1e6) return pre + F2.format(v / 1e6) + " mi";
    if (v >= 1e5) return pre + F0.format(v / 1e3) + " mil";
    if (v >= 1e4) return pre + F1.format(v / 1e3) + " mil";
    return pre + F0.format(v);
  }
  function curto(a, v) {
    if (a === "usdbrl") return F2.format(v);
    if (v >= 1e6) return F1.format(v / 1e6) + " mi";
    if (v >= 1e4) return F0.format(v / 1e3) + " mil";
    return F1.format(v / 1e3) + " mil";
  }
  function pct(v, d) { var s = (v > 0 ? "+" : v < 0 ? "−" : "") + nf(d === undefined ? 1 : d).format(Math.abs(v * 100)) + "%"; return s; }
  function bi(musd) { return (musd < 0 ? "−" : "+") + "US$ " + F1.format(Math.abs(musd) / 1000) + " bi"; }
  function pp(v) { return (v > 0 ? "+" : v < 0 ? "−" : "") + F1.format(Math.abs(v)) + " p.p."; }
  function data(s) { if (!s) return "—"; var p = s.slice(0, 10).split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function el(id) { return document.getElementById(id); }

  function dist() {
    if (estado.dist === "base") return { nome: "Distribuição-base", a: P.base };
    var c = P.cenarios.filter(function (x) { return x.id === estado.dist; })[0];
    return { nome: "Estresse · " + c.nome + " (" + c.periodo + ")", a: c.ativos, c: c };
  }

  /* ---------- 1. abertura ---------- */
  function hero() {
    el("hero-data").textContent = "Dados até " + data(P.data_base) + " · " + F0.format(P.modelo.n_trajetorias) + " trajetórias simuladas";
    var b = P.base;
    el("h-hero").innerHTML = "Em 1 de cada 100 trajetórias, em 365 dias, o dólar passa de <em>" + moeda("usdbrl", b.usdbrl.horizontes["365"].P1.nivel) +
      "</em> e o bitcoin cai abaixo de <em>" + moeda("btcusd", b.btcusd.horizontes["365"].P1.nivel) + "</em><span class=\"dot\">.</span>";
    var html = "";
    ["usdbrl", "btcusd", "btcbrl"].forEach(function (a) {
      var h = b[a].horizontes["365"];
      var pior = P.cenarios.slice().sort(function (x, y) {
        var vx = x.ativos[a].horizontes["365"].P50.nivel, vy = y.ativos[a].horizontes["365"].P50.nivel;
        return a === "usdbrl" ? vy - vx : vx - vy;
      })[0];
      var pv = pior.ativos[a].horizontes["365"].P50;
      html += '<article class="tile glass">' +
        '<div class="tile__ativo"><span class="label">' + NOMES[a] + '</span><span class="eyebrow">P1 · 365 dias</span></div>' +
        '<div class="tile__p1">' + moeda(a, h.P1.nivel) + '</div>' +
        '<div class="tile__var">' + pct(h.P1.var_pct) + ' sobre hoje (' + moeda(a, P.spot[a]) + ')</div>' +
        '<dl class="tile__escada">' +
        '<div><dt>P5</dt><dd>' + moeda(a, h.P5.nivel) + '</dd></div>' +
        '<div><dt>P10</dt><dd>' + moeda(a, h.P10.nivel) + '</dd></div>' +
        '<div><dt>P50</dt><dd>' + moeda(a, h.P50.nivel) + '</dd></div></dl>' +
        '<p class="tile__est">Pior estresse: ' + esc(pior.nome) + ' (' + esc(pior.periodo) + '), mediana de ' + moeda(a, pv.nivel) + ' (' + pct(pv.var_pct) + ').</p>' +
        '</article>';
    });
    el("tiles").innerHTML = html;
    el("hero-nota").textContent = "Pior, aqui, é o dólar mais caro e o bitcoin mais barato. P1, P5 e P10 são os pontos que só 1%, 5% e 10% das trajetórias ultrapassam nessa direção; P50 é a mediana. BTC/BRL é sempre calculado de BTC/USD × USD/BRL na mesma trajetória.";
    // selos de estado
    var v = veredito();
    var alertas = P.gatilhos.filter(function (g) { return g.status === "alerta"; }).map(function (g) { return g.nome; });
    el("selo").innerHTML =
      '<a class="chip glass" href="#h-bt" data-s="' + (v.dentro === v.total && !v.sig ? "ok" : "fora") + '"><i aria-hidden="true"></i>Backtest: ' + v.dentro + ' de ' + v.total + ' células na meta de 8% a 12%; ' + (v.sig ? v.sig + ' desvios significativos' : 'nenhum desvio significativo') + '. Calibração parcial.</a>' +
      '<a class="chip glass" href="#h-gat" data-s="' + (alertas.length ? "alerta" : "normal") + '"><i aria-hidden="true"></i>' +
      (alertas.length ? "Gatilhos em alerta: " + esc(alertas.join(", ")) : "Nenhum gatilho em alerta") + '</a>';
  }

  /* ---------- 2. leques, um por ativo ---------- */
  var ATIVOS = ["usdbrl", "btcusd", "btcbrl"];
  var marcadores = {};

  function opcoes() {
    var s = el("cenario-sel");
    var h = '<option value="base">Distribuição-base</option>';
    P.cenarios.forEach(function (c) { h += '<option value="' + c.id + '">Estresse · ' + esc(c.nome) + ' (' + esc(c.periodo) + ')</option>'; });
    s.innerHTML = h;
    s.addEventListener("change", function () { estado.dist = s.value; leques(); });
  }

  function niceLog(min, max, n) {
    var out = [], l0 = Math.log(min), l1 = Math.log(max);
    for (var i = 0; i < n; i++) {
      var v = Math.exp(l0 + (l1 - l0) * (i + .5) / n);
      var m = Math.pow(10, Math.floor(Math.log10(v)) - 1);
      out.push(Math.round(v / m) * m);
    }
    return out.filter(function (v, i, a) { return a.indexOf(v) === i; });
  }

  function leques() {
    var D = dist();
    var html = "";
    ATIVOS.forEach(function (a) {
      html += '<figure class="fan" id="fan-' + a + '">' +
        '<div class="fan__topo"><h3>' + NOMES[a] + '</h3><p class="note">' + DESC[a] + ' · hoje ' + moeda(a, P.spot[a]) + '</p></div>' +
        '<div class="leitura" id="leitura-' + a + '" aria-live="polite"></div>' +
        '<div class="chart__svg" id="svg-' + a + '"></div>' +
        '<div class="table-wrap"><table class="quantis" id="tab-' + a + '"></table></div>' +
        '</figure>';
    });
    el("leques").innerHTML = html;
    ATIVOS.forEach(function (a) { desenharLeque(a, D); tabela(a, D); });
    marcarTodos(estado.dia || 252);
    el("legenda").innerHTML =
      '<span><i style="background:var(--primary);height:2px"></i>Histórico e mediana (P50)</span>' +
      '<span><i style="background:var(--band-1)"></i>P50 a P10</span>' +
      '<span><i style="background:var(--band-2)"></i>P10 a P5</span>' +
      '<span><i style="background:var(--band-3)"></i>P5 a P1</span>' +
      '<span><i style="background:var(--red);height:3px"></i>P1, cauda ruim</span>' +
      '<span><i style="border-top:1.5px dashed var(--cold);height:0"></i>P90, lado favorável</span>' +
      '<span>Escala logarítmica · eixo em dias úteis · as três curvas usam as mesmas trajetórias</span>';
    var nota = "Para USD/BRL, P10, P5 e P1 são os percentis 90, 95 e 99 da cotação (dólar mais caro); para BTC/USD e BTC/BRL, os percentis 10, 5 e 1 (preço mais baixo).";
    if (P.modelo.recal) nota += " Os quantis da cauda já incluem a recalibração estimada no histórico (ver premissas).";
    if (D.c) nota += " Cenário de estresse: " + D.c.premissas.deriva + ".";
    el("nota-quantis").textContent = nota;
  }

  function desenharLeque(a, D) {
    var L = D.a[a].leque;
    var box = el("svg-" + a), W = Math.max(300, Math.round(box.clientWidth || 640));
    var estreito = W < 560;
    var H = estreito ? 250 : 300;
    var m = { l: estreito ? 46 : 58, r: estreito ? 64 : 88, t: 12, b: 28 };
    var hist = P.historico.slice(-(estreito ? 90 : 130));
    var nh = hist.length, x0 = -(nh - 1), x1 = 252;
    var vals = [];
    hist.forEach(function (h) { vals.push(h[a]); });
    L.forEach(function (p) { vals.push(p.P1, p.P90f, p.P50); });
    var ymin = Math.min.apply(null, vals) * .97, ymax = Math.max.apply(null, vals) * 1.03;
    var X = function (d) { return m.l + (d - x0) / (x1 - x0) * (W - m.l - m.r); };
    var Y = function (v) { return m.t + (Math.log(ymax) - Math.log(v)) / (Math.log(ymax) - Math.log(ymin)) * (H - m.t - m.b); };
    var pth = function (pts) { return pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(""); };
    var faixa = function (k1, k2) {
      var up = L.map(function (p) { return [X(p.d), Y(p[k1])]; });
      var dn = L.slice().reverse().map(function (p) { return [X(p.d), Y(p[k2])]; });
      return pth(up.concat(dn)) + "Z";
    };
    var fim = L[L.length - 1];
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" tabindex="0" aria-label="Cone de risco de ' + NOMES[a] + ', ' + esc(D.nome) +
      '. Em 365 dias: P1 ' + moeda(a, fim.P1) + ', P5 ' + moeda(a, fim.P5) + ', P10 ' + moeda(a, fim.P10) + ', mediana ' + moeda(a, fim.P50) +
      '. Use as setas para percorrer os dias; a tabela abaixo traz todos os valores.">';
    niceLog(ymin, ymax, estreito ? 4 : 5).forEach(function (v) {
      var y = Y(v);
      s += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '" style="stroke:var(--hairline)" stroke-width="1"/>';
      s += '<text x="' + (m.l - 6) + '" y="' + (y + 4) + '" text-anchor="end">' + curto(a, v) + '</text>';
    });
    [["hoje", 0]].concat(HZ.map(function (h) { return [h + "d", P.passos[h]]; })).forEach(function (g) {
      var x = X(g[1]);
      s += '<line x1="' + x + '" x2="' + x + '" y1="' + m.t + '" y2="' + (H - m.b) + '" style="stroke:var(--hairline)" stroke-dasharray="' + (g[1] ? "3 4" : "0") + '"/>';
      if (!(estreito && g[0] === "30d")) s += '<text x="' + x + '" y="' + (H - 9) + '" text-anchor="middle">' + g[0] + '</text>';
    });
    s += '<path d="' + faixa("P50", "P10") + '" style="fill:var(--band-1)"/>';
    s += '<path d="' + faixa("P10", "P5") + '" style="fill:var(--band-2)"/>';
    s += '<path d="' + faixa("P5", "P1") + '" style="fill:var(--band-3)"/>';
    s += '<path d="' + pth(L.map(function (p) { return [X(p.d), Y(p.P90f)]; })) + '" fill="none" style="stroke:var(--cold)" stroke-width="1.2" stroke-dasharray="4 4"/>';
    s += '<path d="' + pth(L.map(function (p) { return [X(p.d), Y(p.P50)]; })) + '" fill="none" style="stroke:var(--primary)" stroke-width="1.6"/>';
    s += '<path d="' + pth(L.map(function (p) { return [X(p.d), Y(p.P1)]; })) + '" fill="none" style="stroke:var(--red)" stroke-width="2.6"/>';
    s += '<path d="' + pth(hist.map(function (h, i) { return [X(i - (nh - 1)), Y(h[a])]; })) + '" fill="none" style="stroke:var(--primary)" stroke-width="1.4"/>';
    s += '<circle cx="' + X(0) + '" cy="' + Y(P.spot[a]) + '" r="3.5" style="fill:var(--primary)"/>';
    var rot = [["P90", fim.P90f, ""], ["P50", fim.P50, "rot-p50"], ["P10", fim.P10, ""], ["P5", fim.P5, ""], ["P1", fim.P1, "rot-p1"]]
      .map(function (r) { return { k: r[0], v: r[1], c: r[2], y: Y(r[1]) }; })
      .sort(function (p, q) { return p.y - q.y; });
    for (var i = 1; i < rot.length; i++) if (rot[i].y - rot[i - 1].y < 13) rot[i].y = rot[i - 1].y + 13;
    var exced = rot[rot.length - 1].y - (H - m.b + 4);
    if (exced > 0) rot.forEach(function (r) { r.y -= exced; });
    if (rot[0].y < m.t) { var d0 = m.t - rot[0].y; rot.forEach(function (r) { r.y += d0; }); }
    rot.forEach(function (r) {
      s += '<text x="' + (W - m.r + 6) + '" y="' + (r.y + 4) + '" class="' + r.c + '">' + r.k + " " + curto(a, r.v) + '</text>';
    });
    s += '<g class="cursor" style="display:none"><line y1="' + m.t + '" y2="' + (H - m.b) + '" style="stroke:var(--secondary)" stroke-width="1"/>' +
      '<circle r="3.5" class="c50" style="fill:var(--primary)"/><circle r="4.5" class="c1" style="fill:var(--red)"/></g>';
    s += '<rect x="' + X(0) + '" y="' + m.t + '" width="' + (X(252) - X(0)) + '" height="' + (H - m.t - m.b) + '" fill="transparent"/>';
    s += "</svg>";
    box.innerHTML = s;
    var svg = box.querySelector("svg"), cur = svg.querySelector(".cursor");
    marcadores[a] = function (d) {
      var p = L.reduce(function (b, q) { return Math.abs(q.d - d) < Math.abs(b.d - d) ? q : b; }, L[1]);
      if (p.d < 1) p = L[1];
      cur.style.display = "";
      var ln = cur.querySelector("line");
      ln.setAttribute("x1", X(p.d)); ln.setAttribute("x2", X(p.d));
      var c5 = cur.querySelector(".c50"), c1 = cur.querySelector(".c1");
      c5.setAttribute("cx", X(p.d)); c5.setAttribute("cy", Y(p.P50));
      c1.setAttribute("cx", X(p.d)); c1.setAttribute("cy", Y(p.P1));
      leitura(a, p);
      return p.d;
    };
    function mover(ev) {
      var r = svg.getBoundingClientRect();
      var px = (ev.clientX - r.left) * (W / r.width);
      var d = x0 + (px - m.l) / (W - m.l - m.r) * (x1 - x0);
      if (d >= 0) marcarTodos(Math.min(252, d));
    }
    svg.addEventListener("pointermove", mover);
    svg.addEventListener("pointerdown", mover);
    svg.addEventListener("keydown", function (ev) {
      var d = estado.dia || 252;
      if (ev.key === "ArrowLeft") { marcarTodos(Math.max(1, d - 7)); ev.preventDefault(); }
      if (ev.key === "ArrowRight") { marcarTodos(Math.min(252, d + 7)); ev.preventDefault(); }
      if (ev.key === "Home") { marcarTodos(1); ev.preventDefault(); }
      if (ev.key === "End") { marcarTodos(252); ev.preventDefault(); }
    });
  }

  function marcarTodos(d) {
    var dd = d;
    ATIVOS.forEach(function (a) { if (marcadores[a]) dd = marcadores[a](d); });
    estado.dia = dd;
  }

  function leitura(a, p) {
    var quando = P.datas_passos[p.d - 1];
    var dc = Math.round(p.d * 365 / 252);
    el("leitura-" + a).innerHTML =
      '<span class="leitura__quando">' + data(quando) + ' · dia útil ' + p.d + ' (~' + dc + ' dias corridos)</span>' +
      '<span class="p1">P1<b>' + moeda(a, p.P1) + '</b></span>' +
      '<span>P5<b>' + moeda(a, p.P5) + '</b></span>' +
      '<span>P10<b>' + moeda(a, p.P10) + '</b></span>' +
      '<span>P50<b>' + moeda(a, p.P50) + '</b></span>';
  }

  function tabela(a, D) {
    var H = D.a[a].horizontes;
    var linhas = [["P1", "P1", "p1"], ["P5", "P5", ""], ["P10", "P10", ""], ["P50", "P50 · mediana", ""], ["P90f", "P90 · favorável", "fav"]];
    var h = '<caption class="sr-only">' + NOMES[a] + ', ' + esc(D.nome) + ': quantis por horizonte</caption>' +
      '<thead><tr><th scope="col">Quantil</th>' + HZ.map(function (z) { return '<th scope="col">' + z + ' dias</th>'; }).join("") + '</tr></thead><tbody>';
    linhas.forEach(function (l) {
      h += '<tr class="' + l[2] + '"><th scope="row">' + l[1] + '</th>';
      HZ.forEach(function (z) { var r = H[z][l[0]]; h += '<td>' + moeda(a, r.nivel) + '<small>' + pct(r.var_pct) + '</small></td>'; });
      h += '</tr>';
    });
    var an = P.ancoras_historicas[a];
    h += '<tr class="ancora"><th scope="row">Pior histórico<small>desde ' + data(an["30"].desde).slice(6) + '</small></th>';
    HZ.forEach(function (z) { h += '<td>' + pct(an[z].var_pct, 0) + '<small>' + data(an[z].inicio).slice(3) + '</small></td>'; });
    el("tab-" + a).innerHTML = h + '</tr></tbody>';
  }

  /* ---------- 3. mapa de calor ---------- */
  function heat() {
    var a = estado.ativoHeat;
    var linhas = [{ nome: "Distribuição-base", sub: "GARCH-t + camada de crise", d: P.base[a].drawdown }]
      .concat(P.cenarios.map(function (c) { return { nome: c.nome + " (" + c.periodo + ")", sub: c.tipo, d: c.ativos[a].drawdown }; }));
    var max = 0;
    linhas.forEach(function (l) { HZ.forEach(function (h) { max = Math.max(max, l.d[h].P5); }); });
    var lbl = a === "usdbrl" ? "Perda máxima do real contra o dólar" : "Queda máxima de " + NOMES[a];
    var h = '<caption>' + lbl + ' desde o pico, até cada horizonte. Número grande: P5. Número pequeno: mediana.</caption>' +
      '<thead><tr><th scope="col">Distribuição</th>' + HZ.map(function (z) { return '<th scope="col">' + z + ' dias</th>'; }).join("") + '</tr></thead><tbody>';
    linhas.forEach(function (l) {
      h += '<tr><th scope="row">' + esc(l.nome) + '<small>' + esc(l.sub) + '</small></th>';
      HZ.forEach(function (z) {
        var v = l.d[z].P5, k = Math.round(8 + 64 * v / max);
        h += '<td style="background:color-mix(in srgb, var(--red) ' + k + '%, transparent)"><b>' + pct(-v, 0) + '</b><small>' + pct(-l.d[z].P50, 0) + '</small></td>';
      });
      h += "</tr>";
    });
    el("heat").innerHTML = h + "</tbody>";
    el("escala").innerHTML = '<span>0%</span><span class="escala__barra" style="background:linear-gradient(90deg, color-mix(in srgb, var(--red) 8%, transparent), color-mix(in srgb, var(--red) 72%, transparent))"></span><span>' + pct(-max, 0) + '</span>';
  }

  /* ---------- 4. cenários ---------- */
  function cenarios() {
    var g = {}; P.gatilhos.forEach(function (x) { g[x.id] = x.valores; });
    var hoje = {
      vix: g.riskoff.vix, dxy: g.dxy.var_3m, selic: g.selic_real.selic_real_ex_ante,
      dbgg: g.fiscal.dbgg_var_12m_pp, fluxo: g.fluxo.soma_63d_musd
    };
    var html = "";
    P.cenarios.forEach(function (c, i) {
      var pr = c.premissas, ge = c.gatilhos_episodio;
      var nums = ["usdbrl", "btcusd", "btcbrl"].map(function (a) {
        var v = c.ativos[a].horizontes["365"].P50;
        return '<div><dt>' + NOMES[a] + '</dt><dd>' + moeda(a, v.nivel) + '<small>' + pct(v.var_pct) + '</small></dd></div>';
      }).join("");
      var linhas = [];
      linhas.push(["Real perder valor", "dólar " + pct(pr.choque_fx_pct) + " em " + pr.dias_ate_pior_fx + " dias úteis", "levaria o dólar a " + moeda("usdbrl", P.spot.usdbrl * (1 + pr.choque_fx_pct))]);
      if (c.tipo === "reconstruído") {
        linhas.push(["Bitcoin cair", pct(pr.choque_btc_pct) + " em " + pr.dias_ate_pior_btc + " dias úteis", "levaria o BTC a " + moeda("btcusd", P.spot.btcusd * (1 + pr.choque_btc_pct))]);
        linhas.push(["Medo global (VIX)", "de " + F1.format(ge.vix_inicio) + " a " + F1.format(ge.vix_pico), "hoje " + F1.format(hoje.vix)]);
        linhas.push(["Dólar global no choque", pct(ge.dxy_var), "hoje " + pct(hoje.dxy) + " em 3 meses"]);
        if (ge.selic_real !== null) linhas.push(["Selic real ex-ante", F1.format(ge.selic_real) + "%", "hoje " + F1.format(hoje.selic) + "%"]);
        linhas.push(["Dívida bruta em 12 meses", pp(ge.dbgg_var_12m_pp), "hoje " + pp(hoje.dbgg)]);
        linhas.push(["Fluxo cambial no choque", bi(ge.fluxo_musd), "hoje " + bi(hoje.fluxo) + " em 63 dias"]);
      } else {
        linhas.push(["Bitcoin", "sem queda própria; contágio só pela correlação", "mediana do BTC/USD estável"]);
        linhas.push(["Dívida bruta", "acima da trajetória do Focus (hipótese)", "Focus: " + F1.format(g.fiscal.focus_dbgg_prox_ano) + "% em " + (Number(P.data_base.slice(0, 4)) + 1)]);
        linhas.push(["Selic real ex-ante", "abaixo de 6% com expectativa desancorando (hipótese)", "hoje " + F1.format(hoje.selic) + "%"]);
        linhas.push(["Fluxo cambial", "saída persistente (hipótese)", "hoje " + bi(hoje.fluxo) + " em 63 dias"]);
      }
      linhas.push(["Correlação diária real × BTC", F2.format(pr.rho_episodio) + " no episódio", "usada " + F2.format(pr.rho_usado) + " (hoje " + F2.format(P.modelo.rho_250d) + ")"]);
      var tab = '<div class="table-wrap"><table class="precisaria"><caption>O que precisaria acontecer</caption><thead><tr><th scope="col">Condição</th><th scope="col">' +
        (c.tipo === "reconstruído" ? "No episódio" : "Premissa") + '</th><th scope="col">Hoje</th></tr></thead><tbody>' +
        linhas.map(function (l) { return '<tr><th scope="row">' + esc(l[0]) + '</th><td data-rot="' + (c.tipo === "reconstruído" ? "No episódio" : "Premissa") + '">' + esc(l[1]) + '</td><td data-rot="Hoje">' + esc(l[2]) + '</td></tr>'; }).join("") + "</tbody></table></div>";
      var real = c.historico_real_pct && c.historico_real_pct["365"];
      var prem = '<li>Início: ' + (c.data_inicio_real ? data(c.data_inicio_real) : "análogos de " + c.analogos.map(data).join(", ")) + '.</li>' +
        '<li>Mediana: ' + esc(pr.deriva) + '.</li>' +
        '<li>Dispersão: volatilidade realizada no episódio, ' + F0.format(pr.vol_anual_fx * 100) + '% a.a. no câmbio e ' + F0.format(pr.vol_anual_btc * 100) + '% a.a. no BTC; inovações t com cópula t de ' + F0.format(pr.nu_copula) + ' graus de liberdade.</li>' +
        '<li>Correlação: a maior entre a do episódio e o percentil 95 histórico da janela de 63 dias (' + F2.format(P.modelo.rho_estresse_p95_63d) + ').</li>' +
        (real ? '<li>O que aconteceu de fato em 365 dias: USD/BRL ' + pct(real.usdbrl) + ', BTC/USD ' + pct(real.btcusd) + '. A recuperação, quando houve, não entra no cenário.</li>' : "");
      html += '<article class="cen glass">' +
        '<div class="cen__topo"><p class="eyebrow">' + (i + 1) + 'º mais severo · ' + esc(c.periodo) + '</p><span class="cen__tipo">' + esc(c.tipo) + '</span></div>' +
        '<h3>' + esc(c.nome) + '</h3><p class="cen__resumo">' + esc(c.resumo) + '</p>' +
        '<dl class="cen__nums" aria-label="Mediana do cenário em 365 dias">' + nums + '</dl>' +
        '<p class="note">Mediana do cenário em 365 dias, aplicada aos preços de hoje.</p>' +
        tab + '<details><summary>Premissas do cenário</summary><ul>' + prem + '</ul></details></article>';
    });
    el("cenarios").innerHTML = html;
  }

  /* ---------- 5. gatilhos ---------- */
  function gatilhos() {
    var nomeS = { alerta: "Alerta", atencao: "Atenção", normal: "Normal", sem_dado: "Sem dado" };
    el("gatilhos").innerHTML = P.gatilhos.map(function (g) {
      var ds = Object.keys(g.datas || {}).map(function (k) { return data(g.datas[k]); });
      return '<li class="gat"><div class="gat__topo"><span class="gat__nome">' + esc(g.nome) + '</span><span class="pill" data-s="' + g.status + '">' + nomeS[g.status] + '</span></div>' +
        '<div><p>' + esc(g.leitura) + '</p><small>' + esc(g.regra) + ' Fonte: ' + esc(g.fonte) + (ds.length ? '. Dado mais recente: ' + ds.join(", ") : "") + '.</small></div></li>';
    }).join("");
  }

  /* ---------- 6. backtest ---------- */
  function veredito() {
    var ag = P.backtest.agregado, dentro = 0, sig = 0, fora = [];
    ag.forEach(function (x) { if (x.p10 >= .08 && x.p10 <= .12) dentro++; else fora.push(x); });
    ["2018", "2021"].forEach(function (c) { P.backtest.por_corte[c].forEach(function (x) { if (!(x.lo <= .1 && .1 <= x.hi)) sig++; }); });
    var semCob = [];
    P.contencao_estresses.forEach(function (c) {
      ATIVOS.forEach(function (a) {
        HZ.forEach(function (z) {
          var x = c.celulas[a][z]; if (!x) return;
          var pit = pitChoque(c.origem, a, z);
          if (!(pit !== undefined && pit >= .05) && !x.contido_por.length) semCob.push(c.choque + ", " + NOMES[a] + " em " + z + " dias");
        });
      });
    });
    return { dentro: dentro, total: ag.length, sig: sig, fora: fora, semCob: semCob };
  }
  function pitChoque(origem, a, z) {
    var c = P.backtest.choques.filter(function (x) { return x.origem === origem; })[0];
    return c && c.pit[a] ? c.pit[a][z] : undefined;
  }

  function celBt(x) {
    var cls = x.p10 > .12 ? "fora-alto" : x.p10 < .08 ? "fora-baixo" : "dentro";
    var sig = !(x.lo <= .1 && .1 <= x.hi);
    return '<td class="' + cls + '">' + F1.format(x.p10 * 100) + '%' + (sig ? ' <abbr title="desvio estatisticamente significativo">!</abbr>' : '') +
      '<small>IC95 ' + F0.format(x.lo * 100) + '–' + F0.format(x.hi * 100) + '% · n≈' + x.n_eff + '</small></td>';
  }

  function tabelaBt(cel, titulo) {
    var h = '<caption>' + titulo + '</caption><thead><tr><th scope="col">Ativo</th>' + HZ.map(function (z) { return '<th scope="col">' + z + ' dias</th>'; }).join("") + '</tr></thead><tbody>';
    ATIVOS.forEach(function (a) {
      h += '<tr><th scope="row">' + NOMES[a] + '</th>';
      HZ.forEach(function (z) {
        var x = cel.filter(function (q) { return q.ativo === a && String(q.h) === z; })[0];
        h += x ? celBt(x) : "<td>—</td>";
      });
      h += "</tr>";
    });
    return h + "</tbody>";
  }

  function backtest() {
    var bt = P.backtest, v = veredito();
    el("bt-sub").textContent = "Parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), congelados depois disso. A cada 5 dias úteis o modelo projetou de novo e comparamos com o que aconteceu. Meta do projeto: o realizado fica pior que o P10 entre 8% e 12% das vezes.";
    el("bt-veredito").innerHTML =
      '<li data-s="' + (v.dentro === v.total ? "ok" : "fora") + '"><b>' + v.dentro + ' de ' + v.total + '</b> células na faixa de 8% a 12%, com os dois cortes juntos. <span>Meta principal: não atendida por completo.</span></li>' +
      '<li data-s="' + (v.sig ? "fora" : "ok") + '"><b>' + v.sig + ' de 24</b> células com desvio estatisticamente significativo, olhando cada corte. <span>' + (v.sig ? "" : "Nenhuma frequência é distinguível de 10% com os dados disponíveis.") + '</span></li>' +
      '<li data-s="' + (v.semCob.length ? "fora" : "ok") + '"><b>' + (v.semCob.length ? v.semCob.length + (v.semCob.length > 1 ? " choques" : " choque") + " sem cobertura" : "Todos os choques cobertos") + '</b> pelo P5 da base ou de um estresse independente. <span>' + esc(v.semCob.join("; ")) + '</span></li>';
    el("bt").innerHTML = tabelaBt(bt.agregado, "Os dois cortes juntos, 2018 a 2026: frequência em que o realizado ficou pior que o P10. Verde: na faixa. Vermelho: o modelo subestimou o risco. Âmbar: foi pessimista demais. “!” marca desvio estatisticamente significativo.");
    el("bt-cortes").innerHTML =
      '<div class="table-wrap"><table class="bt">' + tabelaBt(bt.por_corte["2018"], "Corte 2018: projeções de 2018 a 2020") + '</table></div>' +
      '<div class="table-wrap"><table class="bt">' + tabelaBt(bt.por_corte["2021"], "Corte 2021: projeções de 2021 a 2026") + '</table></div>';
    var periodoC = {}; P.cenarios.forEach(function (c) { periodoC[c.id] = c.periodo; });
    var hc = '<caption>Os choques reais cabem no P5? Variação realizada a partir da véspera de cada choque. Verde: dentro do P5 da distribuição-base projetada naquela data. Âmbar: fora da base, mas dentro do P5 de um estresse construído sem aquele episódio. Vermelho: fora de tudo.</caption>' +
      '<thead><tr><th scope="col">Choque e ativo</th>' + HZ.map(function (z) { return '<th scope="col">' + z + ' dias</th>'; }).join("") + '</tr></thead><tbody>';
    P.contencao_estresses.forEach(function (c) {
      hc += '<tr class="grupo"><th scope="rowgroup" colspan="5">' + esc(c.choque) + ' · véspera em ' + data(c.origem) + '</th></tr>';
      ATIVOS.forEach(function (a) {
        hc += '<tr><th scope="row">' + NOMES[a] + '</th>';
        HZ.forEach(function (z) {
          var x = c.celulas[a][z];
          if (!x) { hc += "<td>—</td>"; return; }
          var pit = pitChoque(c.origem, a, z), txt, cls;
          var base = pit !== undefined ? "base: percentil " + F1.format(pit * 100) : "";
          if (pit !== undefined && pit >= .05) { txt = base; cls = "dentro"; }
          else if (x.contido_por.length) { txt = base + "<br>coberto pelo estresse " + x.contido_por.map(function (i) { return esc(periodoC[i]); }).join(", "); cls = "parcial"; }
          else { txt = base + "<br>fora de todos os estresses"; cls = "fora-alto"; }
          hc += '<td class="' + cls + '">' + pct(x.real_pct, 0) + '<small>' + txt + '</small></td>';
        });
        hc += "</tr>";
      });
    });
    el("bt-choques").innerHTML = hc + "</tbody>";
    var fora = v.fora.map(function (x) { return NOMES[x.ativo] + " em " + x.h + " dias (" + F1.format(x.p10 * 100) + "%)"; });
    el("bt-nota").textContent = "Leitura honesta: " + (fora.length ? "ficam fora da faixa " + fora.join(", ") + ". Em todas, o intervalo de confiança contém 10%: com origens sobrepostas, o número de observações independentes (n≈) é pequeno, e a faixa de 8% a 12% é mais estreita que o ruído do teste nos horizontes longos. " : "") +
      "O corte 2018 cobre a alta persistente do dólar de 2018 a 2020, que um modelo sem aposta de tendência subestima; o corte 2021 cobre um câmbio que oscilou sem tendência forte, em que o mesmo modelo parece pessimista. Os choques que nem a base nem os estresses contêm ficam marcados acima, sem ajuste para escondê-los.";
  }

  /* ---------- 7. método e fontes ---------- */
  function metodo() {
    var mo = P.modelo, fx = mo.fx, bc = mo.btc;
    var itens = [
      "<b>Monte Carlo com " + F0.format(mo.n_trajetorias) + " trajetórias</b> de 252 dias úteis (365 corridos). Horizontes de 30, 90, 180 e 365 dias equivalem a 21, 63, 126 e 252 dias úteis.",
      "<b>Volatilidade GJR-GARCH(1,1) com inovações t de Student</b>, estimada por máxima verossimilhança. Câmbio: amostra desde " + data(mo.amostra_fx[0]) + " (início do câmbio flutuante), ν = " + F1.format(fx.nu) + ", persistência " + F2.format(fx.persistencia) + " (meia-vida de " + F0.format(fx.meia_vida_dias) + " dias). BTC: desde " + data(mo.amostra_btc[0]) + ", ν = " + F1.format(bc.nu) + ", persistência " + F2.format(bc.persistencia) + ".",
      "<b>Deriva zero</b>: a mediana não aposta em tendência. O pessimismo vem da cauda, da assimetria do GARCH (choques ruins elevam mais a volatilidade) e dos cenários.",
      "<b>Camada de crise</b>: episódios históricos de 21 dias abaixo do 2,5% pior, além do que o GARCH-t já gera. Câmbio: " + F2.format(mo.crise_fx.taxa_anual) + " crise extra por ano, choque mediano de " + pct(Math.exp(-mo.crise_fx.severidade) - 1, 0) + " no dólar, com " + F0.format(mo.crise_fx.frac_devolvida * 100) + "% devolvidos em 126 dias. BTC: " + F2.format(mo.crise_btc.taxa_anual) + " por ano, " + pct(Math.exp(mo.crise_btc.severidade) - 1, 0) + ", " + F0.format(mo.crise_btc.frac_devolvida * 100) + "% devolvidos.",
      (mo.recal ? "<b>Recalibração da cauda ruim</b>, estimada no histórico: quando o modelo, olhando para trás, deixou o realizado passar do P10 em mais de 10% das vezes, a cauda é alargada na mesma proporção (fator k, entre 1 e 2). Câmbio: k = " + HZ.map(function (z) { return F2.format(mo.recal.usdbrl[z].k) + " (" + z + "d)"; }).join(", ") + ", porque o real cai mais depressa do que sobe. BTC: k = " + F2.format(mo.recal.btcusd["30"].k) + " em todos os horizontes; o histórico não pede correção. Com k = 1,4, o P10 exibido é o quantil 7,1% do modelo." : ""),
      "<b>Correlação</b> entre os choques do real e do BTC por cópula t: " + F2.format(mo.rho_250d) + " na janela de 250 dias. Nos estresses, sobe para pelo menos " + F2.format(mo.rho_estresse_p95_63d) + " (percentil 95 da janela de 63 dias) com cópula de " + F0.format(mo.nu_copula_estresse) + " graus de liberdade, que junta as caudas.",
      "<b>BTC/BRL nunca é projetado sozinho</b>: em cada trajetória, BTC/BRL = BTC/USD × USD/BRL.",
      "<b>Sem previsão pontual</b>: toda saída é distribuição (P50, P10, P5, P1), e o P90 aparece só como referência do lado favorável.",
      "<b>Probabilidade de risk-off conjunto</b> na base: real perde mais de 10% e BTC cai mais de 30% em 365 dias em " + pct(mo.prob_riskoff_conjunto_365d).replace("+", "") + " das trajetórias."
    ];
    el("premissas").innerHTML = itens.filter(Boolean).map(function (t) { return "<li>" + t + "</li>"; }).join("");
    el("fontes").innerHTML = '<thead><tr><th scope="col">Série</th><th scope="col">Fonte</th><th scope="col">Último dado</th><th scope="col">Coletado em</th></tr></thead><tbody>' +
      P.fontes.map(function (f) {
        return '<tr><td>' + esc(f.serie) + '</td><td><a href="' + esc(f.url) + '" rel="noopener">' + esc(f.fonte) + '</a></td><td>' + (f.ultimo_dado ? data(String(f.ultimo_dado)) : "—") + '</td><td>' + esc(f.coletado_em.replace("T", " ").replace("+00:00", " UTC")) + '</td></tr>';
      }).join("") + "</tbody>";
    el("rodape-data").textContent = "Gerado em " + P.gerado_em.replace("T", " ").replace("+00:00", " UTC") + " · dados até " + data(P.data_base);
  }

  /* ---------- seletor de ativo compartilhado ---------- */
  function ligarAtivo() {
    var bts = document.querySelectorAll('[data-grupo="ativo-heat"] .seg__btn');
    bts.forEach(function (b) {
      b.addEventListener("click", function () {
        estado.ativoHeat = b.getAttribute("data-ativo");
        bts.forEach(function (o) { o.setAttribute("aria-pressed", String(o.getAttribute("data-ativo") === estado.ativoHeat)); });
        heat();
      });
    });
  }

  function iniciar(dados) {
    P = dados;
    hero(); opcoes(); ligarAtivo(); leques(); heat(); cenarios(); gatilhos(); backtest(); metodo();
    var ultimaL = el("leques").clientWidth;
    window.addEventListener("resize", function () {
      var w = el("leques").clientWidth;
      if (Math.abs(w - ultimaL) > 24) { ultimaL = w; leques(); }
    });
  }

  fetch("projections.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(iniciar)
    .catch(function (e) {
      el("hero-data").textContent = "Não foi possível carregar projections.json (" + e.message + "). Abra o painel por um servidor web, não pelo arquivo local.";
    });
})();
