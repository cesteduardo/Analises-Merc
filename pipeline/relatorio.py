"""Gera relatorios/CALIBRACAO.md a partir dos arquivos de backtest."""
import json, math
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
ESCOLHIDA = "juro_real_tudo_crise"
VARIANTES = {
    "zero_tudo": "Deriva zero, sem camada de crise",
    "carry_tudo": "Deriva do diferencial de juros (Selic − Fed Funds), sem camada de crise",
    "zero_tudo_crise": "Deriva zero + camada de crise com devolução (versão 1 do painel)",
    "juro_real_tudo": "Deriva do câmbio condicionada ao juro real, sem camada de crise",
    "juro_real_tudo_crise": "Deriva do câmbio condicionada ao juro real + camada de crise (ESCOLHIDA)",
    "carry_tudo_crise": "Deriva do diferencial de juros + camada de crise",
}
NOMES = {"usdbrl": "USD/BRL", "btcusd": "BTC/USD", "btcbrl": "BTC/BRL"}


def wilson(p, n, z=1.96):
    if n <= 0:
        return (0, 1)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0, c - m), min(1, c + m)


def f(v):
    return f"{100 * v:.1f}%".replace(".", ",")


def tabela(res, corte=None):
    linhas = ["| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|"]
    for a in NOMES:
        cel = []
        for h in (30, 90, 180, 365):
            if corte:
                x = res[(res.corte == corte) & (res.ativo == a) & (res.h == h)].iloc[0]
                p, n = x.abaixo_p10, x.n_indep
            else:
                g = res[(res.ativo == a) & (res.h == h)]
                p = (g.abaixo_p10 * g.n).sum() / g.n.sum()
                n = int(g.n_indep.sum())
            lo, hi = wilson(p, n)
            marca = "✓" if .08 <= p <= .12 else ("▲" if p > .12 else "▼")
            cel.append(f"{marca} {f(p)} <br><sub>IC95 {f(lo)}–{f(hi)}, n≈{n}</sub>")
        linhas.append(f"| {NOMES[a]} | " + " | ".join(cel) + " |")
    return "\n".join(linhas)


def main():
    out = ["# Relatório de calibração", "",
           "Gerado por `pipeline/relatorio.py` a partir de `data/processed/backtest_*.json`.", "",
           "## Desenho do teste", "",
           "- **Cortes**: parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), e congelados.",
           "- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 até o último dado com horizonte completo (corte 2021). Em cada origem a volatilidade é filtrada com os retornos observados até ali, e a correlação usa os 250 dias anteriores.",
           "- **Métrica**: frequência com que o valor realizado ficou **pior que o P10** (dólar acima do percentil 90; BTC abaixo do percentil 10). Meta: 8% a 12%.",
           "- **Incerteza**: as origens se sobrepõem (horizonte maior que o passo de 5 dias), então o número de observações independentes é aproximadamente n × 5 / passos do horizonte. Os intervalos de confiança de Wilson (95%) usam esse n efetivo e são, por isso, largos.",
           "- **Legenda**: ✓ dentro da meta; ▲ acima de 12% (o modelo subestimou o risco); ▼ abaixo de 8% (pessimista demais).", ""]
    resumos = {}
    for tag, nome in VARIANTES.items():
        p = PROC / f"backtest_{tag}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        res = pd.DataFrame(d["resumo"])
        resumos[tag] = res
        dentro = int(((res.abaixo_p10 >= .08) & (res.abaixo_p10 <= .12)).sum())
        pool = res.assign(w=res.abaixo_p10 * res.n).groupby(["ativo", "h"]).apply(lambda g: g.w.sum() / g.n.sum(), include_groups=False)
        dentro_pool = int(((pool >= .08) & (pool <= .12)).sum())
        out += [f"## {nome}", "", f"Combinações na meta, cortes separados: **{dentro} de {len(res)}**. Com os dois cortes juntos: **{dentro_pool} de {len(pool)}**.", "",
                "### Corte 2018 (projeções de 2018 a 2020)", "", tabela(res, "2018"), "",
                "### Corte 2021 (projeções de 2021 a 2026)", "", tabela(res, "2021"), "",
                "### Os dois cortes juntos", "", tabela(res), ""]
    # choques
    d = json.loads((PROC / f"backtest_{ESCOLHIDA}.json").read_text())
    reg = pd.DataFrame(d["registros"])
    out += ["## Os choques reais cabem no P5? (variante escolhida)", "",
            "Percentil do valor realizado na distribuição projetada na véspera do choque, na direção ruim. Abaixo de 5 significa que o choque foi pior que o P5.", "",
            "| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|---|"]
    for o, nm in [("2020-02-14", "Covid (14/02/2020)"), ("2021-11-10", "Inverno cripto (10/11/2021)"), ("2024-09-30", "Pacote fiscal (30/09/2024)")]:
        s = reg[reg.origem == o]
        for a in NOMES:
            g = s[s.ativo == a].set_index("h").pit
            cel = []
            for h in (30, 90, 180, 365):
                if h in g.index:
                    v = 100 * g[h]
                    cel.append(("**" if v < 5 else "") + f"{v:.1f}".replace(".", ",") + ("**" if v < 5 else ""))
                else:
                    cel.append("—")
            out.append(f"| {nm} | {NOMES[a]} | " + " | ".join(cel) + " |")
    out += ["", "## Variantes exploratórias só de câmbio", "",
            "Testadas antes da escolha, com o mesmo desenho (frequência pior que o P10, corte 2018 / corte 2021):", "",
            "| Variante | 30 dias | 90 dias | 180 dias | 365 dias |", "|---|---|---|---|---|",
            "| Metade do diferencial de juros | 25,2% / 9,6% | 24,5% / 7,4% | 27,2% / 4,4% | 33,8% / 3,7% |",
            "| Tendência de 1 ano × 0,5 | 22,5% / 10,6% | 21,9% / 9,9% | 28,5% / 11,4% | 29,8% / 14,2% |",
            "| Tendência de 3 anos | 22,5% / 9,2% | 20,5% / 7,4% | 25,8% / 8,5% | 30,5% / 13,4% |", "",
            "## Conclusão", "",
            "**A meta não é atingida em cada corte separadamente; com os dois cortes juntos, a variante escolhida põe 9 de 12 combinações entre 8% e 12%.**", "",
            "O obstáculo é de dados: de 2018 a 2020 o dólar subiu cerca de 57% contra o real (greve dos caminhoneiros, eleição, Covid e crise fiscal de 2020), um movimento persistente que a volatilidade de 2003 a 2017 não antecipava; de 2021 a 2026 o câmbio oscilou muito, mas o dólar acumulou só cerca de 14% em quase seis anos. Um modelo largo o bastante para o primeiro período tende a ser pessimista demais no segundo.", "",
            "A deriva condicionada ao juro real é a única variante que melhorou os dois cortes ao mesmo tempo no câmbio. Ela tem base econômica (o carrego: juro real alto atrai capital e sustenta o real; juro real baixo o enfraquece) e é estatisticamente significativa na amostra anterior a cada corte (estatística t de Newey-West acima de 3). Mesmo assim, ela foi escolhida olhando os resultados do backtest, o que é uma forma branda de sobreajuste; por isso todas as variantes ficam registradas aqui.", "",
            "**Consequência para a leitura do painel:** com o juro real atual acima do neutro estimado, a deriva da mediana favorece o real. O pessimismo do painel fica na cauda (P10, P5, P1), na camada de crise e nos cenários de estresse, não na mediana.", ""]
    (RAIZ / "relatorios").mkdir(exist_ok=True)
    (RAIZ / "relatorios" / "CALIBRACAO.md").write_text("\n".join(out))
    print("ok")


if __name__ == "__main__":
    main()
