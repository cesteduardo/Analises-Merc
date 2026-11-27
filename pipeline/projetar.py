"""Gera projections.json: distribuição-base, cenários de estresse, drawdowns,
gatilhos monitorados, condições dos episódios e resumo do backtest.

Rodar depois de coletar.py e backtest.py:
    python3 pipeline/coletar.py && python3 pipeline/backtest.py juro_real 0 crise && python3 pipeline/projetar.py
"""
import json, math, sys
from datetime import datetime, timezone, date
from pathlib import Path
import numpy as np
import pandas as pd
from dateutil.easter import easter
sys.path.insert(0, str(Path(__file__).parent))
from nucleo import *

N = 20000
SEED = 20261125
ATIVOS = ["usdbrl", "btcusd", "btcbrl"]
NOMES = {"usdbrl": "USD/BRL", "btcusd": "BTC/USD", "btcbrl": "BTC/BRL"}
QB = {"P50": .50, "P10": .10, "P5": .05, "P1": .01, "P90f": .90}  # na direção ruim (baixo = pior)
CONFIG_BACKTEST = "juro_real_tudo_crise"
NU_C_STRESS = 4.0
JANELA = 63  # dias úteis usados nas comparações "no episódio" e "hoje"


# ---------------------------------------------------------------- utilidades
def feriados_nacionais(anos):
    """Feriados nacionais em que a PTAX não é publicada (conferido contra os dias
    úteis ausentes da série em 2024 e 2025): fixos, Carnaval, Sexta-feira Santa,
    Corpus Christi e, desde 2024, 20 de novembro."""
    out = []
    for y in anos:
        e = pd.Timestamp(easter(y))
        fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
        if y >= 2024:
            fixos.append((11, 20))
        out += [pd.Timestamp(y, m, d) for m, d in fixos]
        out += [e - pd.Timedelta(days=48), e - pd.Timedelta(days=47), e - pd.Timedelta(days=2),
                e + pd.Timedelta(days=60)]
    return out


def meta_serie(nome, data_base):
    """Fonte, URL, coleta e data do último dado observado até a data-base."""
    d = json.loads((RAW / f"{nome}.json").read_text())
    datas = []
    for row in d["dados"]:
        v = row.get("Data") if isinstance(row, dict) else row[0]
        if v:
            datas.append(str(v)[:10])
    ok = [x for x in datas if x <= str(data_base.date())]
    return {"serie": nome, "fonte": d["fonte"], "url": d["url"], "coletado_em": d["coletado_em"],
            "ultimo_dado": max(ok) if ok else None, "primeiro_dado": min(datas) if datas else None,
            "mensal": nome in ("dbgg_pib", "primario_12m_pib", "ipca_12m"),
            "n": len(datas)}


def wilson(p, n, z=1.96):
    if n <= 0:
        return (0.0, 1.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


def classe_calib(p, lo, hi):
    """na_meta: ponto em 8–12% e IC95 com menos de 15 p.p. de largura;
    na_meta_fraca: ponto na faixa, mas IC largo (sem poder estatístico);
    inc_acima / inc_abaixo: ponto fora, mas o IC cruza a faixa;
    acima / abaixo: o IC inteiro fora da faixa."""
    if .08 <= p <= .12:
        return "na_meta" if hi - lo < .15 else "na_meta_fraca"
    if hi >= .08 and lo <= .12:
        return "inc_acima" if p > .12 else "inc_abaixo"
    return "acima" if p > .12 else "abaixo"


def niveis(sf, sb, s0f, s0b):
    """Converte caminhos acumulados (direção ruim) em níveis de preço."""
    fx = s0f * np.exp(-sf)          # x_fx = -dlog(USD/BRL)
    btc = s0b * np.exp(sb)
    return {"usdbrl": fx, "btcusd": btc, "btcbrl": btc * fx}


def ruim(a, lv):
    """Log-nível na direção ruim (baixo = pior) para quantis homogêneos."""
    return -np.log(lv) if a == "usdbrl" else np.log(lv)


def quantis_nivel(a, lv_col):
    """Quantis de preço na direção ruim: para USD/BRL, P10 é o 90º percentil."""
    out = {}
    for k, q in QB.items():
        qq = 1 - q if a == "usdbrl" else q
        out[k] = float(np.quantile(lv_col, qq))
    return out


def resumo_dist(a, lv, s0):
    tab = {}
    for hd, hp in HORIZ_PASSOS.items():
        q = quantis_nivel(a, lv[:, hp - 1])
        tab[str(hd)] = {k: {"nivel": v, "var_pct": v / s0 - 1} for k, v in q.items()}
    return tab


def leque(a, lv, s0, passo=3):
    pts = []
    for t in list(range(0, H_MAX, passo)) + [H_MAX - 1]:
        q = quantis_nivel(a, lv[:, t])
        pts.append({"d": t + 1, **{k: round(v, 6) for k, v in q.items()}})
    return [{"d": 0, **{k: s0 for k in QB}}] + pts


def drawdowns(a, lv, s0):
    """Drawdown máximo na direção ruim até cada horizonte."""
    base = ruim(a, lv) - ruim(a, np.array([s0]))[0]
    dd = drawdown_ate(base, HORIZ_PASSOS)
    return {str(h): {"P50": float(np.quantile(v, .5)), "P10": float(np.quantile(v, .9)),
                     "P5": float(np.quantile(v, .95)), "P1": float(np.quantile(v, .99))}
            for h, v in dd.items()}


def dd_um(c):
    """Drawdown máximo de um único caminho acumulado (direção ruim)."""
    return float(drawdown_max(np.asarray(c, dtype=float)[None, :])[0])


def dd_pico_vale(c):
    """Índices (no caminho com o 0 inicial) do pico e do vale do drawdown máximo."""
    lv = np.concatenate([[0.0], np.asarray(c, dtype=float)])
    j = int(np.argmin(lv - np.maximum.accumulate(lv)))
    return int(np.argmax(lv[:j + 1])), j


def calibrar_estresse(deriva, ruido, alvo, amostra=6000):
    """Ajusta o cenário para que a mediana do drawdown máximo em 365 dias iguale o
    drawdown histórico do episódio, sem dupla contagem.

    Regra 1: a dispersão é a do GARCH-base de hoje (lambda = 1) e a trajetória
    histórica do episódio entra multiplicada por m (bisseção em [0, 1]).
    Regra 2: se a volatilidade de hoje, sozinha, já gera drawdown mediano maior
    que o histórico, a trajetória sai (m = 0) e a dispersão é reduzida
    (bisseção de lambda em [0, 1]).
    Devolve (m, lambda, mediana obtida)."""
    r = ruido[:amostra]

    def med(m, lam):
        return float(np.median(drawdown_max(np.cumsum(m * deriva + lam * r, axis=1))))

    def bis(f, lo, hi):
        for _ in range(30):
            x = (lo + hi) / 2
            lo, hi = (x, hi) if f(x) < alvo else (lo, x)
        return (lo + hi) / 2
    if med(0.0, 1.0) <= alvo:
        m = 1.0 if med(1.0, 1.0) <= alvo else bis(lambda x: med(x, 1.0), 0.0, 1.0)
        return m, 1.0, med(m, 1.0)
    lam = bis(lambda x: med(0.0, x), 0.0, 1.0)
    return 0.0, lam, med(0.0, lam)


def pior_12m(s, ruim_alta):
    """Pior variação de 252 dias úteis da série e o drawdown dentro dela."""
    s = s.dropna()
    v = (s.shift(-252) / s - 1).dropna()
    i = v.idxmax() if ruim_alta else v.idxmin()
    j = s.index.get_loc(i)
    c = np.log(s.iloc[j:j + 253].values / s.iloc[j])
    c = -c if ruim_alta else c
    return {"var_pct": float(v[i]), "inicio": str(i.date()), "fim": str(s.index[j + 252].date()),
            "drawdown_no_periodo": dd_um(c[1:]), "desde": str(s.index[0].date())}


# ---------------------------------------------------------------- principal
def main():
    rng = np.random.default_rng(SEED)
    df = base_diaria()
    r = retornos(df)
    fx_long, _ = serie("usdbrl_ptax")
    xfx_todo = -np.log(fx_long).diff().dropna()   # desde 1999, para os análogos
    xfx = xfx_todo["2003":]
    gf = Garch(xfx.values)
    gb = Garch(r["x_btc"].values)
    cf = estimar_crise(xfx.values, g=gf)
    cb = estimar_crise(r["x_btc"].values, g=gb)
    s2f, vf = gf.filtrar(xfx.values)
    s2b, vb = gb.filtrar(r["x_btc"].values)
    zf = pd.Series(xfx.values / np.sqrt(s2f), index=xfx.index).reindex(r.index)
    zb = pd.Series(r["x_btc"].values / np.sqrt(s2b), index=r.index)
    ok = zf.notna()
    zf, zb = zf[ok], zb[ok]
    rho_250 = float(zf.iloc[-250:].corr(zb.iloc[-250:]))
    roll63 = zf.rolling(63).corr(zb).dropna()
    roll250 = zf.rolling(250).corr(zb).dropna()
    rho_stress = float(roll63.quantile(.95))
    nu_c = ajustar_nu_copula(zf.values, zb.values, float(zf.corr(zb)))

    s0f, s0b = float(df["fx"].iloc[-1]), float(df["btc"].iloc[-1])
    data_base = df.index[-1]

    # ---------- deriva do câmbio condicionada ao juro real ----------
    rr = juro_real_expost(xfx.index)
    reg_jr = ajustar_deriva_juro_real(xfx_todo, juro_real_expost(xfx_todo.index), xfx.index[-1])
    rr_hoje = float(rr.dropna().iloc[-1])
    mu_fx = deriva_juro_real(reg_jr, rr_hoje)
    reg_jr.update({"juro_real_hoje": rr_hoje, "deriva_diaria": mu_fx,
                   "deriva_anual_usdbrl_pct": float(np.exp(-mu_fx * 252) - 1)})

    # ---------- distribuição-base ----------
    e1, e2 = inovacoes(N, H_MAX, rho_250, nu_c, gf.nu, gb.nu, rng)
    sf = simular_com_crise(gf, vf, e1, mu_fx, cf, rng).cumsum(axis=1)
    sb = simular_com_crise(gb, vb, e2, 0.0, cb, rng).cumsum(axis=1)
    # mesmo sorteio sem a camada de crise: mede a deriva adversa que ela acrescenta
    sf0 = simular_garch(gf, vf, e1, mu_fx).cumsum(axis=1)
    sb0 = simular_garch(gb, vb, e2, 0.0).cumsum(axis=1)
    lv = niveis(sf, sb, s0f, s0b)
    lv0 = niveis(sf0, sb0, s0f, s0b)
    # sensibilidade: o mesmo modelo sem a deriva do juro real
    fx_sd = s0f * np.exp(-simular_com_crise(gf, vf, e1, 0.0, cf, np.random.default_rng(SEED + 1)).cumsum(axis=1)[:, -1])
    sem_deriva = {"P50": float(np.quantile(fx_sd, .5)), "P1": float(np.quantile(fx_sd, .99))}
    spot = {"usdbrl": s0f, "btcusd": s0b, "btcbrl": s0f * s0b}
    base = {a: {"horizontes": resumo_dist(a, lv[a], spot[a]), "leque": leque(a, lv[a], spot[a]),
                "drawdown": drawdowns(a, lv[a], spot[a])} for a in ATIVOS}
    efeito_crise = {a: {"mediana_com": float(np.median(lv[a][:, -1]) / spot[a] - 1),
                        "mediana_sem": float(np.median(lv0[a][:, -1]) / spot[a] - 1)} for a in ATIVOS}

    # leitura do pior caso: marginais, conjunta e "tocar no caminho"
    p1f = base["usdbrl"]["horizontes"]["365"]["P1"]["nivel"]
    p1b = base["btcusd"]["horizontes"]["365"]["P1"]["nivel"]
    fim_f, fim_b = lv["usdbrl"][:, -1], lv["btcusd"][:, -1]
    pior = {
        "p1_usdbrl": p1f, "p1_btcusd": p1b,
        "prob_conjunta_p1": float(((fim_f >= p1f) & (fim_b <= p1b)).mean()),
        "prob_toca_p1_usdbrl": float((lv["usdbrl"].max(axis=1) >= p1f).mean()),
        "prob_toca_p1_btcusd": float((lv["btcusd"].min(axis=1) <= p1b).mean()),
        "prob_riskoff_conjunto_365d": float(((fim_f / s0f > 1 / 0.9) & (fim_b / s0b < 0.7)).mean()),
        "usdbrl_sem_deriva": sem_deriva,
        "def_riskoff": "o real perde mais de 10% e o BTC/USD cai mais de 30%, juntos, no fim de 365 dias",
    }

    # ---------- âncoras históricas: piores 12 meses ----------
    btc_al = btc_usd().reindex(fx_long.index, method="ffill")
    btc_al = btc_al[btc_al.index >= "2015-01-26"].dropna()
    bb = (btc_al * fx_long.reindex(btc_al.index)).dropna()
    ancoras = {"usdbrl": pior_12m(fx_long, True), "btcusd": pior_12m(btc_al, False), "btcbrl": pior_12m(bb, False)}

    # ---------- cenários de estresse ----------
    idx = df.index
    xr = r.reindex(idx).fillna(0.0)

    def trilha(ini):
        i0 = idx.get_indexer([pd.Timestamp(ini)], method="bfill")[0]
        return xr["x_fx"].iloc[i0 + 1:i0 + 1 + H_MAX].values, xr["x_btc"].iloc[i0 + 1:i0 + 1 + H_MAX].values, i0

    def trilha_fx_longa(ini):
        i0 = xfx_todo.index.get_indexer([pd.Timestamp(ini)], method="bfill")[0]
        return xfx_todo.iloc[i0 + 1:i0 + 1 + H_MAX].values, xfx_todo.index[i0]

    def ate(x, T):
        """Trajetória histórica dia a dia até o pior ponto conjunto; zero depois."""
        return np.where(np.arange(H_MAX) <= T, x, 0.0)

    CEN = [
        dict(id="covid2020", nome="Covid", periodo="mar/2020", inicio="2020-02-14", tipo="reconstruído",
             resumo="Choque global de liquidez: o real e o bitcoin caem juntos, no mesmo mês."),
        dict(id="fiscal2015", nome="Crise fiscal", periodo="2015", inicio="2015-01-26", tipo="reconstruído",
             resumo="Deterioração fiscal doméstica, perda do grau de investimento e recessão."),
        dict(id="cripto2022", nome="Inverno cripto", periodo="2022", inicio="2021-11-10", tipo="reconstruído",
             resumo="Alta de juros nos EUA, quebras no setor cripto (Terra/Luna, FTX) e BTC em queda longa.",
             qualitativo="Quebras de Terra/Luna, Celsius e FTX: nenhuma série pública autorizada mede isso."),
        dict(id="fiscal2627", nome="Fiscal e eleitoral", periodo="2026–27", inicio=None, tipo="construído",
             analogos=["2002-04-01", "2015-01-02", "2024-09-30"],
             resumo="Hipótese construída: transição pós-eleitoral com dúvida sobre o arcabouço fiscal. O real segue a média de três episódios fiscais; o BTC não tem trajetória própria e só sofre contágio pela correlação piorada."),
    ]
    vol_atual_f, vol_atual_b = math.sqrt(vf * 252), math.sqrt(vb * 252)
    v0f, v0b = max(vf, gf.var_alvo), max(vb, gb.var_alvo)
    vol_ini_f, vol_ini_b = math.sqrt(v0f * 252), math.sqrt(v0b * 252)
    cenarios = []
    for c in CEN:
        if c["tipo"] == "reconstruído":
            xf_h, xb_h, i0 = trilha(c["inicio"])
            d0 = idx[i0]
            cfh, cbh = np.cumsum(xf_h), np.cumsum(xb_h)
            kf, kb = int(np.argmin(cfh)), int(np.argmin(cbh))
            T = max(kf, kb)
            alvo_f, alvo_b = dd_um(cfh), dd_um(cbh)
            # cada ativo segue a própria trajetória até o próprio pior ponto e para:
            # nenhuma recuperação é assumida, nem a de um ativo enquanto o outro ainda cai
            mf, mb = ate(xf_h, kf), ate(xb_h, kb)
            w = max(T + 1, 63)
            rho_ep = float(np.corrcoef(xf_h[:w], xb_h[:w])[0, 1])
            data_pior = str(idx[i0 + 1 + T].date())
        else:
            paths = [trilha_fx_longa(a)[0] for a in c["analogos"]]
            cfh = np.mean([np.cumsum(p) for p in paths], axis=0)
            kf, kb = int(np.argmin(cfh)), None
            T = kf
            alvo_f = float(np.mean([dd_um(np.cumsum(p)) for p in paths]))
            alvo_b = None
            mf, mb = ate(np.mean(paths, axis=0), T), np.zeros(H_MAX)
            rho_ep, d0, data_pior = None, None, None
        rho_c = max(rho_ep if rho_ep is not None else rho_250, rho_stress)
        a1, a2 = inovacoes(N, H_MAX, rho_c, NU_C_STRESS, gf.nu, gb.nu, rng)
        # ruído-base, sem camada de crise, partindo de pelo menos a volatilidade de longo prazo
        nf = simular_garch(gf, v0f, a1, 0.0)
        nb = simular_garch(gb, v0b, a2, 0.0)
        m_f, lam_f, med_f = calibrar_estresse(mf, nf, alvo_f)
        if alvo_b is not None:
            m_b, lam_b, med_b = calibrar_estresse(mb, nb, alvo_b)
        else:
            m_b, lam_b, med_b = 0.0, 1.0, None
        lvc = niveis(np.cumsum(m_f * mf + lam_f * nf, axis=1), np.cumsum(m_b * mb + lam_b * nb, axis=1), s0f, s0b)
        reg = {}
        if c["tipo"] == "reconstruído":
            for hd, hp in HORIZ_PASSOS.items():
                f0, f1 = df["fx"].iloc[i0], df["fx"].iloc[i0 + hp]
                b0, b1 = df["btc"].iloc[i0], df["btc"].iloc[i0 + hp]
                reg[str(hd)] = {"usdbrl": f1 / f0 - 1, "btcusd": b1 / b0 - 1, "btcbrl": (f1 * b1) / (f0 * b0) - 1}
            cbb = np.cumsum(xb_h - xf_h)   # log de BTC/BRL observado
            kbb = int(np.argmin(cbb))
            uf, ub = float(np.exp(-cfh[kf]) - 1), float(np.exp(cbh[kb]) - 1)
            no_pior = {"usdbrl": uf, "btcusd": ub, "btcbrl": (1 + uf) * (1 + ub) - 1}
            pior_obs = {"usdbrl": {"pct": uf, "data": str(idx[i0 + 1 + kf].date()), "dia": kf + 1},
                        "btcusd": {"pct": ub, "data": str(idx[i0 + 1 + kb].date()), "dia": kb + 1},
                        "btcbrl": {"pct": float(np.exp(cbb[kbb]) - 1), "data": str(idx[i0 + 1 + kbb].date()), "dia": kbb + 1}}
            dd_hist = {"usdbrl": alvo_f, "btcusd": alvo_b, "btcbrl": dd_um(cbb)}
            # quando a queda desde o pico (alvo) não coincide com o pior nível contra o início
            dd_dt = {}
            for a_, cam, kst in (("usdbrl", cfh, kf), ("btcusd", cbh, kb), ("btcbrl", cbb, None)):
                ip, iv = dd_pico_vale(cam)
                dd_dt[a_] = {"pico": str(idx[i0 + ip].date()), "vale": str(idx[i0 + iv].date()),
                             "depois_da_parada": bool(kst is not None and iv > kst + 1)}
        else:
            dd_dt = None
            no_pior = {"usdbrl": float(np.exp(-cfh[T]) - 1), "btcusd": 0.0, "btcbrl": float(np.exp(cfh[T]) - 1)}
            pior_obs = None
            dd_hist = {"usdbrl": alvo_f, "btcusd": None, "btcbrl": None}
        cenarios.append({
            **c,
            "data_inicio_real": str(d0.date()) if d0 is not None else None,
            "premissas": {
                "dias_ate_pior": T + 1, "data_pior": data_pior,
                "dias_ate_pior_fx": kf + 1, "dias_ate_pior_btc": (kb + 1) if kb is not None else None,
                "choque_no_pior_pct": no_pior, "pior_observado": pior_obs,
                "drawdown_historico": dd_hist, "drawdown_datas": dd_dt,
                "drawdown_mediano_obtido": {"usdbrl": med_f, "btcusd": med_b},
                "lambda_fx": lam_f, "lambda_btc": lam_b, "m_fx": m_f, "m_btc": m_b,
                "tendencia_aplicada_pct": {"usdbrl": float(np.exp(-m_f * mf.sum()) - 1), "btcusd": float(np.exp(m_b * mb.sum()) - 1)},
                "vol_anual_fx": lam_f * vol_ini_f, "vol_anual_btc": lam_b * vol_ini_b,
                "vol_atual_fx": vol_atual_f, "vol_atual_btc": vol_atual_b,
                "vol_inicial_fx": vol_ini_f, "vol_inicial_btc": vol_ini_b,
                "rho_episodio": rho_ep, "rho_usado": rho_c, "rho_p95_63d": rho_stress, "rho_hoje": rho_250,
                "nu_copula": NU_C_STRESS, "camada_crise": False,
                "pesos_analogos": [1 / 3] * 3 if c["tipo"] == "construído" else None,
            },
            "historico_real_pct": reg,
            "ativos": {a: {"horizontes": resumo_dist(a, lvc[a], spot[a]),
                           "leque": leque(a, lvc[a], spot[a], passo=6),
                           "drawdown": drawdowns(a, lvc[a], spot[a])} for a in ATIVOS},
        })
    for c in cenarios:
        c["severidade"] = {a: c["ativos"][a]["drawdown"]["365"]["P50"] for a in ATIVOS}
    cenarios.sort(key=lambda c: -max(c["severidade"].values()))

    # ---------- gatilhos e condições ----------
    ctx = Contexto(data_base)
    gat = gatilhos(ctx, data_base)
    for c in cenarios:
        c["condicoes"] = condicoes_cenario(ctx, c, data_base)

    # ---------- referências para a mediana do câmbio ----------
    selic_v = ctx.ultimo("selic", data_base)[0]
    ff_v = ctx.ultimo("ff", data_base)[0]
    ano = data_base.year
    referencias = {
        "forward_1a_usdbrl": s0f * (1 + selic_v / 100) / (1 + ff_v / 100),
        "selic": selic_v, "fed_funds": ff_v,
        "focus_cambio": {str(ano): ctx.focus("Câmbio", ano), str(ano + 1): ctx.focus("Câmbio", ano + 1)},
        "focus_data": ctx.focus_data,
        "mediana_365_usdbrl": base["usdbrl"]["horizontes"]["365"]["P50"]["nivel"],
    }

    # ---------- histórico recente e correlação móvel ----------
    hist = df[df.index >= data_base - pd.Timedelta(days=400)]
    historico = [{"t": str(i.date()), "usdbrl": float(v.fx), "btcusd": float(v.btc), "btcbrl": float(v.fx * v.btc)}
                 for i, v in hist.iterrows()]
    cr = pd.DataFrame({"r63": roll63, "r250": roll250}).dropna()
    cr = cr[cr.index >= "2016-06-01"].iloc[::-5].iloc[::-1]
    correlacao = {"serie": [{"t": str(i.date()), "r63": round(float(v.r63), 4), "r250": round(float(v.r250), 4)}
                            for i, v in cr.iterrows()],
                  "p95_63d": rho_stress, "hoje_250d": rho_250, "hoje_63d": float(roll63.iloc[-1])}

    # ---------- backtest ----------
    bt = json.loads((RAIZ / "data" / "processed" / f"backtest_{CONFIG_BACKTEST}.json").read_text())
    bt_out = {"config": bt["config"], "gerado_em": bt["gerado_em"], "cortes": bt["cortes"],
              "resumo": resumo_backtest(bt["resumo"]), "choques": choques_backtest(bt)}

    fer = feriados_nacionais(range(data_base.year, data_base.year + 3))
    datas_futuras = pd.bdate_range(data_base + pd.Timedelta(days=1), periods=H_MAX + 30, freq="C", holidays=fer)[:H_MAX]
    proj = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_base": str(data_base.date()),
        "aviso": "Estudo de risco. Não é recomendação de investimento.",
        "spot": spot,
        "horizontes": HORIZ_DIAS,
        "passos": HORIZ_PASSOS,
        "datas_passos": [str(d.date()) for d in datas_futuras],
        "calendario": "dias úteis da PTAX: sem fins de semana e feriados nacionais",
        "convencao": "P10, P5 e P1 são quantis na direção ruim: para USD/BRL, dólar mais caro (percentis 90, 95 e 99); para BTC/USD e BTC/BRL, preço mais baixo (percentis 10, 5 e 1). P90f é o lado favorável, só como referência.",
        "modelo": {
            "fx": gf.params(), "btc": gb.params(), "crise_fx": {k: v for k, v in cf.items() if k != "episodios"},
            "crise_btc": {k: v for k, v in cb.items() if k != "episodios"},
            "deriva_fx": reg_jr, "efeito_crise": efeito_crise,
            "vol_atual": {"usdbrl": vol_atual_f, "btcusd": vol_atual_b},
            "vol_longo_prazo": {"usdbrl": math.sqrt(gf.var_alvo * 252), "btcusd": math.sqrt(gb.var_alvo * 252)},
            "rho_250d": rho_250, "rho_estresse_p95_63d": rho_stress, "nu_copula": nu_c,
            "nu_copula_estresse": NU_C_STRESS, "n_trajetorias": N, "semente": SEED,
            "amostra_fx": [str(xfx.index[0].date()), str(xfx.index[-1].date())],
            "amostra_btc": [str(r.index[0].date()), str(r.index[-1].date())],
            "prob_riskoff_conjunto_365d": pior["prob_riskoff_conjunto_365d"],
        },
        "pior_caso": pior,
        "ancoras": ancoras,
        "referencias": referencias,
        "base": base,
        "cenarios": cenarios,
        "gatilhos": gat,
        "historico": historico,
        "correlacao": correlacao,
        "backtest": bt_out,
        "fontes": [meta_serie(n, data_base) for n in
                   ["usdbrl_ptax", "btc_binance", "btc_coinbase_fred", "btc_coingecko_spot",
                    "selic_meta", "ipca_12m", "focus_anuais", "focus_ipca12m",
                    "tesouro_direto", "dbgg_pib", "primario_12m_pib", "fluxo_cambial",
                    "dolar_amplo", "fed_funds", "vix"]],
    }
    for f in proj["fontes"]:
        assert f["ultimo_dado"] is None or f["ultimo_dado"] <= proj["data_base"], f
    cg = json.loads((RAW / "btc_coingecko_spot.json").read_text())["dados"][0]
    proj["conferencia_spot"] = {"coingecko_btcusd": cg[1], "coingecko_btcbrl": cg[2], "coingecko_hora": cg[0],
                                "diferenca_pct_btcusd": cg[1] / s0b - 1}
    out = RAIZ / "projections.json"
    out.write_text(json.dumps(proj, ensure_ascii=False, default=float, separators=(",", ":")))
    print(f"ok: {out} ({out.stat().st_size/1e3:.0f} kB)")
    for c in cenarios:
        p = c["premissas"]
        print(f"{c['id']:11s} T*={p['dias_ate_pior']:3d} m={p['m_fx']:.2f}/{p['m_btc']:.2f} λ={p['lambda_fx']:.2f}/{p['lambda_btc']:.2f} "
              f"dd_hist={ {k: round(v, 3) if v else v for k, v in p['drawdown_historico'].items()} } "
              f"dd_med={ {a: round(c['ativos'][a]['drawdown']['365']['P50'], 3) for a in ATIVOS} }")


# ---------------------------------------------------------------- dados dos gatilhos
class Contexto:
    """Séries usadas nos gatilhos e nas condições dos episódios, cortadas na data-base."""

    def __init__(self, data_base):
        self.db = data_base
        nomes = {"selic": "selic_meta", "ipca_e": "focus_ipca12m", "ipca_r": "ipca_12m", "dbgg": "dbgg_pib",
                 "prim": "primario_12m_pib", "flx": "fluxo_cambial", "dxy": "dolar_amplo", "ff": "fed_funds",
                 "vix": "vix"}
        self.s = {k: serie(v)[0][:data_base] for k, v in nomes.items()}
        td = json.loads((RAW / "tesouro_direto.json").read_text())["dados"]
        t = pd.DataFrame(td, columns=["data", "tipo", "venc", "taxa"])
        t["data"] = pd.to_datetime(t["data"])
        t["venc"] = pd.to_datetime(t["venc"])
        self.td = t[t.data <= data_base]
        f = pd.DataFrame(json.loads((RAW / "focus_anuais.json").read_text())["dados"])
        f = f[f.Data <= str(data_base.date())]
        self.focus_data = str(f.Data.max())
        self.focus_ult = f[f.Data == f.Data.max()]
        self.flx63 = self.s["flx"].rolling(JANELA).sum().dropna()

    def ultimo(self, k, ate):
        s = self.s[k].dropna()[:ate]
        return (float(s.iloc[-1]), str(s.index[-1].date())) if len(s) else (None, None)

    def focus(self, ind, ref):
        v = self.focus_ult[(self.focus_ult.Indicador == ind) & (self.focus_ult.DataReferencia == str(ref))]
        return float(v.Mediana.iloc[0]) if len(v) else None

    def ntnb(self, ate):
        """Taxa do Tesouro IPCA+ (sem cupom) com vencimento mais próximo de 10 anos."""
        t = self.td[(self.td.tipo == "Tesouro IPCA+") & (self.td.data <= pd.Timestamp(ate))]
        if not len(t):
            return None
        d = t.data.max()
        t = t[t.data == d]
        anos = (t.venc - d).dt.days / 365.25
        i = (anos - 10).abs().idxmin()
        return {"taxa": float(t.taxa[i]), "vencimento": str(t.venc[i].date()), "anos": float(anos[i]),
                "data": str(d.date())}


def fmt(v, casas=1, sinal=False):
    s = f"{v:.{casas}f}"
    if sinal and float(s) != 0:
        s = f"{v:+.{casas}f}"
    s = s.lstrip("-") if float(s) == 0 else s
    return s.replace("-", "−").replace(".", ",")


# Regras de status dos gatilhos, usadas tanto para hoje quanto para os episódios.
REGRAS = {
    "fiscal": dict(nome="Dívida bruta, variação em 12 meses", un="p.p.", dir=+1, alerta=3.0, atencao=1.5,
                   fonte="BCB/SGS 13762"),
    "selic_real": dict(nome="Selic real ex-ante", un="%", dir=-1, alerta=4.0, atencao=6.0,
                       fonte="BCB/SGS 432 e Focus IPCA 12 meses"),
    "ntnb": dict(nome="Tesouro IPCA+ de ~10 anos", un="% + IPCA", dir=+1, alerta=7.5, atencao=6.5,
                 fonte="Tesouro Transparente (Tesouro IPCA+)"),
    "dxy": dict(nome="Dólar global em 63 dias úteis", un="%", dir=+1, alerta=4.0, atencao=2.0,
                fonte="FRED DTWEXBGS"),
    "fluxo": dict(nome="Fluxo cambial em 63 dias úteis, percentil", un="pct", dir=-1, alerta=10.0, atencao=25.0,
                  fonte="BCB/SGS 13961"),
    "riskoff": dict(nome="VIX (pico na janela)", un="", dir=+1, alerta=30.0, atencao=20.0, fonte="FRED VIXCLS"),
    "fed": dict(nome="Fed Funds, variação em 12 meses", un="p.p.", dir=+1, alerta=2.0, atencao=1.0,
                fonte="FRED DFF"),
}


def status_de(k, v):
    if v is None:
        return "sem_dado"
    R = REGRAS[k]
    if R["dir"] > 0:
        return "alerta" if v > R["alerta"] else ("atencao" if v > R["atencao"] else "normal")
    return "alerta" if v < R["alerta"] else ("atencao" if v < R["atencao"] else "normal")


def valores_em(ctx, t0, modo):
    """Valor de cada condição. modo='hoje': janelas que terminam em t0.
    modo='episodio': janelas de 63 dias úteis (12 meses para o Fed) que começam em t0."""
    t0 = pd.Timestamp(t0)
    b = pd.tseries.offsets.BDay
    if modo == "hoje":
        a, z = t0 - b(JANELA), t0
        fa, fz = t0 - pd.DateOffset(months=12), t0
    else:
        a, z = t0, t0 + b(JANELA)
        fa, fz = t0, t0 + pd.DateOffset(months=12)
    S = ctx.s
    v = {}
    db = S["dbgg"]
    ult = db[:t0].index[-1] if len(db[:t0]) else None
    if ult is not None and len(db[:ult - pd.DateOffset(months=12)]):
        v["fiscal"] = float(db[ult] - db[:ult - pd.DateOffset(months=12)].iloc[-1])
    else:
        v["fiscal"] = None
    sv, ie, ir = S["selic"][:t0], S["ipca_e"][:t0], S["ipca_r"][:t0]
    if len(sv) and len(ie) and ie.index[-1] > t0 - pd.Timedelta(days=40):
        v["selic_real"] = float(100 * ((1 + sv.iloc[-1] / 100) / (1 + ie.iloc[-1] / 100) - 1))
        v["selic_real_tipo"] = "ex-ante"
    elif len(sv) and len(ir):
        v["selic_real"] = float(100 * ((1 + sv.iloc[-1] / 100) / (1 + ir.iloc[-1] / 100) - 1))
        v["selic_real_tipo"] = "ex-post"
    else:
        v["selic_real"] = None
    nt = ctx.ntnb(t0)
    v["ntnb"] = nt["taxa"] if nt else None
    v["ntnb_info"] = nt
    dx = S["dxy"]
    v["dxy"] = (100 * (float(dx[:z].iloc[-1]) / float(dx[:a].iloc[-1]) - 1)
                if len(dx) and dx.index[0] <= a else None)
    fl = S["flx"]
    if len(fl) and fl.index[0] <= a:
        soma = float(fl[a:z].sum()) if modo == "episodio" else float(fl.iloc[-JANELA:].sum())
        v["fluxo"] = 100 * float((ctx.flx63 < soma).mean())
        v["fluxo_soma_musd"] = soma
    else:
        v["fluxo"] = None
    vx = S["vix"]
    v["riskoff"] = float(vx[a:z].max()) if modo == "episodio" else float(vx.iloc[-1])
    if modo == "episodio":
        v["vix_inicio"] = float(vx[:t0].iloc[-1])
    ff = S["ff"]
    v["fed"] = float(ff[:fz].iloc[-1] - ff[:fa].iloc[-1]) if len(ff[:fa]) else None
    return v


GRAU = {"normal": 0, "atencao": 1, "alerta": 2}


def situacao(st_ep, st_hoje):
    """Compara o status de hoje com o do episódio, pelas mesmas regras."""
    if st_ep == "sem_dado" or st_hoje == "sem_dado":
        return "sem_dado"
    if GRAU[st_hoje] >= GRAU[st_ep]:
        return "presente"
    if st_hoje == "atencao":
        return "proxima"
    return "distante"


def regra_txt(k):
    R = REGRAS[k]
    sinal = "acima de" if R["dir"] > 0 else "abaixo de"
    u = {"p.p.": " p.p.", "%": "%", "% + IPCA": "%", "pct": "", "": ""}[R["un"]]
    pre = "percentil " if R["un"] == "pct" else ""
    n = lambda x: fmt(x, 1 if x % 1 else 0)
    fim = "" if u.endswith(".") else "."
    return f"Alerta {sinal} {pre}{n(R['alerta'])}{u}; atenção {sinal} {pre}{n(R['atencao'])}{u}{fim}"


def condicoes_cenario(ctx, c, data_base):
    hoje = valores_em(ctx, data_base, "hoje")
    datas = [c["data_inicio_real"]] if c["tipo"] == "reconstruído" else c["analogos"]
    eps = [valores_em(ctx, d, "episodio") for d in datas]
    linhas = []
    for k, R in REGRAS.items():
        vals = [e.get(k) for e in eps]
        sts = [status_de(k, x) for x in vals]
        disp = [s for s in sts if s != "sem_dado"]
        if not disp:
            continue
        st_ep = max(disp, key=lambda s: GRAU[s])  # o grau mais adverso entre os análogos
        if st_ep == "normal":
            continue  # não foi gatilho do episódio
        st_h = status_de(k, hoje.get(k))
        linhas.append({"id": k, "nome": R["nome"], "unidade": R["un"], "fonte": R["fonte"],
                       "episodio": vals, "status_episodio": sts, "hoje": hoje.get(k), "status_hoje": st_h,
                       "situacao": situacao(st_ep, st_h), "regra": regra_txt(k)})
    extra = {"vix_inicio": [e.get("vix_inicio") for e in eps],
             "selic_real_tipo": [e.get("selic_real_tipo") for e in eps],
             "ntnb": [e.get("ntnb_info") for e in eps], "ntnb_hoje": hoje.get("ntnb_info")}
    return {"datas": datas,
            "janela": f"No episódio, os {JANELA} dias úteis a partir do início; hoje, os {JANELA} dias úteis até a data-base. Fed Funds: 12 meses. Dívida: 12 meses até o ponto de referência.",
            "linhas": linhas, "extra": extra, "qualitativo": c.get("qualitativo")}


def gatilhos(ctx, data_base):
    hoje = valores_em(ctx, data_base, "hoje")
    ano = data_base.year
    selic_v, selic_d = ctx.ultimo("selic", data_base)
    ipca_v, ipca_d = ctx.ultimo("ipca_e", data_base)
    dbgg_v, dbgg_d = ctx.ultimo("dbgg", data_base)
    prim_v, prim_d = ctx.ultimo("prim", data_base)
    dxy_v, dxy_d = ctx.ultimo("dxy", data_base)
    ff_v, ff_d = ctx.ultimo("ff", data_base)
    vix_v, vix_d = ctx.ultimo("vix", data_base)
    flx = ctx.s["flx"]
    f63 = hoje["fluxo_soma_musd"]
    fano = float(flx[str(ano)].sum())
    nt = hoje["ntnb_info"]
    fdb = ctx.focus("Dívida bruta do governo geral", ano + 1)
    halv = date(2024, 4, 20) + pd.Timedelta(minutes=10 * 210000)
    dias_halv = (pd.Timestamp(halv) - data_base).days
    st = {k: status_de(k, hoje.get(k)) for k in REGRAS}
    NAO = "Não altera as projeções: serve para ler os cenários."
    return [
        {"id": "fiscal", "nome": "Risco fiscal",
         "leitura": f"Dívida bruta em {fmt(dbgg_v)}% do PIB ({fmt(hoje['fiscal'], 1, True)} p.p. em 12 meses); "
                    f"déficit primário de {fmt(prim_v, 2)}% do PIB em 12 meses; o Focus projeta dívida de {fmt(fdb)}% em {ano + 1}.",
         "valor": hoje["fiscal"], "regra": regra_txt("fiscal"), "status": st["fiscal"], "no_modelo": False, "efeito": NAO,
         "datas": {"dívida": dbgg_d, "primário": prim_d, "Focus": ctx.focus_data},
         "fonte": "BCB/SGS 13762 e 5793; BCB/Focus"},
        {"id": "selic_real", "nome": "Selic real",
         "leitura": f"Selic de {fmt(selic_v, 2)}% e IPCA esperado de {fmt(ipca_v, 2)}% em 12 meses: juro real ex-ante de {fmt(hoje['selic_real'])}%. Juro real alto sustenta o real.",
         "valor": hoje["selic_real"], "regra": regra_txt("selic_real"), "status": st["selic_real"], "no_modelo": True,
         "efeito": "Entra no modelo, na versão ex-post (Selic deflacionada pelo IPCA realizado): define a deriva mediana do câmbio.",
         "datas": {"Selic": selic_d, "Focus IPCA 12m": ipca_d}, "fonte": "BCB/SGS 432; BCB/Focus"},
        {"id": "ntnb", "nome": "Prêmio do Tesouro IPCA+",
         "leitura": f"Tesouro IPCA+ {nt['vencimento'][:4]} (cerca de {fmt(nt['anos'], 0)} anos) paga IPCA + {fmt(nt['taxa'], 2)}%. Juro real longo alto indica prêmio de risco fiscal.",
         "valor": nt["taxa"], "regra": regra_txt("ntnb"), "status": st["ntnb"], "no_modelo": False, "efeito": NAO,
         "datas": {"Tesouro": nt["data"]}, "fonte": "Tesouro Transparente (taxa de compra)"},
        {"id": "dxy", "nome": "Dólar global",
         "leitura": f"Índice amplo do dólar em {fmt(dxy_v)}, {fmt(hoje['dxy'], 1, True)}% em 63 dias úteis.",
         "valor": hoje["dxy"], "regra": regra_txt("dxy"), "status": st["dxy"], "no_modelo": False, "efeito": NAO,
         "datas": {"índice": dxy_d}, "fonte": "FRED DTWEXBGS, proxy público do DXY (o índice da ICE não está no FRED)"},
        {"id": "fed", "nome": "Juros nos EUA",
         "leitura": f"Fed Funds em {fmt(ff_v, 2)}%, {fmt(hoje['fed'], 2, True)} p.p. em 12 meses.",
         "valor": hoje["fed"], "regra": regra_txt("fed"), "status": st["fed"], "no_modelo": False, "efeito": NAO,
         "datas": {"Fed Funds": ff_d}, "fonte": "FRED DFF"},
        {"id": "fluxo", "nome": "Fluxo cambial",
         "leitura": f"Saldo de US$ {fmt(f63 / 1000, 1, True)} bi em 63 dias úteis (percentil {fmt(hoje['fluxo'], 0)} desde 2008); no ano, US$ {fmt(fano / 1000, 1, True)} bi.",
         "valor": hoje["fluxo"], "regra": regra_txt("fluxo"), "status": st["fluxo"], "no_modelo": False, "efeito": NAO,
         "datas": {"fluxo": str(flx.index[-1].date())}, "fonte": "BCB/SGS 13961 (fluxo contratado, total)"},
        {"id": "riskoff", "nome": "Aversão a risco global",
         "leitura": f"VIX em {fmt(vix_v)}.",
         "valor": vix_v, "regra": regra_txt("riskoff"), "status": st["riskoff"], "no_modelo": False, "efeito": NAO,
         "datas": {"VIX": vix_d}, "fonte": "FRED VIXCLS"},
        {"id": "halving", "nome": "Halving do BTC",
         "leitura": f"Próximo halving estimado para {halv.strftime('%m/%Y')}, daqui a cerca de {dias_halv} dias: fora dos 365 dias projetados.",
         "valor": dias_halv, "regra": "Inferência: bloco 1.050.000 a 10 minutos por bloco desde o halving de 20/04/2024. O ciclo pós-halving não garante alta.",
         "status": "normal", "no_modelo": False, "efeito": NAO, "datas": {}, "fonte": "Cálculo próprio (inferência)"},
        {"id": "etf", "nome": "Fluxo de ETFs de BTC",
         "leitura": "Lacuna: nenhuma das fontes autorizadas (BCB, Tesouro, FRED, CoinGecko, Binance) publica o fluxo diário dos ETFs à vista.",
         "valor": None, "regra": "Exigido pela especificação, mas não monitorado até haver fonte pública autorizada.",
         "status": "sem_dado", "no_modelo": False, "efeito": NAO, "datas": {}, "fonte": "—"},
    ]


def resumo_backtest(res):
    out = []
    df = pd.DataFrame(res)
    for corte in sorted(df.corte.unique()) + ["agregado"]:
        for a in ATIVOS:
            for h in HORIZ_DIAS:
                if corte == "agregado":
                    g = df[(df.ativo == a) & (df.h == h)]
                    w = g.n / g.n.sum()
                    p, p5, p1 = (float((g[k] * w).sum()) for k in ("abaixo_p10", "abaixo_p5", "abaixo_p1"))
                    n, ni = int(g.n.sum()), int(g.n_indep.sum())
                else:
                    x = df[(df.corte == corte) & (df.ativo == a) & (df.h == h)].iloc[0]
                    p, p5, p1 = float(x.abaixo_p10), float(x.abaixo_p5), float(x.abaixo_p1)
                    n, ni = int(x.n), int(x.n_indep)
                lo, hi = wilson(p, ni)
                out.append({"corte": corte, "ativo": a, "h": h, "n": n, "n_indep": ni, "abaixo_p10": p,
                            "abaixo_p5": p5, "abaixo_p1": p1, "ic95": [lo, hi], "classe": classe_calib(p, lo, hi)})
    return out


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
