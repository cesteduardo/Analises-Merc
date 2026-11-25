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
QS = {"P50": .50, "P10": .10, "P5": .05, "P1": .01}


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
        rr = r[:fim]
        z1 = residuos_padronizados(gf, xfx_long[cfg["fx_ini"]:fim].reindex(rr.index).fillna(0).values)
        z2 = residuos_padronizados(gb, rr["x_btc"].values)
        rho_all = float(np.corrcoef(z1, z2)[0, 1])
        nu_c = ajustar_nu_copula(z1, z2, rho_all)
        grade = np.round(np.arange(-0.3, 0.651, 0.05), 2)
        inov = {g: inovacoes(N, H_MAX, g, nu_c, gf.nu, gb.nu, rng) for g in grade}
        out["cortes"][nome] = {"fx": gf.params(), "btc": gb.params(), "rho": rho_all, "nu_copula": nu_c,
                               "crise_fx": cf, "crise_btc": cb}
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
        for o in sorted(origens):
            i0 = idx.get_loc(o)
            # variância prevista para o passo seguinte, só com dados até a origem
            v_f = gf.omega + (gf.alpha + gf.gamma * (xf_all[o] < 0)) * xf_all[o] ** 2 + gf.beta * s2f[o]
            v_b = gb.omega + (gb.alpha + gb.gamma * (r["x_btc"][o] < 0)) * r["x_btc"][o] ** 2 + gb.beta * s2b[o]
            rho = float(zf[:o].iloc[-250:].corr(zb[:o].iloc[-250:]))
            g = grade[np.argmin(np.abs(grade - rho))]
            e1, e2 = inov[g]
            mu_f = -selic_ff(o, selic, ff) / 252 if cfg["deriva_fx"] == "carry" else 0.0
            sf = simular_com_crise(gf, v_f, e1, mu_f, cf, rng).cumsum(axis=1)
            sb = simular_com_crise(gb, v_b, e2, 0.0, cb, rng).cumsum(axis=1)
            s0f, s0b = df["fx"].iloc[i0], df["btc"].iloc[i0]
            for hd, hp in HORIZ_PASSOS.items():
                if i0 + hp >= len(idx):
                    continue
                real_f, real_b = df["fx"].iloc[i0 + hp], df["btc"].iloc[i0 + hp]
                lv = {"usdbrl": sf[:, hp - 1], "btcusd": sb[:, hp - 1],
                      "btcbrl": sb[:, hp - 1] - sf[:, hp - 1]}
                # na direção ruim: valores baixos = pior
                real = {"usdbrl": -np.log(real_f / s0f), "btcusd": np.log(real_b / s0b),
                        "btcbrl": np.log(real_b * real_f / (s0b * s0f))}
                for a in lv:
                    pit = float((lv[a] < real[a]).mean())
                    q = {k: float(np.quantile(lv[a], v)) for k, v in QS.items()}
                    out["registros"].append({"corte": nome, "origem": str(o.date()), "h": hd, "ativo": a,
                                             "pit": pit, "real": float(real[a]), **q})
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
    cfg = dict(fx_ini="2003-01-01", deriva_fx=sys.argv[1] if len(sys.argv) > 1 else "zero",
               btc_alvo_anos=int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "0" else None,
               crise=len(sys.argv) > 3 and sys.argv[3] == "crise")
    out = rodar(cfg)
    res = resumir(out)
    pd.set_option("display.width", 200)
    print(json.dumps(cfg))
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    tag = f"{cfg['deriva_fx']}_{cfg['btc_alvo_anos'] or 'tudo'}" + ("_crise" if cfg["crise"] else "")
    out["resumo"] = res.to_dict(orient="records")
    out["gerado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (RAIZ / "data" / "processed" / f"backtest_{tag}.json").write_text(json.dumps(out))
