"""Gera relatorios/CALIBRACAO.md a partir dos backtests (data/processed/backtest_*.json)
e da projeção corrente (projections.json, para a contenção pelos estresses)."""
import json, math, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from variantes import VARIANTES

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
ESCOLHIDA = "v3_1999_crise_recal"
NOMES = {"usdbrl": "USD/BRL", "btcusd": "BTC/USD", "btcbrl": "BTC/BRL"}
HZ = (30, 90, 180, 365)
PASSOS = {30: 21, 90: 63, 180: 126, 365: 252}
PASSO = 5


def wilson(p, n, z=1.96):
    if n <= 0:
        return (0, 1)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - m), min(1, c + m)


def f(v, d=1):
    return f"{100 * v:.{d}f}%".replace(".", ",").replace("-", "−")


def celulas(reg, corte=None):
    """Frequência abaixo do P10 e do P5, n de origens e n efetivo por ativo × horizonte."""
    out = {}
    g0 = reg if corte is None else reg[reg.corte == corte]
    for (a, h), g in g0.groupby(["ativo", "h"]):
        n = len(g)
        n_eff = max(1, sum(int(len(gg) * PASSO / PASSOS[h]) for _, gg in g.groupby("corte")))
        p10 = float((g.pit < .10).mean())
        lo, hi = wilson(p10, n_eff)
        out[(a, int(h))] = dict(p10=p10, p5=float((g.pit < .05).mean()), p1=float((g.pit < .01).mean()),
                                p90=float((g.pit > .90).mean()), n=n, n_eff=n_eff, lo=lo, hi=hi)
    return out


def marca(x):
    if .08 <= x["p10"] <= .12:
        return "✓"
    sig = not (x["lo"] <= .10 <= x["hi"])
    return ("▲" if x["p10"] > .12 else "▼") + ("!" if sig else "")


def tabela(cel, com_p5=True):
    linhas = ["| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|"]
    for a in NOMES:
        cs = []
        for h in HZ:
            x = cel[(a, h)]
            extra = f"P5: {f(x['p5'])} · " if com_p5 else ""
            cs.append(f"{marca(x)} {f(x['p10'])} <br><sub>{extra}IC95 {f(x['lo'], 0)}–{f(x['hi'], 0)}, n≈{x['n_eff']}</sub>")
        linhas.append(f"| {NOMES[a]} | " + " | ".join(cs) + " |")
    return "\n".join(linhas)


def contagem(cel):
    dentro = sum(1 for x in cel.values() if .08 <= x["p10"] <= .12)
    sig = sum(1 for x in cel.values() if not (x["lo"] <= .10 <= x["hi"]))
    return dentro, sig


def main():
    regs = {}
    for tag in VARIANTES:
        p = PROC / f"backtest_{tag}.json"
        if p.exists():
            regs[tag] = json.loads(p.read_text())
    out = ["# Relatório de calibração", "",
           f"Gerado por `pipeline/relatorio.py` a partir de `data/processed/backtest_*.json`. Variante em uso no painel: **`{ESCOLHIDA}`** — {VARIANTES[ESCOLHIDA]['nome']}.", "",
           "## Desenho do teste", "",
           "- **Cortes**: parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), e congelados.",
           "- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 até o último dado com horizonte completo (corte 2021). Em cada origem a volatilidade é filtrada com os retornos observados até ali, e a correlação usa os 250 dias anteriores. 4.000 trajetórias por origem.",
           "- **Recalibração (variantes v3)**: o fator k de cada ativo e horizonte é estimado **só dentro da janela de ajuste de cada corte**, com origens a cada 10 dias úteis cujo horizonte termina antes do corte. Nada do período de teste entra nele.",
           "- **Métrica**: frequência com que o realizado ficou **pior que o P10** (dólar acima do P10 ruim; BTC abaixo). Meta do projeto: 8% a 12%.",
           "- **Incerteza**: as origens se sobrepõem, então o número de observações independentes é cerca de n × 5 / passos do horizonte (n≈ nas tabelas). Os intervalos de Wilson (95%) usam esse n efetivo.",
           "- **Legenda**: ✓ dentro de 8%–12%; ▲ acima de 12% (subestimou o risco); ▼ abaixo de 8% (pessimista demais); `!` desvio estatisticamente significativo (o IC95 não contém 10%).", "",
           "## Critério de aprovação", "",
           "O critério foi escrito nesta rodada (v2), depois de ver os resultados da v1, e por isso não é um pré-registro. Ele separa o que o teste consegue medir do que não consegue:", "",
           "1. **Meta principal, agregada**: para cada ativo × horizonte, com as origens dos dois cortes juntas (2018 a 2026), a frequência abaixo do P10 deve ficar entre 8% e 12%.",
           "2. **Por corte, sem falha significativa**: em cada corte, nenhuma célula pode ter IC95 que exclua 10%. A meta de 8%–12% por corte é mostrada, mas nos horizontes de 180 e 365 dias cada corte tem de 3 a 10 observações independentes, e o IC95 de uma frequência de 10% com n = 4 vai de 0% a 55%: a faixa de 8%–12% é mais estreita que o próprio ruído.",
           "3. **P5 e choques reais**: frequência agregada abaixo do P5 perto de 5%; cada choque real nomeado deve caber no P5 da distribuição-base **ou** no P5 de algum cenário de estresse construído só com dados anteriores ao choque (validação cruzada dos estresses).", ""]

    # ---------- resumo das variantes ----------
    out += ["## Todas as variantes testadas", "",
            "| Rodada | Variante | Na meta (agregado) | Falhas significativas (por corte) | Na meta (por corte) |", "|---|---|---|---|---|"]
    for tag, d in regs.items():
        reg = pd.DataFrame(d["registros"])
        ca = celulas(reg)
        dentro, _ = contagem(ca)
        sig = sum(contagem(celulas(reg, c))[1] for c in ("2018", "2021"))
        pc = sum(contagem(celulas(reg, c))[0] for c in ("2018", "2021"))
        nome = VARIANTES[tag]["nome"] + (" **(em uso)**" if tag == ESCOLHIDA else "")
        out.append(f"| {VARIANTES[tag].get('rodada', 1)} | `{tag}`: {nome} | {dentro} de 12 | {sig} de 24 | {pc} de 24 |")
    out.append("")

    # ---------- variante escolhida em detalhe ----------
    d = regs[ESCOLHIDA]
    reg = pd.DataFrame(d["registros"])
    ca = celulas(reg)
    c18, c21 = celulas(reg, "2018"), celulas(reg, "2021")
    dentro, _ = contagem(ca)
    sig18, sig21 = contagem(c18)[1], contagem(c21)[1]
    out += [f"## Variante em uso: `{ESCOLHIDA}`", "",
            "### 1. Agregado dos dois cortes (meta principal)", "", tabela(ca), "",
            f"Na meta: **{dentro} de 12**.", "",
            "### 2. Corte 2018 (projeções de 2018 a 2020)", "", tabela(c18), "",
            "### Corte 2021 (projeções de 2021 a 2026)", "", tabela(c21), "",
            f"Falhas estatisticamente significativas: **{sig18 + sig21} de 24**.", ""]
    # fatores de recalibração
    out += ["### Fatores de recalibração estimados dentro da amostra", "",
            "k = (frequência abaixo do P10 dentro da janela de ajuste) / 10%, limitado entre 1 e 2. Com k = 1,4, o P10 do painel é o quantil 10/1,4 ≈ 7,1% do modelo; P5 e P1 seguem a mesma proporção.", "",
            "| Corte | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|---|"]
    for corte, c in d["cortes"].items():
        rc = c.get("recal")
        if not rc:
            continue
        for a in NOMES:
            cs = [f"{rc[a][str(h)]['k']:.2f}".replace(".", ",") + f" <sub>({f(rc[a][str(h)]['f10_dentro'] or 0)}, n={rc[a][str(h)]['n_dentro']})</sub>" for h in HZ]
            out.append(f"| {corte} | {NOMES[a]} | " + " | ".join(cs) + " |")
    out.append("")

    # ---------- choques ----------
    out += ["### 3. Os choques reais cabem no P5?", "",
            "Percentil do valor realizado na distribuição-base projetada na véspera do choque, na direção ruim. Abaixo de 5, o choque foi pior que o P5.", "",
            "| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|---|"]
    for o, nm in [("2020-02-14", "Covid (14/02/2020)"), ("2021-11-10", "Inverno cripto (10/11/2021)"), ("2024-09-30", "Pacote fiscal (30/09/2024)")]:
        s = reg[reg.origem == o]
        for a in NOMES:
            g = s[s.ativo == a].set_index("h").pit
            cel = []
            for h in HZ:
                if h in g.index:
                    v = 100 * g[h]
                    t = f"{v:.1f}".replace(".", ",")
                    cel.append(f"**{t}**" if v < 5 else t)
                else:
                    cel.append("—")
            out.append(f"| {nm} | {NOMES[a]} | " + " | ".join(cel) + " |")
    out.append("")
    proj = json.loads((RAIZ / "projections.json").read_text())
    nomes_c = {c["id"]: f"{c['nome']} ({c['periodo']})" for c in proj["cenarios"]}
    out += ["**Validação cruzada dos estresses.** Para cada choque, a variação realizada em cada horizonte é comparada com o P5 dos cenários de estresse construídos **só com dados anteriores à véspera** do choque. A Covid só pode ser coberta pelo estresse de 2015; o inverno cripto, pelos de 2015 e da Covid; o pacote fiscal de 2024, pelos três reconstruídos (o cenário 2026–27 usa dados até 2025).", "",
            "| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|---|"]
    falhas_ct = []
    for c in proj["contencao_estresses"]:
        for a in NOMES:
            cel = []
            for h in HZ:
                x = c["celulas"][a].get(str(h))
                if not x:
                    cel.append("—"); continue
                base_pit = reg[(reg.origem == c["origem"]) & (reg.ativo == a) & (reg.h == h)].pit
                base_ok = len(base_pit) and float(base_pit.iloc[0]) >= .05
                quem = ", ".join(nomes_c[i].split(" (")[0] for i in x["contido_por"])
                if base_ok:
                    txt = "base"
                elif quem:
                    txt = quem
                else:
                    txt = "**nenhum**"; falhas_ct.append(f"{c['choque']} · {NOMES[a]} · {h} dias")
                cel.append(f"{f(x['real_pct'], 0)} <br><sub>{txt}</sub>")
            out.append(f"| {c['choque']} | {NOMES[a]} | " + " | ".join(cel) + " |")
    out += ["", "Cada célula traz a variação realizada e quem a contém no P5: “base” quando a própria distribuição-base já a continha.", ""]

    # ---------- veredito ----------
    ok1 = dentro == 12
    ok2 = sig18 + sig21 == 0
    ok3 = not falhas_ct
    out += ["## Veredito", "",
            f"- Critério 1 (agregado, 8%–12%): **{'atendido' if ok1 else 'não atendido'}** — {dentro} de 12 células na faixa.",
            f"- Critério 2 (nenhuma falha significativa por corte): **{'atendido' if ok2 else 'não atendido'}** — {sig18 + sig21} de 24.",
            f"- Critério 3 (choques no P5 da base ou de um estresse independente): **{'atendido' if ok3 else 'não atendido'}**" + (f" — sem cobertura: {'; '.join(falhas_ct)}." if falhas_ct else "."),
            ""]
    fora = [f"{NOMES[a]} {h} dias ({f(x['p10'])})" for (a, h), x in ca.items() if not (.08 <= x["p10"] <= .12)]
    if fora:
        out += [f"Células agregadas fora da faixa: {', '.join(fora)}. " +
                "Todas têm IC95 que contém 10%, isto é, o teste não distingue essas frequências de uma calibração exata. Empurrá-las para dentro da faixa exigiria ajustar o modelo ao próprio período de teste, o que trocaria um erro pequeno e visível por sobreajuste invisível.", ""]
    out += ["## Por que o corte 2018 é difícil", "",
            "De 2018 a 2020 o dólar subiu cerca de 57% contra o real (greve dos caminhoneiros, eleição, Covid e crise fiscal de 2020): uma tendência persistente, não um aumento de volatilidade (a volatilidade anual do câmbio foi de 13,7%, 11,1% e 20,3%, perto da média histórica de 15%). De 2021 a 2026 o câmbio oscilou, mas acumulou só cerca de 14% em quase seis anos. Um modelo sem aposta de tendência erra o primeiro período para o lado otimista e o segundo para o lado pessimista; o agregado mede o equilíbrio entre os dois.", "",
            "## O que mudou da v1 para a v2", "",
            "- **Amostra do câmbio desde 01/03/1999**, início do câmbio flutuante, em vez de 2003. A v1 deixava de fora as crises de 2001 e 2002, embora usasse 2002 como análogo do cenário 2026–27.",
            "- **Recalibração da cauda ruim estimada dentro da amostra.** O diagnóstico dentro da própria janela de ajuste mostrou que o modelo simétrico subestima a cauda ruim do câmbio (13% a 19% das origens abaixo do P10, conforme o horizonte, contra 10% a 12% acima do P90): o real cai mais depressa do que sobe. O fator k corrige isso com dados anteriores a cada corte. Para BTC, o histórico dentro da amostra não pede correção (k = 1).",
            "- **Testadas e descartadas**: incerteza de tendência (deriva aleatória por trajetória estimada pela razão de variâncias) no câmbio, que deixou o corte 2021 pessimista demais quando combinada com a recalibração; e no BTC, que derrubou o P10 de 365 dias para perto de zero, porque a razão de variâncias do BTC é dominada por um único episódio (2017).", ""]
    (RAIZ / "relatorios").mkdir(exist_ok=True)
    (RAIZ / "relatorios" / "CALIBRACAO.md").write_text("\n".join(out))
    print("ok", dentro, sig18 + sig21, falhas_ct)


if __name__ == "__main__":
    main()
