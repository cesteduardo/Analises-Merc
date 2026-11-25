/* Painel Merc — gráficos e tabelas.
   Lê projections.json (gerado por pipeline/projetar.py) e desenha tudo em SVG e
   HTML, sem bibliotecas. Convenção: P10, P5 e P1 estão sempre na direção ruim
   (USD/BRL mais alto; BTC mais baixo). P90 é o lado favorável, só referência.
   Um único seletor de ativo comanda as seções 2 a 4. */
(function () {
  "use strict";

  var P = null;
  var estado = { ativo: "usdbrl", dist: "base", dia: null };
  var ATIVOS = ["usdbrl", "btcusd", "btcbrl"];
  var NOMES = { usdbrl: "USD/BRL", btcusd: "BTC/USD", btcbrl: "BTC/BRL" };
  var DESC = { usdbrl: "reais por dólar (PTAX)", btcusd: "bitcoin em dólar", btcbrl: "bitcoin em reais, BTC/USD × USD/BRL" };
  var PIOR = { usdbrl: "dólar mais caro", btcusd: "bitcoin mais barato", btcbrl: "bitcoin mais barato em reais" };
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

  /* ---------- formatação (pt-BR) ---------- */
  var nf = function (d) { return new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }); };
  var F0 = nf(0), F1 = nf(1), F2 = nf(2);
  function menos(s) { return s.replace("-", "−"); }
  /* preço: USD/BRL com 2 casas (ou 1, se arredondado); BTC sempre em "mil" */
  function moeda(a, v, arred) {
    if (a === "usdbrl") return "R$ " + (arred ? F1 : F2).format(v);
    var pre = a === "btcusd" ? "US$ " : "R$ ";
    if (v >= 1e6) return pre + F2.format(v / 1e6) + " mi";
    if (v >= 1e5 || arred) return pre + F0.format(v / 1e3) + " mil";
    return pre + F1.format(v / 1e3) + " mil";
  }
  function curto(a, v) {
    if (a === "usdbrl") return F2.format(v);
    if (v >= 1e6) return F1.format(v / 1e6) + " mi";
    if (v >= 1e5) return F0.format(v / 1e3) + " mil";
    return F1.format(v / 1e3) + " mil";
  }
  function pct(v, d) {
    d = d === undefined ? 1 : d;
    var t = nf(d).format(Math.abs(v * 100));
    if (Number(t.replace(",", ".")) === 0) return t + "%";
    return (v > 0 ? "+" : "−") + t + "%";
  }
  function pctN(v, d) { return nf(d === undefined ? 1 : d).format(v * 100) + "%"; }
  function pp(v, d) { return (v > 0 ? "+" : v < 0 ? "−" : "") + nf(d === undefined ? 1 : d).format(Math.abs(v)) + " p.p."; }
  function data(s) { if (!s) return "—"; var p = String(s).slice(0, 10).split("-"); return p[2] + "/" + p[1] + "/" + p[0]; }
  var MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  function mesAno(s) { var p = String(s).split("-"); return MES[Number(p[1]) - 1] + "/" + p[0].slice(2); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function el(id) { return document.getElementById(id); }
  /* cor pela direção ruim de cada ativo */
  function dir(a, v) { if (Math.abs(v) < .0005) return ""; return (a === "usdbrl" ? v > 0 : v < 0) ? "ruim" : "bom"; }
  function varC(a, v, d) { return '<span class="' + dir(a, v) + '">' + pct(v, d) + "</span>"; }

  function cenario(id) { return P.cenarios.filter(function (x) { return x.id === id; })[0]; }
  function dist() {
    if (estado.dist === "base") return { nome: "Distribuição-base", a: P.base };
    var c = cenario(estado.dist);
    return { nome: "Estresse " + c.nome + " (" + c.periodo + ")", a: c.ativos, c: c };
  }
  function porSeveridade(a) {
    return P.cenarios.slice().sort(function (x, y) { return y.severidade[a] - x.severidade[a]; });
  }
  function bt(corte, a, h) {
    return P.backtest.resumo.filter(function (q) { return q.corte === corte && q.ativo === a && String(q.h) === String(h); })[0];
  }

  /* ---------- 1. resumo ---------- */
  function regua(a) {
    var h = P.base[a].horizontes["365"], s0 = P.spot[a];
    var x = function (v) { return a === "usdbrl" ? Math.log(v / s0) : -Math.log(v / s0); };
    var pts = { P50: x(h.P50.nivel), P10: x(h.P10.nivel), P5: x(h.P5.nivel), P1: x(h.P1.nivel) };
    var lo = Math.min(0, pts.P50) - .04, hi = pts.P1 + .02;
    var pos = function (v) { return (100 * (v - lo) / (hi - lo)).toFixed(2) + "%"; };
    var faixa = function (a1, a2, cor) {
      return '<span class="regua__faixa" style="left:' + pos(pts[a1]) + ';width:calc(' + pos(pts[a2]) + ' - ' + pos(pts[a1]) + ');background:' + cor + '"></span>';
    };
    return '<div class="regua" aria-hidden="true"><span class="regua__trilho"></span>' +
      faixa("P50", "P10", "var(--band-1)") + faixa("P10", "P5", "var(--band-2)") + faixa("P5", "P1", "var(--band-3)") +
      '<span class="regua__marca" style="left:' + pos(0) + ';background:var(--tertiary)"></span>' +
      '<span class="regua__marca" style="left:' + pos(pts.P50) + ';background:var(--primary)"></span>' +
      '<span class="regua__marca" style="left:' + pos(pts.P1) + ';background:var(--red);width:3px"></span>' +
      '<span class="regua__rot regua__rot--cima" style="left:' + pos(pts.P50) + '">P50</span>' +
      '<span class="regua__rot regua__rot--cima regua__rot--fim" style="left:100%">P1</span>' +
      '<span class="regua__rot" style="left:' + pos(0) + '">hoje</span>' +
      '<span class="regua__rot regua__rot--fim" style="left:100%">pior →</span></div>';
  }

  function calibTexto(a) {
    var cl = HZ.map(function (z) { return bt("agregado", a, z).classe; });
    var ok = cl.filter(function (c) { return c === "na_meta"; }).length;
    var c365 = bt("2018", a, 365).classe === "na_meta" && bt("2021", a, 365).classe === "na_meta";
    return "Backtest: " + ok + " de 4 horizontes na meta somando os dois cortes" +
      (c365 ? "." : "; em 365 dias, a meta não se confirma nos dois cortes (amostra de 3 a 4 janelas independentes).");
  }

  function hero() {
    el("hero-data").innerHTML = '<span class="passo">1</span>Resumo · dados até ' + data(P.data_base) + " · " + F0.format(P.modelo.n_trajetorias) + " trajetórias";
    el("hero-lead").textContent = "Para cada ativo, o número em vermelho é o pior caso plausível: o nível que só 1 em cada 100 trajetórias simuladas ultrapassa no fim de 365 dias, na direção ruim (dólar mais caro, bitcoin mais barato). Abaixo dele, a mediana e as faixas intermediárias.";
    var html = "";
    ATIVOS.forEach(function (a) {
      var h = P.base[a].horizontes["365"];
      var pe = porSeveridade(a)[0], pv = pe.ativos[a].horizontes["365"].P50;
      html += '<article class="ativo" data-card="' + a + '" data-on="' + (a === estado.ativo) + '">' +
        '<div class="ativo__topo"><h2 class="ativo__nome">' + NOMES[a] + '</h2><span class="ativo__hoje n">hoje ' + moeda(a, P.spot[a]) + '</span></div>' +
        '<p class="ativo__p1"><span class="k">P1 · pior caso plausível em 365 dias</span><b class="n">' + moeda(a, h.P1.nivel, true) + '</b>' +
        '<span class="n">' + pct(h.P1.var_pct, 0) + " sobre hoje, " + PIOR[a] + '</span></p>' +
        regua(a) +
        '<dl class="ativo__q">' +
        '<div><dt>P50 · mediana</dt><dd class="n">' + moeda(a, h.P50.nivel, true) + '<small>' + pct(h.P50.var_pct, 0) + '</small></dd></div>' +
        '<div><dt>P10 · 1 em 10</dt><dd class="n">' + moeda(a, h.P10.nivel, true) + '<small>' + pct(h.P10.var_pct, 0) + '</small></dd></div>' +
        '<div><dt>P5 · 1 em 20</dt><dd class="n">' + moeda(a, h.P5.nivel, true) + '<small>' + pct(h.P5.var_pct, 0) + '</small></dd></div></dl>' +
        '<div class="ativo__extra"><p>Pior estresse para ' + NOMES[a] + ': ' + esc(pe.nome) + ' (' + esc(pe.periodo) + '), mediana de ' + moeda(a, pv.nivel, true) + ' (' + pct(pv.var_pct, 0) + ') em 365 dias.</p>' +
        '<p>' + esc(calibTexto(a)) + '</p></div>' +
        '<button type="button" class="ativo__ver" data-sel="' + a + '">' + (a === estado.ativo ? "Exibido nas seções abaixo" : "Ver " + NOMES[a] + " nas seções abaixo") + '</button>' +
        '</article>';
    });
    el("resumo").innerHTML = html;
    el("resumo").querySelectorAll("[data-sel]").forEach(function (b) {
      b.addEventListener("click", function () {
        selecionar(b.getAttribute("data-sel"));
        var alvo = el("h-leque"); if (alvo && alvo.scrollIntoView) alvo.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
    var pc = P.pior_caso;
    el("hero-conjunta").innerHTML =
      "Os dois P1 são marginais, cada um medido sozinho. Os dois juntos na mesma trajetória são muito mais raros: o dólar termina acima de " +
      moeda("usdbrl", pc.p1_usdbrl, true) + " e o bitcoin abaixo de " + moeda("btcusd", pc.p1_btcusd, true) + " em " + pctN(pc.prob_conjunta_p1, 2) +
      " das trajetórias. Tocar o P1 em algum momento do caminho é mais comum do que terminar além dele: " + pctN(pc.prob_toca_p1_usdbrl) + " no dólar e " + pctN(pc.prob_toca_p1_btcusd) + " no bitcoin. " +
      "Um risk-off conjunto (" + esc(pc.def_riskoff) + ") aparece em " + pctN(pc.prob_riskoff_conjunto_365d) + " das trajetórias.";
    var al = P.gatilhos.filter(function (g) { return g.status === "alerta"; }).map(function (g) { return g.nome; });
    var at = P.gatilhos.filter(function (g) { return g.status === "atencao"; }).map(function (g) { return g.nome; });
    var c = contagem();
    el("estado").innerHTML =
      '<li data-s="fora"><i aria-hidden="true"></i><span><b>Calibração incompleta.</b> ' + c.corte + " de 24 combinações na meta de 8% a 12% por corte, " + c.agr + " de 12 somando os cortes, e os choques da Covid em 30 dias ficaram além do P1. A especificação ainda não está cumprida (seção 6).</span></li>" +
      '<li data-s="' + (al.length ? "alerta" : "normal") + '"><i aria-hidden="true"></i><span><b>' + (al.length ? al.length + " gatilhos em alerta:" : "Nenhum gatilho em alerta.") + "</b> " + esc(al.join(", ")) + (at.length ? ". Em atenção: " + esc(at.join(", ")) : "") + ". Eles não alteram os números acima (seção 5).</span></li>";
  }

  function contagem() {
    var r = P.backtest.resumo;
    return {
      corte: r.filter(function (x) { return x.corte !== "agregado" && x.classe === "na_meta"; }).length,
      agr: r.filter(function (x) { return x.corte === "agregado" && x.classe === "na_meta"; }).length,
      inc: r.filter(function (x) { return x.corte !== "agregado" && x.classe === "inconclusivo"; }).length,
      fora: r.filter(function (x) { return x.corte !== "agregado" && (x.classe === "acima" || x.classe === "abaixo"); }).length
    };
  }

  /* ---------- seleção de ativo ---------- */
  function selecionar(a) {
    estado.ativo = a;
    document.querySelectorAll(".seg__btn").forEach(function (o) { o.setAttribute("aria-pressed", String(o.getAttribute("data-ativo") === a)); });
    document.querySelectorAll("[data-card]").forEach(function (o) { o.setAttribute("data-on", String(o.getAttribute("data-card") === a)); });
    document.querySelectorAll(".ativo__ver").forEach(function (o) { var x = o.getAttribute("data-sel"); o.textContent = x === a ? "Exibido nas seções abaixo" : "Ver " + NOMES[x] + " nas seções abaixo"; });
    chips(); leque(); horizontes(); heat(); cenarios();
  }

  /* ---------- 2. cone ---------- */
  function chips() {
    var a = estado.ativo;
    var h = '<button type="button" class="chip" data-d="base" aria-pressed="' + (estado.dist === "base") + '">Base</button>';
    porSeveridade(a).forEach(function (c) {
      h += '<button type="button" class="chip" data-d="' + c.id + '" aria-pressed="' + (estado.dist === c.id) + '">' + esc(c.nome) + '<small>' + esc(c.periodo) + '</small></button>';
    });
    var box = el("dist");
    box.innerHTML = h;
    box.querySelectorAll(".chip").forEach(function (b) {
      b.addEventListener("click", function () { estado.dist = b.getAttribute("data-d"); estado.dia = null; chips(); leque(); horizontes(); });
    });
    el("leque-sub").textContent = "Cada faixa é uma probabilidade, não uma previsão. A linha vermelha é o P1: só 1 em cada 100 trajetórias termina pior que ela. Toque no gráfico para ler um dia; os estresses usam o mesmo eixo da base.";
  }

  function niceLog(min, max, n) {
    var out = [], l0 = Math.log(min), l1 = Math.log(max);
    for (var i = 0; i < n; i++) {
      var v = Math.exp(l0 + (l1 - l0) * (i + .5) / n);
      var m = Math.pow(10, Math.floor(Math.log10(v)) - 1) * (v >= 1e4 ? 5 : 1);
      out.push(Math.round(v / m) * m);
    }
    return out.filter(function (v, i, a) { return a.indexOf(v) === i; });
  }

  function leque() {
    var a = estado.ativo, D = dist(), L = D.a[a].leque, B = P.base[a].leque;
    var box = el("leque"), W = Math.max(300, Math.round(box.clientWidth || 640));
    var estreito = W < 560;
    var H = estreito ? 300 : 390;
    var m = { l: estreito ? 42 : 56, r: estreito ? 66 : 92, t: 24, b: 30 };
    var hist = P.historico.slice(-(estreito ? 84 : 130));
    var nh = hist.length;
    var x0 = -(nh - 1), x1 = 252;
    // eixo fixo por ativo: o mesmo para a base e todos os estresses
    var vals = [];
    hist.forEach(function (h) { vals.push(h[a]); });
    [P.base].concat(P.cenarios.map(function (c) { return c.ativos; })).forEach(function (d) {
      d[a].leque.forEach(function (p) { vals.push(p.P1, p.P90f); });
    });
    var ymin = Math.min.apply(null, vals) * .97, ymax = Math.max.apply(null, vals) * 1.03;
    var X = function (d) { return m.l + (d - x0) / (x1 - x0) * (W - m.l - m.r); };
    var Y = function (v) { return m.t + (Math.log(ymax) - Math.log(v)) / (Math.log(ymax) - Math.log(ymin)) * (H - m.t - m.b); };
    var pth = function (pts) { return pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(""); };
    var linha = function (S, k) { return pth(S.map(function (p) { return [X(p.d), Y(p[k])]; })); };
    var faixa = function (k1, k2) {
      var up = L.map(function (p) { return [X(p.d), Y(p[k1])]; });
      var dn = L.slice().reverse().map(function (p) { return [X(p.d), Y(p[k2])]; });
      return pth(up.concat(dn)) + "Z";
    };
    var un = a === "btcusd" ? "US$" : "R$";
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Cone de risco de ' + NOMES[a] + " em 365 dias, " + esc(D.nome) + '. Valores nos cartões abaixo." tabindex="0">';
    s += '<text x="' + (m.l - 6) + '" y="' + (m.t - 10) + '" text-anchor="end" class="unidade">' + un + (a === "usdbrl" ? "" : "") + '</text>';
    niceLog(ymin, ymax, estreito ? 5 : 6).forEach(function (v) {
      var y = Y(v);
      s += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '" style="stroke:var(--hairline)" stroke-width="1"/>';
      s += '<text x="' + (m.l - 6) + '" y="' + (y + 4) + '" text-anchor="end">' + curto(a, v) + '</text>';
    });
    // eixo x: início do histórico, hoje e horizontes
    s += '<text x="' + X(x0) + '" y="' + (H - 9) + '" text-anchor="start">' + mesAno(hist[0].t) + '</text>';
    s += '<line x1="' + X(0) + '" x2="' + X(0) + '" y1="' + (m.t - 4) + '" y2="' + (H - m.b) + '" style="stroke:var(--secondary)" stroke-width="1"/>';
    s += '<text x="' + X(0) + '" y="' + (m.t - 10) + '" text-anchor="middle" class="unidade">hoje</text>';
    HZ.forEach(function (h) {
      var x = X(P.passos[h]);
      s += '<line x1="' + x + '" x2="' + x + '" y1="' + m.t + '" y2="' + (H - m.b) + '" style="stroke:var(--hairline)" stroke-dasharray="3 4"/>';
      s += '<text x="' + x + '" y="' + (H - 9) + '" text-anchor="middle">' + h + 'd</text>';
    });
    s += '<path d="' + faixa("P50", "P10") + '" style="fill:var(--band-1)"/>';
    s += '<path d="' + faixa("P10", "P5") + '" style="fill:var(--band-2)"/>';
    s += '<path d="' + faixa("P5", "P1") + '" style="fill:var(--band-3)"/>';
    if (D.c) {  // contorno fantasma da base
      s += '<path d="' + linha(B, "P1") + '" fill="none" style="stroke:var(--muted)" stroke-width="1.2" stroke-dasharray="2 3"/>';
      s += '<path d="' + linha(B, "P50") + '" fill="none" style="stroke:var(--muted)" stroke-width="1.2" stroke-dasharray="2 3"/>';
    }
    s += '<path d="' + linha(L, "P90f") + '" fill="none" style="stroke:var(--cold)" stroke-width="1.3" stroke-dasharray="5 4"/>';
    s += '<path d="' + linha(L, "P50") + '" fill="none" style="stroke:var(--primary)" stroke-width="1.8"/>';
    s += '<path d="' + linha(L, "P1") + '" fill="none" style="stroke:var(--red)" stroke-width="2.6"/>';
    s += '<path d="' + pth(hist.map(function (h, i) { return [X(i - (nh - 1)), Y(h[a])]; })) + '" fill="none" style="stroke:var(--primary)" stroke-width="1.5"/>';
    s += '<circle cx="' + X(0) + '" cy="' + Y(P.spot[a]) + '" r="4" style="fill:var(--primary)"/>';
    var fim = L[L.length - 1];
    var rot = [["P90", fim.P90f, "rot-bom"], ["P50", fim.P50, "rot-p50"], ["P10", fim.P10, ""], ["P5", fim.P5, ""], ["P1", fim.P1, "rot-p1"]]
      .map(function (r) { return { k: r[0], v: r[1], c: r[2], y: Y(r[1]) }; })
      .sort(function (p, q) { return p.y - q.y; });
    for (var i = 1; i < rot.length; i++) if (rot[i].y - rot[i - 1].y < 14) rot[i].y = rot[i - 1].y + 14;
    var exced = rot[rot.length - 1].y - (H - m.b + 4);
    if (exced > 0) rot.forEach(function (r) { r.y -= exced; });
    rot.forEach(function (r) {
      s += '<text x="' + (W - m.r + 6) + '" y="' + (r.y + 4) + '" class="' + r.c + '">' + r.k + " " + curto(a, r.v) + '</text>';
    });
    s += '<g id="cursor" style="display:none"><line y1="' + m.t + '" y2="' + (H - m.b) + '" style="stroke:var(--secondary)" stroke-width="1"/>' +
      '<circle r="4" class="c50" style="fill:var(--primary)"/><circle r="4.5" class="c1" style="fill:var(--red)"/></g>';
    s += "</svg>";
    box.innerHTML = s;

    var svg = box.querySelector("svg"), cur = svg.querySelector("#cursor");
    function marcar(d) {
      var p = L.reduce(function (b, q) { return Math.abs(q.d - d) < Math.abs(b.d - d) ? q : b; }, L[1]);
      if (p.d < 1) p = L[1];
      estado.dia = p.d;
      cur.style.display = "";
      cur.querySelector("line").setAttribute("x1", X(p.d)); cur.querySelector("line").setAttribute("x2", X(p.d));
      var c5 = cur.querySelector(".c50"), c1 = cur.querySelector(".c1");
      c5.setAttribute("cx", X(p.d)); c5.setAttribute("cy", Y(p.P50));
      c1.setAttribute("cx", X(p.d)); c1.setAttribute("cy", Y(p.P1));
      leitura(a, p);
    }
    function mover(ev) {
      var r = svg.getBoundingClientRect();
      var px = (ev.clientX - r.left) * (W / r.width);
      var d = x0 + (px - m.l) / (W - m.l - m.r) * (x1 - x0);
      if (d >= 0) marcar(Math.min(252, d));
    }
    svg.addEventListener("pointermove", mover);
    svg.addEventListener("pointerdown", mover);
    svg.addEventListener("keydown", function (ev) {
      var d = estado.dia || 252;
      if (ev.key === "ArrowLeft") { marcar(Math.max(1, d - 7)); ev.preventDefault(); }
      if (ev.key === "ArrowRight") { marcar(Math.min(252, d + 7)); ev.preventDefault(); }
    });
    marcar(estado.dia || 252);

    el("legenda").innerHTML =
      '<span><i style="background:var(--red);height:3px"></i>P1, pior caso plausível</span>' +
      '<span><i style="background:var(--band-3)"></i>P5 a P1</span>' +
      '<span><i style="background:var(--band-2)"></i>P10 a P5</span>' +
      '<span><i style="background:var(--band-1)"></i>P50 a P10</span>' +
      '<span><i style="background:var(--primary);height:2px"></i>Histórico e mediana</span>' +
      '<span><i style="border-top:1.5px dashed var(--cold);height:0"></i>P90, lado favorável</span>' +
      (D.c ? '<span><i style="border-top:1.5px dotted var(--muted);height:0"></i>Base, para comparar</span>' : "") +
      '<span>Escala logarítmica · eixo em dias úteis</span>';
  }

  function leitura(a, p) {
    var quando = P.datas_passos[p.d - 1];
    var dc = Math.round((new Date(quando) - new Date(P.data_base)) / 864e5);
    var s0 = P.spot[a];
    var v = function (k, rot, cls) {
      return '<div class="leitura__v ' + (cls || "") + '"><span class="k">' + rot + '</span><b class="n">' + moeda(a, p[k]) + '</b><small class="n">' + pct(p[k] / s0 - 1) + '</small></div>';
    };
    el("leitura").innerHTML =
      '<span class="leitura__quando">' + data(quando) + " · dia útil " + p.d + " (" + dc + " dias corridos) · " + esc(dist().nome) + "</span>" +
      v("P1", "P1", "p1") + v("P5", "P5") + v("P10", "P10") + v("P50", "Mediana");
  }

  function horizontes() {
    var a = estado.ativo, D = dist(), H = D.a[a].horizontes;
    var un = a === "usdbrl" ? "R$ por US$" : a === "btcusd" ? "US$" : "R$";
    var t = '<table class="hzt"><caption class="sr-only">' + NOMES[a] + ", " + esc(D.nome) + ", por horizonte</caption><thead><tr><th scope=\"col\">" + un + "</th>" +
      HZ.map(function (hz) { return '<th scope="col">' + hz + " dias<small>" + data(P.datas_passos[P.passos[hz] - 1]).slice(0, 5) + "</small></th>"; }).join("") + "</tr></thead><tbody>";
    [["P1", "P1", "p1"], ["P5", "P5", ""], ["P10", "P10", ""], ["P50", "P50", "p50"], ["P90f", "P90", "fav"]].forEach(function (q) {
      t += '<tr class="' + q[2] + '"><th scope="row">' + q[1] + "</th>" + HZ.map(function (hz) {
        var r = H[hz][q[0]];
        return '<td><b>' + curto(a, r.nivel) + "</b><small>" + pct(r.var_pct, 0) + "</small></td>";
      }).join("") + "</tr>";
    });
    el("horizontes").innerHTML = t + "</tbody></table>";
    var nota = a === "usdbrl" ? "Para USD/BRL, P10, P5 e P1 são os percentis 90, 95 e 99 da cotação: dólar mais caro."
      : "Para " + NOMES[a] + ", P10, P5 e P1 são os percentis 10, 5 e 1: preço mais baixo.";
    nota += " Datas em dias úteis da PTAX, sem feriados nacionais. " + NOMES[a] + ": " + DESC[a] + ".";
    if (D.c) nota += " Num estresse, a mediana reproduz a queda máxima do episódio; P5 e P1 somam a esse episódio a volatilidade de hoje e por isso ficam além do pior caso plausível da base.";
    el("nota-quantis").textContent = nota;
  }

  /* ---------- 3. mapa de calor ---------- */
  var DD_MAX = .9; // escala de cor fixa para os três ativos
  function heat() {
    var a = estado.ativo;
    var lbl = a === "usdbrl" ? "a perda máxima do real contra o dólar" : "a queda máxima de " + NOMES[a];
    el("dd-sub").textContent = "Mesmo quando o ponto final se recupera, o caminho pode cair muito antes. Cada célula mostra " + lbl +
      " desde o pico, até o horizonte. Número grande: a queda que 1 em cada 20 trajetórias ultrapassa (P5). Número pequeno: a mediana. Linhas da mais severa para a menos severa neste ativo.";
    var linhas = [{ nome: "Distribuição-base", sub: "GARCH-t e camada de crise", d: P.base[a].drawdown }]
      .concat(porSeveridade(a).map(function (c) {
        var hd = c.premissas.drawdown_historico[a];
        return { nome: c.nome + " (" + c.periodo + ")", sub: hd ? "histórico: " + pct(-hd, 0) : c.tipo, d: c.ativos[a].drawdown };
      }));
    var h = '<div class="heat__cab" aria-hidden="true">' + HZ.map(function (z) { return "<span>" + z + " dias</span>"; }).join("") + "</div>";
    linhas.forEach(function (l) {
      h += '<div class="heat__linha"><div class="heat__nome">' + esc(l.nome) + '<small>' + esc(l.sub) + '</small></div><div class="heat__cel" role="list">';
      HZ.forEach(function (z) {
        var v = l.d[z].P5, k = Math.round(6 + 70 * Math.min(1, v / DD_MAX));
        h += '<div role="listitem" class="' + (k > 48 ? "quente" : "") + '" style="background:color-mix(in srgb, var(--red) ' + k + '%, transparent)" aria-label="' + z + " dias: P5 " + pct(-v, 0) + ", mediana " + pct(-l.d[z].P50, 0) + '"><b class="n">' + pct(-v, 0) + '</b><small class="n">' + pct(-l.d[z].P50, 0) + "</small></div>";
      });
      h += "</div></div>";
    });
    el("heat").innerHTML = h;
    el("escala").innerHTML = '<span>0%</span><span class="escala__barra" style="background:linear-gradient(90deg, color-mix(in srgb, var(--red) 6%, transparent), color-mix(in srgb, var(--red) 76%, transparent))"></span><span>' + pct(-DD_MAX, 0) + "</span><span>mesma escala nos três ativos</span>";
  }

  /* ---------- 4. cenários ---------- */
  var UN = {
    fiscal: function (v) { return pp(v); }, selic_real: function (v) { return F1.format(v) + "%"; },
    ntnb: function (v) { return "IPCA + " + F2.format(v) + "%"; }, dxy: function (v) { return pct(v / 100); },
    fluxo: function (v) { return "percentil " + F0.format(v); }, riskoff: function (v) { return F1.format(v); },
    fed: function (v) { return pp(v, 2); }
  };
  var SIT = { presente: "Presente hoje", proxima: "Próxima", distante: "Distante", sem_dado: "Sem dado" };

  function cenarios() {
    var a = estado.ativo;
    el("est-sub").textContent = "Três episódios reconstruídos com dados reais e um cenário construído para 2026–27, aplicados aos preços de hoje. A mediana de cada estresse reproduz a queda máxima que o episódio teve de fato; nenhuma recuperação depois do pior ponto é assumida. Ordem pela queda mediana no caminho de " + NOMES[a] + ". Em “o que precisaria acontecer”, cada condição que foi gatilho no episódio é comparada com hoje pelas mesmas regras da seção 5: no episódio, os 63 dias úteis a partir do início; hoje, os 63 dias úteis até a data-base (Fed Funds e dívida: 12 meses).";
    el("cenarios").innerHTML = porSeveridade(a).map(function (c, i) {
      var pr = c.premissas, h = c.ativos[a].horizontes["365"], dd = c.ativos[a].drawdown["365"];
      var hd = pr.drawdown_historico[a];
      var foco = '<dl class="cen__foco">' +
        '<div><dt>Mediana em 365 dias</dt><dd class="n">' + moeda(a, h.P50.nivel, true) + "<small>" + varC(a, h.P50.var_pct, 0) + "</small></dd></div>" +
        '<div><dt>Queda mediana no caminho</dt><dd class="n ruim">' + pct(-dd.P50, 0) + "<small>" + (hd ? "no episódio: " + pct(-hd, 0) : "sem episódio próprio") + "</small></dd></div>" +
        '<div><dt>P5 em 365 dias</dt><dd class="n">' + moeda(a, h.P5.nivel, true) + "<small>" + varC(a, h.P5.var_pct, 0) + "</small></dd></div>" +
        '<div><dt>' + (c.tipo === "reconstruído" ? "No pior ponto conjunto" : "No pior ponto dos análogos") + '</dt><dd class="n">' + varC(a, pr.choque_no_pior_pct[a], 0) + "<small>" + (pr.data_pior ? data(pr.data_pior) + ", dia útil " + pr.dias_ate_pior : "dia útil " + pr.dias_ate_pior) + "</small></dd></div></dl>";
      var outros = ATIVOS.filter(function (x) { return x !== a; }).map(function (x) {
        return NOMES[x] + " " + varC(x, c.ativos[x].horizontes["365"].P50.var_pct, 0);
      }).join(" · ");
      var co = c.condicoes, anos = co.datas.map(function (d) { return d.slice(0, 4); });
      var conds = co.linhas.map(function (l) {
        var ep = l.episodio.map(function (v, j) { return (anos.length > 1 ? anos[j] + ": " : "") + (v === null ? "sem dado" : UN[l.id](v)); }).join(" · ");
        return '<li><span class="cond__nome">' + esc(l.nome) + '</span><span class="sit" data-s="' + l.situacao + '">' + SIT[l.situacao] + "</span>" +
          '<span class="cond__v">' + (anos.length > 1 ? "Nos análogos" : "No episódio") + ": <b class=\"n\">" + esc(ep) + "</b> · Hoje: <b class=\"n\">" + (l.hoje === null ? "sem dado" : esc(UN[l.id](l.hoje))) + "</b></span></li>";
      }).join("");
      var real = c.historico_real_pct && c.historico_real_pct["365"];
      var prem = [];
      prem.push(c.data_inicio_real ? "Início do episódio: " + data(c.data_inicio_real) + ". Pior ponto conjunto em " + data(pr.data_pior) + " (dia útil " + pr.dias_ate_pior + "): a trajetória dos dois ativos é seguida até essa mesma data e fica parada depois." :
        "Análogos com peso de 1/3 cada: " + c.analogos.map(data).join(", ") + ". O câmbio segue a média diária dos três até o pior ponto da média (dia útil " + pr.dias_ate_pior + "). O BTC não tem trajetória própria.");
      prem.push("Mediana calibrada sem dupla contagem: a trajetória histórica entra multiplicada por " + F2.format(pr.m_fx) + " no câmbio" + (c.tipo === "reconstruído" ? " e " + F2.format(pr.m_btc) + " no BTC" : "") +
        ", somada ao ruído do GARCH-t de hoje (escala " + F2.format(pr.lambda_fx) + " e " + F2.format(pr.lambda_btc) + "), para que a queda mediana no caminho seja igual à do episódio" + (c.tipo === "construído" ? " (média dos análogos)" : "") + ".");
      prem.push("Volatilidade de partida: a condicional de hoje, " + F0.format(pr.vol_atual_fx * 100) + "% a.a. no câmbio e " + F0.format(pr.vol_atual_btc * 100) + "% a.a. no BTC, que volta à média de longo prazo pelo GARCH. A camada de crise da base não entra nos estresses.");
      prem.push("Correlação real × BTC: " + (pr.rho_episodio !== null ? F2.format(pr.rho_episodio) + " no episódio; " : "sem episódio, parte da de hoje (" + F2.format(pr.rho_hoje) + "); ") + "usada " + F2.format(pr.rho_usado) + ", a maior entre essa e o percentil 95 da janela de 63 dias (" + F2.format(pr.rho_p95_63d) + "), com cópula t de " + F0.format(pr.nu_copula) + " graus de liberdade.");
      if (real) prem.push("O que aconteceu de fato em 365 dias: USD/BRL " + pct(real.usdbrl) + ", BTC/USD " + pct(real.btcusd) + ", BTC/BRL " + pct(real.btcbrl) + ". A recuperação depois do pior ponto não entra no cenário.");
      prem.push("P5 e P1 do estresse somam o episódio à volatilidade de hoje. Por isso ficam além do pior movimento histórico de 12 meses (" + NOMES[a] + ": " + pct(P.ancoras[a].var_pct, 0) + ", " + mesAno(P.ancoras[a].inicio) + " a " + mesAno(P.ancoras[a].fim) + ") e fora do que o painel chama de plausível.");
      return '<article class="cen">' +
        '<div class="cen__topo"><span class="cen__ordem">' + (i + 1) + "º para " + NOMES[a] + '</span><span class="cen__tipo">' + esc(c.tipo) + "</span></div>" +
        "<h3>" + esc(c.nome) + " (" + esc(c.periodo) + ")</h3>" + '<p class="cen__resumo">' + esc(c.resumo) + "</p>" +
        foco + '<p class="cen__outros">Mediana em 365 dias dos outros ativos: ' + outros + ".</p>" +
        '<h4 class="h3">O que precisaria acontecer</h4>' +
        '<ul class="cond">' + conds + (co.qualitativo ? '<li><span class="cond__nome">Quebras no setor cripto</span><span class="sit" data-s="sem_dado">Sem dado</span><span class="cond__v">' + esc(co.qualitativo) + "</span></li>" : "") + "</ul>" +
        '<details class="mais"><summary>Premissas do cenário</summary><ul>' + prem.map(function (t) { return "<li>" + t + "</li>"; }).join("") + "</ul></details></article>";
    }).join("");
  }

  /* ---------- 5. gatilhos ---------- */
  function gatilhos() {
    var nomeS = { alerta: "Alerta", atencao: "Atenção", normal: "Normal", sem_dado: "Sem dado" };
    var ordem = { alerta: 0, atencao: 1, normal: 2, sem_dado: 3 };
    el("gatilhos").innerHTML = P.gatilhos.slice().sort(function (x, y) { return ordem[x.status] - ordem[y.status]; }).map(function (g) {
      var ds = Object.keys(g.datas || {}).map(function (k) { return k + " " + data(g.datas[k]); });
      return '<li class="gat"><div class="gat__topo"><span class="gat__nome">' + esc(g.nome) + '</span><span class="pill" data-s="' + g.status + '">' + nomeS[g.status] + "</span></div>" +
        "<div><p>" + esc(g.leitura) + '</p><small><span class="tag">' + esc(g.efeito) + "</span> " + esc(g.regra) + " Fonte: " + esc(g.fonte) + (ds.length ? ". Dado mais recente: " + esc(ds.join(", ")) : "") + ".</small></div></li>";
    }).join("");
  }

  /* ---------- 6. backtest ---------- */
  var CL = { na_meta: "na meta", inconclusivo: "inconclusivo", acima: "risco subestimado", abaixo: "pessimista demais" };
  function gradeBT(corte) {
    return '<div class="grade">' + ATIVOS.map(function (a) {
      var n = bt(corte, a, 30);
      return '<div class="grade__linha"><div class="grade__nome">' + NOMES[a] + "<small>" + F0.format(n.n) + " origens</small></div>" +
        '<div class="grade__cel">' + HZ.map(function (z) {
          var x = bt(corte, a, z);
          return '<div data-c="' + x.classe + '" aria-label="' + z + " dias: " + pctN(x.abaixo_p10) + ", " + CL[x.classe] + '"><span class="h">' + z + 'd</span><b class="n">' + pctN(x.abaixo_p10) + '</b><small class="n">IC ' + F0.format(x.ic95[0] * 100) + "–" + F0.format(x.ic95[1] * 100) + "%<br>~" + x.n_indep + " indep.</small></div>";
        }).join("") + "</div></div>";
    }).join("") + "</div>";
  }
  function chave() {
    return '<ul class="chave"><li><i style="border-color:var(--ok)"></i>Na meta (8% a 12%)</li><li><i></i>Inconclusivo: fora da meta, mas o intervalo de 95% a cruza</li><li><i style="border-color:var(--red);background:var(--red-soft)"></i>Risco subestimado</li><li><i style="border-color:var(--amber)"></i>Pessimista demais</li></ul>';
  }
  function backtest() {
    var c = contagem();
    el("bt-sub").textContent = "Parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), congelados depois. A cada 5 dias úteis o modelo projetou de novo e comparamos com o que aconteceu. Meta da especificação: o realizado fica pior que o P10 entre 8% e 12% das vezes. Cada célula traz essa frequência, o intervalo de confiança de 95% (Wilson) e o número aproximado de janelas independentes.";
    el("bt-veredito").innerHTML = "<b>Especificação ainda não cumprida.</b><span>Por corte, " + c.corte + " de 24 combinações estão na meta, " + c.inc + " são inconclusivas e " + c.fora + " ficam fora com significância. Somando os cortes, " + c.agr + " de 12. Os choques da Covid em 30 dias ficaram além do P1, então o P5 não contém todos os choques reais.</span>";
    el("bt").innerHTML = '<h3 class="h3">Somando os dois cortes</h3>' + gradeBT("agregado") + chave();
    el("bt-cortes").innerHTML = '<p class="note">Corte 2018: projeções de 2018 a 2020. Corte 2021: projeções de 2021 a 2026.</p><h3 class="h3">Corte 2018</h3>' + gradeBT("2018") + '<h3 class="h3">Corte 2021</h3>' + gradeBT("2021");
    var txt = function (v) { return v < .01 ? "pior que o P1" : v < .05 ? "entre P5 e P1" : v < .10 ? "entre P10 e P5" : "melhor que o P10"; };
    el("bt-choques").innerHTML = '<p class="note">Posição do realizado na distribuição projetada às vésperas de cada choque, medida na direção ruim: 0% é o pior extremo e 50% é a mediana. Vermelho: fora do P5.</p>' +
      P.backtest.choques.map(function (ch) {
        return '<div class="grade"><h4 class="h3">' + esc(ch.nome) + "</h4>" + ATIVOS.map(function (a) {
          return '<div class="grade__linha"><div class="grade__nome">' + NOMES[a] + '</div><div class="grade__cel">' + HZ.map(function (z) {
            var v = ch.pit[a] && ch.pit[a][z];
            if (v === undefined) return "<div><span class=\"h\">" + z + "d</span><b>—</b></div>";
            return '<div data-c="' + (v < .05 ? "acima" : "na_meta") + '"><span class="h">' + z + 'd</span><b class="n">' + pctN(v) + "</b><small>" + txt(v) + "</small></div>";
          }).join("") + "</div></div>";
        }).join("") + "</div>";
      }).join("");
    el("bt-nota").textContent = "Leitura: com origens sobrepostas, há poucas janelas independentes (de 3 a 69 por célula), e quase todas as diferenças em relação à meta cabem no acaso. No corte 2018, o modelo subestimou a desvalorização do real de 2018 a 2020; no corte 2021, foi pessimista demais em USD/BRL de 90 e 180 dias. A Covid ficou além do P1 em 30 dias nos três ativos e em 90 dias no câmbio; o inverno cripto ficou entre P5 e P1 em BTC/USD (365 dias) e BTC/BRL (180 e 365 dias). É para esses casos que existem os estresses da seção 4.";
  }

  /* ---------- 7. método e fontes ---------- */
  function corr() {
    var C = P.correlacao, S = C.serie, box = el("corr");
    var W = Math.max(300, Math.round(box.clientWidth || 520)), H = 200, m = { l: 34, r: 12, t: 10, b: 24 };
    var y0 = -.3, y1 = .8;
    var X = function (i) { return m.l + i / (S.length - 1) * (W - m.l - m.r); };
    var Y = function (v) { return m.t + (y1 - v) / (y1 - y0) * (H - m.t - m.b); };
    var ln = function (k) { return S.map(function (p, i) { return (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(Math.max(y0, Math.min(y1, p[k]))).toFixed(1); }).join(""); };
    var s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Correlação móvel entre os choques do real e do bitcoin, janelas de 63 e 250 dias, desde 2016">';
    [-.2, 0, .2, .4, .6].forEach(function (v) {
      s += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(v) + '" y2="' + Y(v) + '" style="stroke:var(--hairline)"/>';
      s += '<text x="' + (m.l - 6) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + menos(F1.format(v)) + "</text>";
    });
    var anos = {};
    S.forEach(function (p, i) { var y = p.t.slice(0, 4); if (!anos[y] && Number(y) % 2 === 0) { anos[y] = 1; s += '<text x="' + X(i) + '" y="' + (H - 6) + '" text-anchor="middle">' + y + "</text>"; } });
    s += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(C.p95_63d) + '" y2="' + Y(C.p95_63d) + '" style="stroke:var(--red)" stroke-dasharray="4 4"/>';
    s += '<path d="' + ln("r63") + '" fill="none" style="stroke:var(--muted)" stroke-width="1"/>';
    s += '<path d="' + ln("r250") + '" fill="none" style="stroke:var(--primary)" stroke-width="1.8"/>';
    box.innerHTML = s + "</svg>";
    el("corr-cap").innerHTML = "<b>Correlação móvel entre os choques do real e do BTC.</b> Linha escura: janela de 250 dias (hoje " + F2.format(C.hoje_250d) + ", usada na base). Linha clara: 63 dias (hoje " + menos(F2.format(C.hoje_63d)) + "). Tracejado vermelho: percentil 95 da janela de 63 dias (" + F2.format(C.p95_63d) + "), o piso usado nos estresses.";
  }

  function metodo() {
    var mo = P.modelo, fx = mo.fx, bc = mo.btc, dv = mo.deriva_fx, ec = mo.efeito_crise;
    var itens = [
      "<b>Monte Carlo com " + F0.format(mo.n_trajetorias) + " trajetórias</b> de 252 dias úteis (cerca de 365 corridos). Os horizontes de 30, 90, 180 e 365 dias correspondem a 21, 63, 126 e 252 dias úteis.",
      "<b>Volatilidade GJR-GARCH(1,1) com inovações t de Student.</b> Câmbio desde " + data(mo.amostra_fx[0]) + ": ν = " + F1.format(fx.nu) + ", persistência " + F2.format(fx.persistencia) + ", meia-vida de " + F0.format(fx.meia_vida_dias) + " dias. BTC desde " + data(mo.amostra_btc[0]) + ": ν = " + F1.format(bc.nu) + ", persistência " + F2.format(bc.persistencia) + ". A largura dos cones depende da volatilidade de hoje, que está " +
        (mo.vol_atual.usdbrl > mo.vol_longo_prazo.usdbrl ? "acima" : "abaixo") + " da média no câmbio (" + F0.format(mo.vol_atual.usdbrl * 100) + "% a.a. contra " + F0.format(mo.vol_longo_prazo.usdbrl * 100) + "%) e " +
        (mo.vol_atual.btcusd > mo.vol_longo_prazo.btcusd ? "acima" : "abaixo") + " no BTC (" + F0.format(mo.vol_atual.btcusd * 100) + "% contra " + F0.format(mo.vol_longo_prazo.btcusd * 100) + "%), e converge para a média ao longo do horizonte.",
      "<b>Deriva do câmbio pelo juro real.</b> Uma regressão (Newey-West, desde 2003) liga o retorno do real nos 63 dias seguintes ao juro real ex-post. Com o juro real de hoje (" + F1.format(dv.juro_real_hoje) + "%, acima do neutro estimado de " + F1.format(dv.juro_neutro) + "%), a mediana do dólar recua " + pct(dv.deriva_anual_usdbrl_pct).replace("−", "") + " ao ano. Essa escolha foi feita olhando o backtest (risco de sobreajuste). O BTC não tem deriva.",
      "<b>Camada de crise:</b> crises de 21 dias que o GARCH-t sozinho gera menos do que a história mostra. Câmbio: " + F2.format(mo.crise_fx.taxa_anual) + " crise extra por ano, choque mediano de " + pct(Math.exp(-mo.crise_fx.severidade) - 1, 0) + " no dólar, " + F0.format(mo.crise_fx.frac_devolvida * 100) + "% devolvidos em 126 dias. BTC: " + F2.format(mo.crise_btc.taxa_anual) + " por ano, " + pct(Math.exp(mo.crise_btc.severidade) - 1, 0) + ", " + F0.format(mo.crise_btc.frac_devolvida * 100) + "% devolvidos. Ela só empurra para o lado ruim: desloca a mediana de 365 dias do USD/BRL de " + pct(ec.usdbrl.mediana_sem) + " para " + pct(ec.usdbrl.mediana_com) + " e a do BTC/USD de " + pct(ec.btcusd.mediana_sem) + " para " + pct(ec.btcusd.mediana_com) + ". Não entra nos estresses.",
      "<b>Dependência por cópula t.</b> Na base, a correlação é a dos últimos 250 dias (" + F2.format(mo.rho_250d) + ") e os graus de liberdade estimados batem no teto (ν = " + F0.format(mo.nu_copula) + "): a dependência é quase gaussiana e as caudas conjuntas não são reforçadas. Nos estresses, a correlação sobe para pelo menos " + F2.format(mo.rho_estresse_p95_63d) + " e ν cai para " + F0.format(mo.nu_copula_estresse) + ", o que junta as caudas.",
      "<b>BTC/BRL nunca é projetado sozinho:</b> em cada trajetória, BTC/BRL = BTC/USD × USD/BRL.",
      "<b>Sem previsão pontual:</b> toda saída é distribuição (P50, P10, P5, P1). O P90 aparece só como referência do lado favorável.",
      "<b>Âncoras históricas, piores 12 meses:</b> USD/BRL " + pct(P.ancoras.usdbrl.var_pct, 0) + " (" + mesAno(P.ancoras.usdbrl.inicio) + " a " + mesAno(P.ancoras.usdbrl.fim) + ", desde 1999); BTC/USD " + pct(P.ancoras.btcusd.var_pct, 0) + " (" + mesAno(P.ancoras.btcusd.inicio) + " a " + mesAno(P.ancoras.btcusd.fim) + "); BTC/BRL " + pct(P.ancoras.btcbrl.var_pct, 0) + " (" + mesAno(P.ancoras.btcbrl.inicio) + " a " + mesAno(P.ancoras.btcbrl.fim) + "). O P1 da base fica perto delas ou além."
    ];
    el("premissas").innerHTML = itens.map(function (t) { return "<li>" + t + "</li>"; }).join("");
    corr();
    var R = P.referencias, ano = P.data_base.slice(0, 4), prox = String(Number(ano) + 1);
    el("refs").innerHTML = '<h3 class="h3">Referências para a mediana do dólar</h3><dl>' +
      "<div><dt>Mediana do modelo em 365 dias</dt><dd class=\"n\">" + moeda("usdbrl", R.mediana_365_usdbrl) + "</dd></div>" +
      "<div><dt>Forward de 1 ano pelo diferencial Selic " + F2.format(R.selic) + "% − Fed Funds " + F2.format(R.fed_funds) + "% (inferência)</dt><dd class=\"n\">" + moeda("usdbrl", R.forward_1a_usdbrl) + "</dd></div>" +
      "<div><dt>Focus, câmbio no fim de " + ano + "</dt><dd class=\"n\">" + moeda("usdbrl", R.focus_cambio[ano]) + "</dd></div>" +
      "<div><dt>Focus, câmbio no fim de " + prox + "</dt><dd class=\"n\">" + moeda("usdbrl", R.focus_cambio[prox]) + "</dd></div></dl>" +
      '<p class="note">O forward embute o carrego, não uma expectativa. O Focus é a mediana dos economistas em ' + data(R.focus_data) + ". Nenhum dos dois entra no modelo.</p>";
    el("fontes").innerHTML = P.fontes.map(function (f) {
      return "<li><b>" + esc(f.serie) + '</b><a href="' + esc(f.url) + '" rel="noopener">' + esc(f.fonte) + "</a><span>Último dado " + data(f.ultimo_dado) + " · coletado em " + esc(f.coletado_em.replace("T", " ").replace("+00:00", " UTC")) + "</span></li>";
    }).join("");
    el("rodape-data").textContent = "Gerado em " + P.gerado_em.replace("T", " ").replace("+00:00", " UTC") + " · dados até " + data(P.data_base);
  }

  function iniciar(dados) {
    P = dados;
    document.querySelectorAll(".seg__btn").forEach(function (b) {
      b.addEventListener("click", function () { selecionar(b.getAttribute("data-ativo")); });
    });
    hero(); chips(); leque(); horizontes(); heat(); cenarios(); gatilhos(); backtest(); metodo();
    var ultimaL = 0;
    window.addEventListener("resize", function () {
      var w = el("leque").clientWidth;
      if (Math.abs(w - ultimaL) > 24) { ultimaL = w; leque(); corr(); }
    });
  }

  fetch("projections.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(iniciar)
    .catch(function (e) {
      el("hero-data").textContent = "Não foi possível carregar projections.json (" + e.message + "). Abra o painel por um servidor web, não pelo arquivo local.";
    });
})();
