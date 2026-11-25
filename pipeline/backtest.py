"""Backtest fora da amostra com dois cortes (2018 e 2021).

Para cada corte, os parâmetros do GARCH e da cópula são estimados só com dados
até o corte e ficam congelados. A partir daí, a cada 5 dias úteis (origem), o
modelo filtra a volatilidade com os retornos observados até a origem, simula
4.000 trajetórias e registra onde o valor realizado caiu na distribuição.

Métrica principal: frequência com que o realizado ficou PIOR que o P10 (mais
dólar, BTC mais barato). Meta: 8% a 12%.
"""
import json, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from nucleo import *
from variantes import VARIANTES

CORTES = {
    "2018": dict(fim_ajuste="2017-12-31", aval_ini="2018-01-01", aval_fim="2020-12-31"),
    "2021": dict(fim_ajuste="2020-12-31", aval_ini="2021-01-01", aval_fim="2026-12-31"),
}
CHOQUES = {  # origem imediatamente anterior ao choque, escolhida pelo histórico real
    "Covid (fev/2020)": "2020-02-14",
    "Inverno cripto (nov/2021)": "2021-11-10",
    "Pacote fiscal (dez/2024)": "2024-09-30",
}
N, PASSO = 4000, 5
N_DENTRO, PASSO_DENTRO, K_MAX = 2000, 10, 2.0
QS = {"P50": .50, "P10": .10, "P5": .05, "P1": .01}


def recalibrar_pit(p, k):
    """Com o P10 lido no nível 0,10/k do modelo (e P5, P1 na mesma proporção),
    o PIT equivalente na cauda ruim é p·k. Acima da mediana nada muda."""
    return float(min(p * k, max(p, .5)))


def selic_ff(data, selic, ff):
    s = selic[:data].iloc[-1]
    f = ff[:data].iloc[-1]
    return np.log1p(s / 100) - np.log1p(f / 100)


def rodar(cfg):
    df = base_diaria()
    r = retornos(df)
    fx_long, _ = serie("usdbrl_ptax")
    xfx_long = -np.log(fx_long).diff().dropna()
    selic, _ = serie("selic_meta")
    ff, _ = serie("fed_funds")
    out = {"config": cfg, "cortes": {}, "registros": []}
    rng = np.random.default_rng(20261125)
    for nome, c in CORTES.items():
        fim = pd.Timestamp(c["fim_ajuste"])
        xf = xfx_long[cfg["fx_ini"]:fim].values
        xb = r["x_btc"][:fim].values
        alvo_b = None
        if cfg.get("btc_alvo_anos"):
            alvo_b = float(np.var(xb[-252 * cfg["btc_alvo_anos"]:]))
        gf, gb = Garch(xf), Garch(xb, alvo_var=alvo_b)
        cf = estimar_crise(xf, g=gf) if cfg.get("crise") else None
        cb = estimar_crise(xb, g=gb) if cfg.get("crise") else None
        tf = estimar_deriva_incerta(xf, gf, cf) if cfg.get("deriva_incerta_fx") else None
        tb = estimar_deriva_incerta(xb, gb, cb) if cfg.get("deriva_incerta_btc") else None
        rr = r[:fim]
        z1 = residuos_padronizados(gf, xfx_long[cfg["fx_ini"]:fim].reindex(rr.index).fillna(0).values)
        z2 = residuos_padronizados(gb, rr["x_btc"].values)
        rho_all = float(np.corrcoef(z1, z2)[0, 1])
        nu_c = ajustar_nu_copula(z1, z2, rho_all)
        grade = np.round(np.arange(-0.3, 0.651, 0.05), 2)
        inov = {g: inovacoes(N, H_MAX, g, nu_c, gf.nu, gb.nu, rng) for g in grade}
        out["cortes"][nome] = {"fx": gf.params(), "btc": gb.params(), "rho": rho_all, "nu_copula": nu_c,
                               "crise_fx": cf, "crise_btc": cb, "tendencia_fx": tf, "tendencia_btc": tb}
        # variâncias filtradas com parâmetros congelados ao longo de toda a amostra
        xf_all = xfx_long[cfg["fx_ini"]:]
        s2f, _ = gf.filtrar(xf_all.values)
        s2f = pd.Series(s2f, index=xf_all.index)
        s2b, _ = gb.filtrar(r["x_btc"].values)
        s2b = pd.Series(s2b, index=r.index)
        zf = (r["x_fx"] / np.sqrt(s2f.reindex(r.index))).dropna()
        zb = (r["x_btc"] / np.sqrt(s2b)).reindex(zf.index)
        idx = df.index
        origens = idx[(idx >= c["aval_ini"]) & (idx <= c["aval_fim"])]
        origens = list(origens[::PASSO])
        for ch, d in CHOQUES.items():
            d = idx[idx <= d][-1]
            if c["aval_ini"] <= str(d.date()) <= c["aval_fim"] and d not in origens:
                origens.append(d)
        def simular_origem(o, n_traj, so_fx=False):
            """Trajetórias acumuladas (direção ruim) a partir da origem o, só com
            dados até o. Devolve (sf, sb); sb é None quando so_fx."""
            v_f = gf.omega + (gf.alpha + gf.gamma * (xf_all[o] < 0)) * xf_all[o] ** 2 + gf.beta * s2f[o]
            if so_fx:
                e1 = t_padronizada_ppf(np.clip(rng.random((n_traj, H_MAX)), 1e-12, 1 - 1e-12), gf.nu)
                e2 = None
            else:
                rho = float(zf[:o].iloc[-250:].corr(zb[:o].iloc[-250:]))
                g = grade[np.argmin(np.abs(grade - rho))]
                e1, e2 = inov[g]
                e1, e2 = e1[:n_traj], e2[:n_traj]
            mu_f = -selic_ff(o, selic, ff) / 252 if cfg["deriva_fx"] == "carry" else 0.0
            mtf = rng.standard_normal(n_traj) * tf["s_diaria"] if tf else None
            sf = simular_com_crise(gf, v_f, e1, mu_f, cf, rng, mu_trilha=mtf).cumsum(axis=1)
            if so_fx:
                return sf, None
            v_b = gb.omega + (gb.alpha + gb.gamma * (r["x_btc"][o] < 0)) * r["x_btc"][o] ** 2 + gb.beta * s2b[o]
            mtb = rng.standard_normal(n_traj) * tb["s_diaria"] if tb else None
            sb = simular_com_crise(gb, v_b, e2, 0.0, cb, rng, mu_trilha=mtb).cumsum(axis=1)
            return sf, sb

        def pits(o, sf, sb, nivel_fx, nivel_btc, limite=None):
            """PIT do realizado em cada horizonte, na direção ruim. Com `limite`, só
            horizontes que terminam até essa data (avaliação dentro da amostra)."""
            idx_f = nivel_fx.index
            i0 = idx_f.get_loc(o)
            s0f = nivel_fx.iloc[i0]
            s0b = nivel_btc.iloc[i0] if nivel_btc is not None else None
            res = []
            for hd, hp in HORIZ_PASSOS.items():
                if i0 + hp >= len(idx_f) or (limite is not None and idx_f[i0 + hp] > limite):
                    continue
                real_f = nivel_fx.iloc[i0 + hp]
                lv = {"usdbrl": sf[:, hp - 1]}
                real = {"usdbrl": -np.log(real_f / s0f)}
                if sb is not None:
                    real_b = nivel_btc.iloc[i0 + hp]
                    lv.update({"btcusd": sb[:, hp - 1], "btcbrl": sb[:, hp - 1] - sf[:, hp - 1]})
                    real.update({"btcusd": np.log(real_b / s0b), "btcbrl": np.log(real_b * real_f / (s0b * s0f))})
                for a in lv:
                    res.append((hd, a, lv[a], float(real[a])))
            return res

        # ---- recalibração dos quantis, estimada só dentro da amostra de ajuste ----
        k_recal = {a: {h: 1.0 for h in HORIZ_DIAS} for a in ("usdbrl", "btcusd", "btcbrl")}
        if cfg.get("recal"):
            dentro = {a: {h: [] for h in HORIZ_DIAS} for a in k_recal}
            fx_niv = fx_long[cfg["fx_ini"]:]
            o_fx = fx_niv.index[(fx_niv.index > xf_all.index[300]) & (fx_niv.index < fim)][::PASSO_DENTRO]
            for o in o_fx:
                sf, _ = simular_origem(o, N_DENTRO, so_fx=True)
                for hd, a, lv, re in pits(o, sf, None, fx_niv, None, limite=fim):
                    dentro[a][hd].append(float((lv < re).mean()))
            o_b = idx[(idx > idx[300]) & (idx < fim)][::PASSO_DENTRO]
            for o in o_b:
                sf, sb = simular_origem(o, N_DENTRO)
                for hd, a, lv, re in pits(o, sf, sb, df["fx"], df["btc"], limite=fim):
                    if a != "usdbrl":
                        dentro[a][hd].append(float((lv < re).mean()))
            for a in dentro:
                for h in HORIZ_DIAS:
                    v = np.array(dentro[a][h])
                    f10 = float((v < .10).mean()) if len(v) else .10
                    # só torna o painel mais pessimista, nunca menos; teto de 2x
                    k_recal[a][h] = float(np.clip(f10 / .10, 1.0, K_MAX))
            out["cortes"][nome]["recal"] = {a: {str(h): {"k": k_recal[a][h], "n_dentro": len(dentro[a][h]),
                                                         "f10_dentro": float((np.array(dentro[a][h]) < .1).mean()) if dentro[a][h] else None}
                                                for h in HORIZ_DIAS} for a in dentro}

        for o in sorted(origens):
            sf, sb = simular_origem(o, N)
            for hd, a, lv, re in pits(o, sf, sb, df["fx"], df["btc"]):
                k = k_recal[a][hd]
                pit_bruto = float((lv < re).mean())
                q = {kk: float(np.quantile(lv, v / k if v < .5 else v)) for kk, v in QS.items()}
                out["registros"].append({"corte": nome, "origem": str(o.date()), "h": hd, "ativo": a,
                                         "pit": recalibrar_pit(pit_bruto, k), "pit_bruto": pit_bruto, "k": k,
                                         "real": re, **q})
    return out


def resumir(out):
    reg = pd.DataFrame(out["registros"])
    linhas = []
    for (corte, a, h), g in reg.groupby(["corte", "ativo", "h"]):
        n = len(g)
        n_eff = max(1, int(n * PASSO / HORIZ_PASSOS[h]))
        f10 = float((g.pit < .10).mean()); f5 = float((g.pit < .05).mean()); f1 = float((g.pit < .01).mean())
        f90 = float((g.pit > .90).mean())
        linhas.append(dict(corte=corte, ativo=a, h=h, n=n, n_indep=n_eff, abaixo_p10=f10, abaixo_p5=f5,
                           abaixo_p1=f1, acima_p90=f90))
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    # uso: python3 pipeline/backtest.py <variante>   (ver pipeline/variantes.py)
    tag = sys.argv[1] if len(sys.argv) > 1 else "zero_tudo_crise"
    cfg = dict(VARIANTES[tag], tag=tag)
    out = rodar(cfg)
    res = resumir(out)
    pd.set_option("display.width", 200)
    print(json.dumps(cfg))
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    out["resumo"] = res.to_dict(orient="records")
    out["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (RAIZ / "data" / "processed" / f"backtest_{tag}.json").write_text(json.dumps(out))
