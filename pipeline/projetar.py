"""Gera projections.json: distribuição-base, cenários de estresse, drawdowns,
gatilhos monitorados e resumo do backtest.

Rodar depois de coletar.py e backtest.py:
    python3 pipeline/coletar.py && python3 pipeline/backtest.py zero 0 crise && python3 pipeline/projetar.py
"""
import json, sys
from datetime import datetime, timezone, date
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from nucleo import *

N = 20000
SEED = 20261125
ATIVOS = ["usdbrl", "btcusd", "btcbrl"]
NOMES = {"usdbrl": "USD/BRL", "btcusd": "BTC/USD", "btcbrl": "BTC/BRL"}
QB = {"P50": .50, "P10": .10, "P5": .05, "P1": .01, "P90f": .90}  # na direção ruim (baixo = pior)
CONFIG_BACKTEST = "v3_1999_crise_recal"
from variantes import VARIANTES
CFG = VARIANTES[CONFIG_BACKTEST]
N_DENTRO, PASSO_DENTRO, K_MAX = 2000, 10, 2.0


def arquivo_ou_resumo(completo, resumo):
    """Os brutos do Tesouro e do Focus anual são grandes e não vão para o git;
    sem eles, usa o extrato compacto (versionado) gravado na mesma coleta."""
    f = RAW / f"{completo}.json"
    return f if f.exists() else RAW / f"{resumo}.json"


def meta_serie(nome):
    if nome in ("tesouro_direto", "focus_anuais"):
        nome = arquivo_ou_resumo(nome, {"tesouro_direto": "tesouro_resumo", "focus_anuais": "focus_resumo"}[nome]).stem
    d = json.loads((RAW / f"{nome}.json").read_text())
    ult = None
    if d["dados"] and isinstance(d["dados"][-1], list):
        ult = max(str(x[0]) for x in d["dados"])
    elif d["dados"] and isinstance(d["dados"][-1], dict) and "Data" in d["dados"][-1]:
        ult = max(str(x["Data"]) for x in d["dados"])
    return {"serie": nome, "fonte": d["fonte"], "url": d["url"], "coletado_em": d["coletado_em"],
            "ultimo_dado": ult}


def niveis(sf, sb, s0f, s0b):
    """Converte caminhos acumulados (direção ruim) em níveis de preço."""
    fx = s0f * np.exp(-sf)          # x_fx = -dlog(USD/BRL)
    btc = s0b * np.exp(sb)
    return {"usdbrl": fx, "btcusd": btc, "btcbrl": btc * fx}


def ruim(a, lv):
    """Log-nível na direção ruim (baixo = pior) para quantis homogêneos."""
    return -np.log(lv) if a == "usdbrl" else np.log(lv)


def k_no_passo(kh, t):
    """Fator de recalibração no passo t (0 a 251), interpolado entre os
    horizontes; antes de 21 dias úteis vale o de 30 dias."""
    if kh is None:
        return 1.0
    xs = [HORIZ_PASSOS[h] - 1 for h in HORIZ_DIAS]
    ys = [kh[h] for h in HORIZ_DIAS]
    return float(np.interp(t, xs, ys))


def quantis_nivel(a, lv_col, k=1.0):
    """Quantis de preço na direção ruim: para USD/BRL, P10 é o 90º percentil.
    Com k > 1 (recalibração), a cauda ruim é lida nos níveis p/k do modelo."""
    out = {}
    for nome, q in QB.items():
        q = q / k if q < .5 else q
        qq = 1 - q if a == "usdbrl" else q
        out[nome] = float(np.quantile(lv_col, qq))
    return out


def resumo_dist(a, lv, s0, kh=None):
    tab = {}
    for hd, hp in HORIZ_PASSOS.items():
        q = quantis_nivel(a, lv[:, hp - 1], kh[hd] if kh else 1.0)
        tab[str(hd)] = {k: {"nivel": v, "var_pct": v / s0 - 1} for k, v in q.items()}
    return tab


def leque(a, lv, s0, passo=3, kh=None):
    pts = []
    for t in list(range(0, H_MAX, passo)) + [H_MAX - 1]:
        q = quantis_nivel(a, lv[:, t], k_no_passo(kh, t))
        pts.append({"d": t + 1, **{k: round(v, 6) for k, v in q.items()}})
    return [{"d": 0, **{k: s0 for k in QB}}] + pts


def drawdowns(a, lv, s0, kh=None):
    """Drawdown máximo na direção ruim até cada horizonte. Com recalibração, os
    quantis altos do drawdown são lidos nos mesmos níveis p/k da cauda."""
    base = ruim(a, lv) - ruim(a, np.array([s0]))[0]
    dd = drawdown_ate(base, HORIZ_PASSOS)
    out = {}
    for h, v in dd.items():
        k = kh[h] if kh else 1.0
        out[str(h)] = {"P50": float(np.quantile(v, .5)), "P10": float(np.quantile(v, 1 - .10 / k)),
                       "P5": float(np.quantile(v, 1 - .05 / k)), "P1": float(np.quantile(v, 1 - .01 / k))}
    return out


def estimar_recal(gf, gb, cf, cb, xfx, s2f, r, s2b, zf, zb, df, fx_niv, nu_c, rng):
    """Recalibração da cauda ruim estimada no histórico (dentro da amostra), com
    a mesma regra do backtest: k = (frequência abaixo do P10) / 10%, entre 1 e 2.
    Câmbio: origens desde 1999 (só câmbio). BTC e BTC/BRL: origens desde 2016."""
    dentro = {a: {h: [] for h in HORIZ_DIAS} for a in ATIVOS}

    def registra(o, sf, sb, nivel_fx, nivel_btc, ativos):
        idx = nivel_fx.index
        i0 = idx.get_loc(o)
        for hd, hp in HORIZ_PASSOS.items():
            if i0 + hp >= len(idx):
                continue
            rf = -np.log(nivel_fx.iloc[i0 + hp] / nivel_fx.iloc[i0])
            if "usdbrl" in ativos:
                dentro["usdbrl"][hd].append(float((sf[:, hp - 1] < rf).mean()))
            if sb is not None:
                rb = np.log(nivel_btc.iloc[i0 + hp] / nivel_btc.iloc[i0])
                dentro["btcusd"][hd].append(float((sb[:, hp - 1] < rb).mean()))
                dentro["btcbrl"][hd].append(float((sb[:, hp - 1] - sf[:, hp - 1] < rb - rf).mean()))

    for o in fx_niv.index[(fx_niv.index > xfx.index[300])][::PASSO_DENTRO]:
        if o not in s2f.index:
            continue
        v = gf.omega + (gf.alpha + gf.gamma * (xfx[o] < 0)) * xfx[o] ** 2 + gf.beta * s2f[o]
        e = t_padronizada_ppf(np.clip(rng.random((N_DENTRO, H_MAX)), 1e-12, 1 - 1e-12), gf.nu)
        sf = simular_com_crise(gf, v, e, 0.0, cf, rng).cumsum(axis=1)
        registra(o, sf, None, fx_niv, None, ["usdbrl"])
    grade = np.round(np.arange(-0.3, 0.651, 0.05), 2)
    inov = {}
    idx = df.index
    for o in idx[idx > idx[300]][::PASSO_DENTRO]:
        rho = float(zf[:o].iloc[-250:].corr(zb[:o].iloc[-250:]))
        g = float(grade[np.argmin(np.abs(grade - rho))])
        if g not in inov:
            inov[g] = inovacoes(N_DENTRO, H_MAX, g, nu_c, gf.nu, gb.nu, rng)
        e1, e2 = inov[g]
        xo = xfx[o]
        vf = gf.omega + (gf.alpha + gf.gamma * (xo < 0)) * xo ** 2 + gf.beta * s2f[o]
        xb = r["x_btc"][o]
        vb = gb.omega + (gb.alpha + gb.gamma * (xb < 0)) * xb ** 2 + gb.beta * s2b[o]
        sf = simular_com_crise(gf, vf, e1, 0.0, cf, rng).cumsum(axis=1)
        sb = simular_com_crise(gb, vb, e2, 0.0, cb, rng).cumsum(axis=1)
        registra(o, sf, sb, df["fx"], df["btc"], ["btcusd", "btcbrl"])
    out = {}
    for a in ATIVOS:
        out[a] = {}
        for h in HORIZ_DIAS:
            v = np.array(dentro[a][h])
            f10 = float((v < .10).mean())
            out[a][h] = {"k": float(np.clip(f10 / .10, 1.0, K_MAX)), "f10_dentro": f10, "n_dentro": len(v),
                         "f5_dentro": float((v < .05).mean()), "f90_dentro": float((v > .90).mean())}
    return out


def main():
    rng = np.random.default_rng(SEED)
    df = base_diaria()
    r = retornos(df)
    fx_long, _ = serie("usdbrl_ptax")
    xfx_todo = -np.log(fx_long).diff().dropna()   # desde 1999, para os análogos
    xfx = xfx_todo[CFG["fx_ini"]:]
    gf = Garch(xfx.values)
    gb = Garch(r["x_btc"].values)
    cf = estimar_crise(xfx.values, g=gf)
    cb = estimar_crise(r["x_btc"].values, g=gb)
    _, vf = gf.filtrar(xfx.values)
    _, vb = gb.filtrar(r["x_btc"].values)
    s2f, _ = gf.filtrar(xfx.values)
    s2b, _ = gb.filtrar(r["x_btc"].values)
    zf = pd.Series(xfx.values / np.sqrt(s2f), index=xfx.index).reindex(r.index)
    zb = pd.Series(r["x_btc"].values / np.sqrt(s2b), index=r.index)
    ok = zf.notna()
    zf, zb = zf[ok], zb[ok]
    rho_250 = float(zf.iloc[-250:].corr(zb.iloc[-250:]))
    roll63 = zf.rolling(63).corr(zb).dropna()
    rho_stress = float(roll63.quantile(.95))
    nu_c = ajustar_nu_copula(zf.values, zb.values, float(zf.corr(zb)))
    NU_C_STRESS = 4.0

    s0f, s0b = float(df["fx"].iloc[-1]), float(df["btc"].iloc[-1])
    data_base = df.index[-1]

    # ---------- distribuição-base ----------
    e1, e2 = inovacoes(N, H_MAX, rho_250, nu_c, gf.nu, gb.nu, rng)
    sf = simular_com_crise(gf, vf, e1, 0.0, cf, rng).cumsum(axis=1)
    sb = simular_com_crise(gb, vb, e2, 0.0, cb, rng).cumsum(axis=1)
    lv = niveis(sf, sb, s0f, s0b)
    spot = {"usdbrl": s0f, "btcusd": s0b, "btcbrl": s0f * s0b}
    recal = None
    if CFG.get("recal"):
        s2f_s = pd.Series(s2f, index=xfx.index)
        s2b_s = pd.Series(s2b, index=r.index)
        cache = RAIZ / "data" / "processed" / f"recal_{CONFIG_BACKTEST}.json"
        chave = {"data_base": str(data_base.date()), "variante": CONFIG_BACKTEST, "n": N_DENTRO, "passo": PASSO_DENTRO}
        c_ok = cache.exists() and json.loads(cache.read_text()).get("chave") == chave
        if c_ok:
            recal = {a: {int(h): v for h, v in d.items()} for a, d in json.loads(cache.read_text())["recal"].items()}
        else:
            recal = estimar_recal(gf, gb, cf, cb, xfx, s2f_s, r, s2b_s, zf, zb, df, fx_long[CFG["fx_ini"]:], nu_c,
                                  np.random.default_rng(SEED + 1))
            cache.write_text(json.dumps({"chave": chave, "recal": recal}))
    KH = {a: ({h: recal[a][h]["k"] for h in HORIZ_DIAS} if recal else None) for a in ATIVOS}
    base = {a: {"horizontes": resumo_dist(a, lv[a], spot[a], KH[a]), "leque": leque(a, lv[a], spot[a], kh=KH[a]),
                "drawdown": drawdowns(a, lv[a], spot[a], KH[a])} for a in ATIVOS}
    # probabilidade conjunta de risk-off: real perde >10% e BTC cai >30% em 365 dias
    conj = float(((lv["usdbrl"][:, -1] / s0f > 1 / 0.9) & (lv["btcusd"][:, -1] / s0b < 0.7)).mean())

    # ---------- cenários de estresse ----------
    idx = df.index
    xr = r.reindex(idx).fillna(0.0)

    def trilha(ini, col):
        i0 = idx.get_indexer([pd.Timestamp(ini)], method="bfill")[0]
        x = xr[col].iloc[i0 + 1:i0 + 1 + H_MAX].values
        return x, idx[i0]

    def trilha_fx_longa(ini):
        i0 = xfx_todo.index.get_indexer([pd.Timestamp(ini)], method="bfill")[0]
        return xfx_todo.iloc[i0 + 1:i0 + 1 + H_MAX].values, xfx_todo.index[i0]

    def ate_o_fundo(x):
        c = np.cumsum(x)
        k = int(np.argmin(c))
        alvo = np.where(np.arange(len(x)) <= k, x, 0.0)
        return alvo, k, float(c[k]), float(c[-1])

    CEN = [
        dict(id="covid2020", nome="Covid", periodo="mar/2020", inicio="2020-02-14", tipo="reconstruído",
             resumo="Choque global de liquidez: o real e o bitcoin caem juntos, no mesmo mês."),
        dict(id="fiscal2015", nome="Crise fiscal", periodo="2015", inicio="2015-01-26", tipo="reconstruído",
             resumo="Deterioração fiscal doméstica, perda do grau de investimento e recessão."),
        dict(id="cripto2022", nome="Inverno cripto", periodo="2022", inicio="2021-11-10", tipo="reconstruído",
             resumo="Alta de juros nos EUA, quebras no setor cripto (Terra/Luna, FTX) e BTC em queda longa."),
        dict(id="fiscal2627", nome="Fiscal e eleitoral", periodo="2026–27", inicio=None, tipo="construído",
             analogos=["2002-04-01", "2015-01-02", "2024-09-30"],
             resumo="Hipótese: transição pós-eleitoral com dúvida sobre o arcabouço fiscal. Real segue a média de 2002, 2015 e 2024; BTC sem deriva própria, contágio só pela correlação piorada."),
    ]
    cenarios = []
    for c in CEN:
        if c["tipo"] == "reconstruído":
            xf_h, d0 = trilha(c["inicio"], "x_fx")
            xb_h, _ = trilha(c["inicio"], "x_btc")
            seg_f, seg_b = xf_h, xb_h
        else:
            paths = [trilha_fx_longa(a)[0] for a in c["analogos"]]
            seg_f = np.mean(paths, axis=0)
            seg_b = np.zeros(H_MAX)
            d0 = None
        mf, kf, fundo_f, fim_f = ate_o_fundo(seg_f)
        if c["tipo"] == "reconstruído":
            mb, kb, fundo_b, fim_b = ate_o_fundo(seg_b)
            vol_f = float(np.std(xf_h))  # volatilidade realizada nos 252 dias do episódio
            vol_b = float(np.std(xb_h))
            rho_ep = float(np.corrcoef(xf_h[:max(kf, kb, 63)], xb_h[:max(kf, kb, 63)])[0, 1])
        else:
            mb, kb, fundo_b, fim_b = np.zeros(H_MAX), 0, 0.0, 0.0
            vol_f = float(np.mean([np.std(p) for p in paths]))
            vol_b = float(np.sqrt(gb.var_alvo))
            rho_ep = rho_250
        rho_c = max(rho_ep, rho_stress)
        a1, a2 = inovacoes(N, H_MAX, rho_c, NU_C_STRESS, gf.nu, gb.nu, rng)
        cf_ = (mf + vol_f * a1).cumsum(axis=1)
        cb_ = (mb + vol_b * a2).cumsum(axis=1)
        lvc = niveis(cf_, cb_, s0f, s0b)
        reg = {}
        if c["tipo"] == "reconstruído":
            i0 = idx.get_indexer([pd.Timestamp(c["inicio"])], method="bfill")[0]
            for hd, hp in HORIZ_PASSOS.items():
                f0, f1 = df["fx"].iloc[i0], df["fx"].iloc[i0 + hp]
                b0, b1 = df["btc"].iloc[i0], df["btc"].iloc[i0 + hp]
                reg[str(hd)] = {"usdbrl": f1 / f0 - 1, "btcusd": b1 / b0 - 1, "btcbrl": (f1 * b1) / (f0 * b0) - 1}
        cenarios.append({
            **{k: v for k, v in c.items()},
            "data_inicio_real": str(d0.date()) if d0 is not None else None,
            "premissas": {
                "deriva": "trajetória histórica dia a dia até o pior ponto em 365 dias; depois, deriva zero (a recuperação não é assumida)",
                "vol_anual_fx": vol_f * np.sqrt(252), "vol_anual_btc": vol_b * np.sqrt(252),
                "rho_episodio": rho_ep, "rho_usado": rho_c, "nu_copula": NU_C_STRESS,
                "dias_ate_pior_fx": kf + 1, "dias_ate_pior_btc": kb + 1,
                "choque_fx_pct": float(np.exp(-fundo_f) - 1), "choque_btc_pct": float(np.exp(fundo_b) - 1),
            },
            "historico_real_pct": reg,
            "ativos": {a: {"horizontes": resumo_dist(a, lvc[a], spot[a]),
                           "leque": leque(a, lvc[a], spot[a], passo=6),
                           "drawdown": drawdowns(a, lvc[a], spot[a])} for a in ATIVOS},
        })
    # gatilhos observados em cada episódio (o que aconteceu de fato)
    for c in cenarios:
        c["gatilhos_episodio"] = gatilhos_episodio(c) if c["tipo"] == "reconstruído" else None
    # severidade: pior P50 de drawdown em 365 dias entre os três ativos
    for c in cenarios:
        c["severidade"] = max(c["ativos"][a]["drawdown"]["365"]["P50"] for a in ATIVOS)
    cenarios.sort(key=lambda c: -c["severidade"])

    # ---------- contenção dos choques reais pelos estresses (validação cruzada) ----------
    # Para cada choque real, o realizado em cada horizonte cabe no P5 de algum
    # cenário que NÃO foi construído com aquele episódio?
    PROPRIO = {"2020-02-14": {"covid2020"}, "2021-11-10": {"cripto2022"}, "2024-09-30": {"fiscal2627"}}
    contencao = []
    for o, nm in [("2020-02-14", "Covid"), ("2021-11-10", "Inverno cripto"), ("2024-09-30", "Pacote fiscal de 2024")]:
        i0 = idx.get_indexer([pd.Timestamp(o)], method="ffill")[0]
        linha = {"choque": nm, "origem": o, "celulas": {}}
        for a in ATIVOS:
            linha["celulas"][a] = {}
            for hd, hp in HORIZ_PASSOS.items():
                if i0 + hp >= len(idx):
                    continue
                f0, f1 = df["fx"].iloc[i0], df["fx"].iloc[i0 + hp]
                b0, b1 = df["btc"].iloc[i0], df["btc"].iloc[i0 + hp]
                real = {"usdbrl": f1 / f0 - 1, "btcusd": b1 / b0 - 1, "btcbrl": f1 * b1 / (f0 * b0) - 1}[a]
                cobre = []
                for c in cenarios:
                    if c["id"] in PROPRIO[o]:
                        continue
                    p5 = c["ativos"][a]["horizontes"][str(hd)]["P5"]["var_pct"]
                    if (a == "usdbrl" and p5 >= real) or (a != "usdbrl" and p5 <= real):
                        cobre.append(c["id"])
                linha["celulas"][a][str(hd)] = {"real_pct": float(real), "contido_por": cobre}
        contencao.append(linha)

    # ---------- gatilhos ----------
    gat = gatilhos(cenarios)

    # ---------- histórico recente para os gráficos ----------
    hist = df[df.index >= data_base - pd.Timedelta(days=400)]
    historico = [{"t": str(i.date()), "usdbrl": float(v.fx), "btcusd": float(v.btc), "btcbrl": float(v.fx * v.btc)}
                 for i, v in hist.iterrows()]

    bt = json.loads((RAIZ / "data" / "processed" / f"backtest_{CONFIG_BACKTEST}.json").read_text())
    from relatorio import celulas
    reg_bt = pd.DataFrame(bt["registros"])
    def cel_json(c):
        return [{"ativo": a, "h": h, **v} for (a, h), v in c.items()]
    bt_out = {"config": bt["config"], "gerado_em": bt["gerado_em"], "resumo": bt["resumo"],
              "cortes": {k: {kk: vv for kk, vv in v.items() if kk not in ("crise_fx", "crise_btc")} for k, v in bt["cortes"].items()},
              "agregado": cel_json(celulas(reg_bt)),
              "por_corte": {c: cel_json(celulas(reg_bt, c)) for c in ("2018", "2021")},
              "choques": choques_backtest(bt)}

    datas_futuras = pd.bdate_range(data_base + pd.Timedelta(days=1), periods=H_MAX)
    proj = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_base": str(data_base.date()),
        "aviso": "Estudo de risco. Não é recomendação de investimento.",
        "spot": spot,
        "horizontes": HORIZ_DIAS,
        "passos": HORIZ_PASSOS,
        "datas_passos": [str(d.date()) for d in datas_futuras],
        "convencao": "P10, P5 e P1 são quantis na direção ruim: para USD/BRL, dólar mais caro (percentis 90, 95 e 99); para BTC/USD e BTC/BRL, preço mais baixo (percentis 10, 5 e 1). P90f é o lado favorável, só como referência.",
        "modelo": {
            "fx": gf.params(), "btc": gb.params(), "crise_fx": {k: v for k, v in cf.items() if k != "episodios"},
            "crise_btc": {k: v for k, v in cb.items() if k != "episodios"},
            "rho_250d": rho_250, "rho_estresse_p95_63d": rho_stress, "nu_copula": nu_c,
            "nu_copula_estresse": NU_C_STRESS, "n_trajetorias": N, "semente": SEED,
            "amostra_fx": [str(xfx.index[0].date()), str(xfx.index[-1].date())],
            "amostra_btc": [str(r.index[0].date()), str(r.index[-1].date())],
            "prob_riskoff_conjunto_365d": conj,
            "variante": CONFIG_BACKTEST, "variante_nome": CFG["nome"],
            "recal": {a: {str(h): v for h, v in recal[a].items()} for a in recal} if recal else None,
        },
        "base": base,
        "cenarios": cenarios,
        "gatilhos": gat,
        "contencao_estresses": contencao,
        "ancoras_historicas": ancoras(df, fx_long[CFG["fx_ini"]:]),
        "historico": historico,
        "backtest": bt_out,
        "fontes": [meta_serie(n) for n in ["usdbrl_ptax", "btc_binance", "btc_coinbase_fred", "btc_coingecko_spot",
                                           "selic_meta", "ipca_12m", "focus_anuais", "focus_ipca12m",
                                           "tesouro_direto", "dbgg_pib", "primario_12m_pib", "fluxo_cambial",
                                           "dolar_amplo", "fed_funds", "vix"]],
    }
    cg = json.loads((RAW / "btc_coingecko_spot.json").read_text())["dados"][0]
    proj["conferencia_spot"] = {"coingecko_btcusd": cg[1], "coingecko_btcbrl": cg[2], "coingecko_hora": cg[0],
                                "diferenca_pct_btcusd": cg[1] / s0b - 1}
    out = RAIZ / "projections.json"
    out.write_text(json.dumps(proj, ensure_ascii=False, default=float, separators=(",", ":")))
    print(f"ok: {out} ({out.stat().st_size/1e3:.0f} kB)")


def b(v, d=1):
    """Número em formato brasileiro (vírgula decimal)."""
    return f"{v:.{d}f}".replace(".", ",")


def bs(v, d=1):
    return ("+" if v > 0 else "−" if v < 0 else "") + b(abs(v), d)


def ancoras(df, fx):
    """Pior variação histórica observada em cada horizonte, na direção ruim:
    âncora para julgar se o P1 é plausível. Câmbio desde o início da amostra;
    BTC desde 26/01/2015."""
    series = {"usdbrl": fx, "btcusd": df["btc"], "btcbrl": df["btc"] * df["fx"]}
    out = {}
    for a, s in series.items():
        out[a] = {}
        for h, hp in HORIZ_PASSOS.items():
            ch = (s.shift(-hp) / s - 1).dropna()
            i = ch.idxmax() if a == "usdbrl" else ch.idxmin()
            out[a][str(h)] = {"var_pct": float(ch[i]), "inicio": str(i.date()),
                              "fim": str(s.index[s.index.get_loc(i) + hp].date()), "desde": str(s.index[0].date())}
    return out


def ultimo(s, ate=None):
    s = s.dropna()
    if ate is not None:
        s = s[:ate]
    return float(s.iloc[-1]), str(s.index[-1].date())


def gatilhos(cenarios):
    hoje = pd.Timestamp.today().normalize()
    selic, _ = serie("selic_meta")
    ipca12, _ = serie("focus_ipca12m")
    dbgg, _ = serie("dbgg_pib")
    prim, _ = serie("primario_12m_pib")
    flx, _ = serie("fluxo_cambial")
    dxy, _ = serie("dolar_amplo")
    ff, _ = serie("fed_funds")
    vix, _ = serie("vix")
    td = json.loads(arquivo_ou_resumo("tesouro_direto", "tesouro_resumo").read_text())["dados"]
    focus = pd.DataFrame(json.loads(arquivo_ou_resumo("focus_anuais", "focus_resumo").read_text())["dados"])
    ano = hoje.year
    fult = focus[focus.Data == focus.Data.max()]

    def fv(ind, ref):
        v = fult[(fult.Indicador == ind) & (fult.DataReferencia == str(ref))]
        return float(v.Mediana.iloc[0]) if len(v) else None

    selic_v, selic_d = ultimo(selic, hoje)
    ipca_v, ipca_d = ultimo(ipca12)
    selic_real = (1 + selic_v / 100) / (1 + ipca_v / 100) - 1
    ntnb = [r for r in td if r[1] == "Tesouro IPCA+"]
    ult_d = max(r[0] for r in ntnb)
    ntnb_ult = sorted([r for r in ntnb if r[0] == ult_d], key=lambda r: r[2])
    ntnb_10 = min(ntnb_ult, key=lambda r: abs(pd.Timestamp(r[2]).year - (pd.Timestamp(ult_d).year + 10)))
    pre = sorted([r for r in td if r[1] == "Tesouro Prefixado" and r[0] == ult_d], key=lambda r: r[2])
    dbgg_v, dbgg_d = ultimo(dbgg)
    dbgg_12 = float(dbgg[:pd.Timestamp(dbgg_d) - pd.DateOffset(months=12)].iloc[-1])
    prim_v, prim_d = ultimo(prim)
    dxy_v, dxy_d = ultimo(dxy)
    dxy_3m = dxy_v / float(dxy[:pd.Timestamp(dxy_d) - pd.DateOffset(months=3)].iloc[-1]) - 1
    dxy_pct = float((dxy.pct_change(63).dropna() < dxy_3m).mean())
    f21 = float(flx.iloc[-21:].sum())
    f63 = float(flx.iloc[-63:].sum())
    fano = float(flx[str(hoje.year)].sum())
    f63_hist = flx.rolling(63).sum().dropna()
    f63_pct = float((f63_hist < f63).mean())
    vix_v, vix_d = ultimo(vix)
    ff_v, ff_d = ultimo(ff)
    # halving: bloco 840.000 em 20/04/2024; próximo no bloco 1.050.000, ~10 min por bloco
    halv = date(2024, 4, 20) + pd.Timedelta(minutes=10 * 210000)
    dias_halv = (pd.Timestamp(halv) - hoje).days

    def st(cond_alerta, cond_atencao):
        return "alerta" if cond_alerta else ("atencao" if cond_atencao else "normal")

    g = [
        {"id": "fiscal", "nome": "Risco fiscal",
         "leitura": f"Dívida bruta em {b(dbgg_v, 1)}% do PIB ({bs(dbgg_v - dbgg_12, 1)} p.p. em 12 meses); déficit primário de {b(prim_v, 2)}% do PIB em 12 meses; Focus projeta dívida de {b(fv('Dívida bruta do governo geral', ano + 1), 1)}% em {ano + 1}.",
         "valores": {"dbgg_pib": dbgg_v, "dbgg_var_12m_pp": dbgg_v - dbgg_12, "deficit_primario_12m_pib": prim_v,
                     "focus_dbgg_prox_ano": fv("Dívida bruta do governo geral", ano + 1),
                     "focus_primario_prox_ano": fv("Resultado primário", ano + 1)},
         "regra": "Alerta se a dívida bruta sobe mais de 3 p.p. em 12 meses; atenção acima de 1,5 p.p.",
         "status": st(dbgg_v - dbgg_12 > 3, dbgg_v - dbgg_12 > 1.5),
         "datas": {"dbgg": dbgg_d, "primario": prim_d, "focus": str(fult.Data.max())},
         "fonte": "BCB/SGS 13762 e 5793; BCB/Focus"},
        {"id": "selic_real", "nome": "Selic real",
         "leitura": f"Selic de {b(selic_v, 2)}% e IPCA esperado de {b(ipca_v, 2)}% em 12 meses: juro real ex-ante de {b(100 * selic_real, 1)}%. NTN-B de ~10 anos ({ntnb_10[2][:4]}) paga IPCA + {b(ntnb_10[3], 2)}%.",
         "valores": {"selic_meta": selic_v, "ipca_esperado_12m": ipca_v, "selic_real_ex_ante": 100 * selic_real,
                     "ntnb_10a": ntnb_10[3], "ntnb_vencimento": ntnb_10[2],
                     "prefixados": [{"vencimento": r[2], "taxa": r[3]} for r in pre]},
         "regra": "Juro real alto sustenta o real (carrego). Alerta se cair abaixo de 4%; atenção abaixo de 6%. NTN-B acima de 7% sinaliza prêmio de risco fiscal elevado (atenção).",
         "status": st(100 * selic_real < 4, 100 * selic_real < 6 or ntnb_10[3] > 7),
         "datas": {"selic": selic_d, "focus_ipca12m": ipca_d, "tesouro": ult_d},
         "fonte": "BCB/SGS 432; BCB/Focus; Tesouro Transparente"},
        {"id": "dxy", "nome": "Dólar global",
         "leitura": f"Índice amplo do dólar (FRED, proxy público do DXY) em {b(dxy_v, 1)}, {bs(100 * dxy_3m, 1)}% em 3 meses (percentil {b(100 * dxy_pct, 0)} do histórico). Fed Funds em {b(ff_v, 2)}%.",
         "valores": {"indice": dxy_v, "var_3m": dxy_3m, "percentil_var_3m": dxy_pct, "fed_funds": ff_v},
         "regra": "Alerta se o dólar global sobe mais de 4% em 3 meses; atenção acima de 2%.",
         "status": st(dxy_3m > .04, dxy_3m > .02),
         "datas": {"indice": dxy_d, "fed_funds": ff_d},
         "fonte": "FRED DTWEXBGS e DFF. O DXY da ICE não é público no FRED; usamos o índice amplo do Fed"},
        {"id": "fluxo", "nome": "Fluxo cambial",
         "leitura": f"Saldo de US$ {bs(f21 / 1000, 1)} bi em 21 dias úteis e US$ {bs(f63 / 1000, 1)} bi em 63 (percentil {b(100 * f63_pct, 0)}); no ano, US$ {bs(fano / 1000, 1)} bi.",
         "valores": {"soma_21d_musd": f21, "soma_63d_musd": f63, "ano_musd": fano, "percentil_63d": f63_pct},
         "regra": "Alerta se a saída em 63 dias úteis estiver entre as 10% piores da história; atenção entre as 25% piores.",
         "status": st(f63_pct < .10, f63_pct < .25),
         "datas": {"fluxo": str(flx.index[-1].date())},
         "fonte": "BCB/SGS 13961 (fluxo cambial contratado, total)"},
        {"id": "riskoff", "nome": "Aversão a risco global",
         "leitura": f"VIX em {b(vix_v, 1)}.",
         "valores": {"vix": vix_v},
         "regra": "Alerta acima de 30; atenção acima de 20.",
         "status": st(vix_v > 30, vix_v > 20),
         "datas": {"vix": vix_d}, "fonte": "FRED VIXCLS"},
        {"id": "halving", "nome": "Halving do BTC",
         "leitura": f"Próximo halving estimado para {halv.strftime('%m/%Y')} (~{dias_halv} dias), fora dos 365 dias projetados.",
         "valores": {"data_estimada": str(halv), "dias": dias_halv},
         "regra": "Inferência: bloco 1.050.000 a 10 minutos por bloco desde o halving de 20/04/2024. Não entra no modelo; historicamente, o ciclo pós-halving não é garantia de alta.",
         "status": "normal", "datas": {}, "fonte": "Cálculo próprio (inferência), sem série externa"},
        {"id": "etf", "nome": "Fluxo de ETFs de BTC",
         "leitura": "Sem dado: nenhuma das fontes autorizadas publica o fluxo diário dos ETFs à vista.",
         "valores": {}, "regra": "Não monitorado quantitativamente até haver fonte pública autorizada.",
         "status": "sem_dado", "datas": {}, "fonte": "nenhuma fonte autorizada publica a série"},
    ]
    return g


def gatilhos_episodio(c):
    """Valores dos gatilhos no início e durante a fase de choque do episódio."""
    ini = pd.Timestamp(c["data_inicio_real"])
    dias = max(c["premissas"]["dias_ate_pior_fx"], c["premissas"]["dias_ate_pior_btc"], 21)
    fim = pd.bdate_range(ini, periods=dias + 1)[-1]
    selic, _ = serie("selic_meta")
    ipca12, _ = serie("focus_ipca12m")
    dbgg, _ = serie("dbgg_pib")
    dxy, _ = serie("dolar_amplo")
    vix, _ = serie("vix")
    flx, _ = serie("fluxo_cambial")
    sv = float(selic[:ini].iloc[-1])
    iv = float(ipca12[:ini].iloc[-1]) if len(ipca12[:ini]) else None
    d1 = float(dbgg[:ini].iloc[-1])
    d0 = float(dbgg[:ini - pd.DateOffset(months=12)].iloc[-1])
    dx0, dx1 = float(dxy[:ini].iloc[-1]), float(dxy[:fim].iloc[-1])
    return {
        "inicio": str(ini.date()), "fim_choque": str(fim.date()),
        "selic_real": 100 * ((1 + sv / 100) / (1 + iv / 100) - 1) if iv is not None else None,
        "dbgg_var_12m_pp": d1 - d0, "dbgg": d1,
        "dxy_var": dx1 / dx0 - 1,
        "vix_inicio": float(vix[:ini].iloc[-1]), "vix_pico": float(vix[ini:fim].max()),
        "fluxo_musd": float(flx[ini:fim].sum()),
    }


def choques_backtest(bt):
    reg = pd.DataFrame(bt["registros"])
    out = []
    nomes = {"2020-02-14": "Covid (origem 14/02/2020)", "2021-11-10": "Inverno cripto (origem 10/11/2021)",
             "2024-09-30": "Pacote fiscal (origem 30/09/2024)"}
    for o, nm in nomes.items():
        s = reg[reg.origem == o]
        if not len(s):
            continue
        out.append({"nome": nm, "origem": o,
                    "pit": {a: {str(int(h)): float(v) for h, v in g.set_index("h").pit.items()}
                            for a, g in s.groupby("ativo")}})
    return out


if __name__ == "__main__":
    main()
