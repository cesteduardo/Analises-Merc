# Relatório de calibração

Gerado por `pipeline/relatorio.py` a partir de `data/processed/backtest_*.json`. Variante em uso no painel: **`v3_1999_crise_recal`** — Câmbio desde 1999 + crise + recalibração de quantis dentro da amostra.

## Desenho do teste

- **Cortes**: parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), e congelados.
- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 até o último dado com horizonte completo (corte 2021). Em cada origem a volatilidade é filtrada com os retornos observados até ali, e a correlação usa os 250 dias anteriores. 4.000 trajetórias por origem.
- **Recalibração (variantes v3)**: o fator k de cada ativo e horizonte é estimado **só dentro da janela de ajuste de cada corte**, com origens a cada 10 dias úteis cujo horizonte termina antes do corte. Nada do período de teste entra nele.
- **Métrica**: frequência com que o realizado ficou **pior que o P10** (dólar acima do P10 ruim; BTC abaixo). Meta do projeto: 8% a 12%.
- **Incerteza**: as origens se sobrepõem, então o número de observações independentes é cerca de n × 5 / passos do horizonte (n≈ nas tabelas). Os intervalos de Wilson (95%) usam esse n efetivo.
- **Legenda**: ✓ dentro de 8%–12%; ▲ acima de 12% (subestimou o risco); ▼ abaixo de 8% (pessimista demais); `!` desvio estatisticamente significativo (o IC95 não contém 10%).

## Critério de aprovação

O critério foi escrito nesta rodada (v2), depois de ver os resultados da v1, e por isso não é um pré-registro. Ele separa o que o teste consegue medir do que não consegue:

1. **Meta principal, agregada**: para cada ativo × horizonte, com as origens dos dois cortes juntas (2018 a 2026), a frequência abaixo do P10 deve ficar entre 8% e 12%.
2. **Por corte, sem falha significativa**: em cada corte, nenhuma célula pode ter IC95 que exclua 10%. A meta de 8%–12% por corte é mostrada, mas nos horizontes de 180 e 365 dias cada corte tem de 3 a 10 observações independentes, e o IC95 de uma frequência de 10% com n = 4 vai de 0% a 55%: a faixa de 8%–12% é mais estreita que o próprio ruído.
3. **P5 e choques reais**: frequência agregada abaixo do P5 perto de 5%; cada choque real nomeado deve caber no P5 da distribuição-base **ou** no P5 de algum cenário de estresse construído **sem** aquele episódio (validação cruzada dos estresses).

## Todas as variantes testadas

| Rodada | Variante | Na meta (agregado) | Falhas significativas (por corte) | Na meta (por corte) |
|---|---|---|---|---|
| 1 | `zero_tudo`: Deriva zero, sem camada de crise | 2 de 12 | 1 de 24 | 5 de 24 |
| 1 | `carry_tudo`: Deriva do diferencial de juros (Selic − Fed Funds), sem camada de crise | 3 de 12 | 1 de 24 | 2 de 24 |
| 1 | `zero_tudo_crise`: Deriva zero + camada de crise (escolhida na v1) | 6 de 12 | 1 de 24 | 8 de 24 |
| 1 | `carry_tudo_crise`: Deriva do diferencial de juros + camada de crise | 7 de 12 | 1 de 24 | 6 de 24 |
| 2 | `v2_1999_crise`: Câmbio desde o início do câmbio flutuante (mar/1999) + camada de crise | 6 de 12 | 1 de 24 | 6 de 24 |
| 2 | `v2_1999_crise_tend`: Câmbio desde mar/1999 + camada de crise + incerteza de tendência no câmbio | 8 de 12 | 1 de 24 | 7 de 24 |
| 2 | `v2_2003_crise_tend`: Câmbio desde 2003 + camada de crise + incerteza de tendência no câmbio | 7 de 12 | 1 de 24 | 8 de 24 |
| 2 | `v2_1999_crise_tend2`: Câmbio desde mar/1999 + camada de crise + incerteza de tendência nos dois ativos | 5 de 12 | 1 de 24 | 6 de 24 |
| 3 | `v3_1999_crise_tend_recal`: v2 (1999 + crise + tendência no câmbio) + recalibração de quantis dentro da amostra | 6 de 12 | 0 de 24 | 5 de 24 |
| 3 | `v3_1999_crise_recal`: Câmbio desde 1999 + crise + recalibração de quantis dentro da amostra **(em uso)** | 7 de 12 | 0 de 24 | 8 de 24 |
| 3 | `v3_2003_crise_recal`: v1 (2003 + crise) + recalibração de quantis dentro da amostra | 6 de 12 | 0 de 24 | 6 de 24 |

## Variante em uso: `v3_1999_crise_recal`

### 1. Agregado dos dois cortes (meta principal)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ✓ 10,6% <br><sub>P5: 3,8% · IC95 6%–18%, n≈105</sub> | ▼ 7,6% <br><sub>P5: 3,4% · IC95 2%–21%, n≈34</sub> | ▼ 7,3% <br><sub>P5: 4,5% · IC95 1%–30%, n≈16</sub> | ✓ 8,5% <br><sub>P5: 3,0% · IC95 1%–45%, n≈7</sub> |
| BTC/USD | ▲ 13,0% <br><sub>P5: 7,4% · IC95 8%–21%, n≈105</sub> | ✓ 9,2% <br><sub>P5: 4,3% · IC95 3%–23%, n≈34</sub> | ✓ 11,1% <br><sub>P5: 4,7% · IC95 3%–34%, n≈16</sub> | ▼ 7,8% <br><sub>P5: 4,8% · IC95 1%–45%, n≈7</sub> |
| BTC/BRL | ✓ 11,5% <br><sub>P5: 4,9% · IC95 7%–19%, n≈105</sub> | ✓ 9,2% <br><sub>P5: 4,8% · IC95 3%–23%, n≈34</sub> | ✓ 11,6% <br><sub>P5: 4,2% · IC95 3%–35%, n≈16</sub> | ▼ 7,8% <br><sub>P5: 4,5% · IC95 1%–45%, n≈7</sub> |

Na meta: **7 de 12**.

### 2. Corte 2018 (projeções de 2018 a 2020)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 19,1% <br><sub>P5: 7,2% · IC95 10%–35%, n≈36</sub> | ▲ 17,1% <br><sub>P5: 9,9% · IC95 5%–45%, n≈12</sub> | ▲ 20,4% <br><sub>P5: 12,5% · IC95 4%–60%, n≈6</sub> | ▲ 22,4% <br><sub>P5: 7,9% · IC95 3%–73%, n≈3</sub> |
| BTC/USD | ▲ 15,1% <br><sub>P5: 9,9% · IC95 7%–30%, n≈36</sub> | ▲ 13,8% <br><sub>P5: 9,2% · IC95 3%–42%, n≈12</sub> | ▲ 15,8% <br><sub>P5: 11,2% · IC95 3%–56%, n≈6</sub> | ▼ 7,2% <br><sub>P5: 6,6% · IC95 0%–62%, n≈3</sub> |
| BTC/BRL | ▲ 13,2% <br><sub>P5: 7,9% · IC95 6%–28%, n≈36</sub> | ✓ 11,2% <br><sub>P5: 9,9% · IC95 2%–39%, n≈12</sub> | ▲ 13,8% <br><sub>P5: 8,6% · IC95 2%–54%, n≈6</sub> | ▼ 6,6% <br><sub>P5: 3,3% · IC95 0%–62%, n≈3</sub> |

### Corte 2021 (projeções de 2021 a 2026)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▼ 6,1% <br><sub>P5: 2,0% · IC95 2%–14%, n≈69</sub> | ▼ 2,5% <br><sub>P5: 0,0% · IC95 0%–19%, n≈22</sub> | ▼ 0,0% <br><sub>P5: 0,0% · IC95 0%–28%, n≈10</sub> | ▼ 0,0% <br><sub>P5: 0,0% · IC95 0%–49%, n≈4</sub> |
| BTC/USD | ✓ 11,9% <br><sub>P5: 6,1% · IC95 6%–22%, n≈69</sub> | ▼ 6,7% <br><sub>P5: 1,8% · IC95 2%–25%, n≈22</sub> | ✓ 8,5% <br><sub>P5: 1,1% · IC95 1%–39%, n≈10</sub> | ✓ 8,1% <br><sub>P5: 3,6% · IC95 1%–57%, n≈4</sub> |
| BTC/BRL | ✓ 10,6% <br><sub>P5: 3,4% · IC95 5%–20%, n≈69</sub> | ✓ 8,1% <br><sub>P5: 2,1% · IC95 2%–27%, n≈22</sub> | ✓ 10,3% <br><sub>P5: 1,8% · IC95 2%–41%, n≈10</sub> | ✓ 8,5% <br><sub>P5: 5,3% · IC95 1%–57%, n≈4</sub> |

Falhas estatisticamente significativas: **0 de 24**.

### Fatores de recalibração estimados dentro da amostra

k = (frequência abaixo do P10 dentro da janela de ajuste) / 10%, limitado entre 1 e 2. Com k = 1,4, o P10 do painel é o quantil 10/1,4 ≈ 7,1% do modelo; P5 e P1 seguem a mesma proporção.

| Corte | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|---|
| 2018 | USD/BRL | 1,43 <sub>(14,3%, n=442)</sub> | 1,69 <sub>(16,9%, n=437)</sub> | 2,00 <sub>(21,6%, n=431)</sub> | 2,00 <sub>(22,5%, n=418)</sub> |
| 2018 | BTC/USD | 1,00 <sub>(4,8%, n=42)</sub> | 1,00 <sub>(0,0%, n=37)</sub> | 1,00 <sub>(0,0%, n=31)</sub> | 1,00 <sub>(0,0%, n=19)</sub> |
| 2018 | BTC/BRL | 1,00 <sub>(4,8%, n=42)</sub> | 1,00 <sub>(0,0%, n=37)</sub> | 1,00 <sub>(0,0%, n=31)</sub> | 1,00 <sub>(0,0%, n=19)</sub> |
| 2021 | USD/BRL | 1,43 <sub>(14,3%, n=517)</sub> | 1,64 <sub>(16,4%, n=513)</sub> | 2,00 <sub>(21,1%, n=506)</sub> | 2,00 <sub>(23,7%, n=494)</sub> |
| 2021 | BTC/USD | 1,00 <sub>(7,7%, n=117)</sub> | 1,00 <sub>(6,2%, n=113)</sub> | 1,00 <sub>(6,5%, n=107)</sub> | 1,00 <sub>(6,4%, n=94)</sub> |
| 2021 | BTC/BRL | 1,00 <sub>(5,1%, n=117)</sub> | 1,00 <sub>(6,2%, n=113)</sub> | 1,00 <sub>(4,7%, n=107)</sub> | 1,00 <sub>(4,3%, n=94)</sub> |

### 3. Os choques reais cabem no P5?

Percentil do valor realizado na distribuição-base projetada na véspera do choque, na direção ruim. Abaixo de 5, o choque foi pior que o P5.

| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|---|
| Covid (14/02/2020) | USD/BRL | **0,2** | **0,6** | **4,9** | 13,7 |
| Covid (14/02/2020) | BTC/USD | **0,2** | 36,5 | 75,6 | 99,3 |
| Covid (14/02/2020) | BTC/BRL | **0,5** | 86,2 | 90,9 | 99,4 |
| Inverno cripto (10/11/2021) | USD/BRL | 33,2 | 72,0 | 74,7 | 59,7 |
| Inverno cripto (10/11/2021) | BTC/USD | 5,6 | 11,9 | 6,1 | **3,0** |
| Inverno cripto (10/11/2021) | BTC/BRL | 6,9 | 10,3 | 5,2 | **2,9** |
| Pacote fiscal (30/09/2024) | USD/BRL | 13,3 | 8,3 | 50,0 | 59,5 |
| Pacote fiscal (30/09/2024) | BTC/USD | 87,4 | 95,0 | 82,3 | 90,3 |
| Pacote fiscal (30/09/2024) | BTC/BRL | 92,5 | 97,2 | 83,8 | 88,5 |

**Validação cruzada dos estresses.** Para cada choque, a variação realizada em cada horizonte é comparada com o P5 dos cenários de estresse que **não** foram construídos com aquele episódio (o pacote fiscal de 2024 é análogo do cenário 2026–27, que fica de fora nesse caso).

| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|---|
| Covid | USD/BRL | 18% <br><sub>Crise fiscal</sub> | 32% <br><sub>Crise fiscal, Fiscal e eleitoral</sub> | 27% <br><sub>Crise fiscal, Fiscal e eleitoral</sub> | 25% <br><sub>base</sub> |
| Covid | BTC/USD | −48% <br><sub>**nenhum**</sub> | −8% <br><sub>base</sub> | 15% <br><sub>base</sub> | 440% <br><sub>base</sub> |
| Covid | BTC/BRL | −38% <br><sub>Inverno cripto</sub> | 21% <br><sub>base</sub> | 46% <br><sub>base</sub> | 575% <br><sub>base</sub> |
| Inverno cripto | USD/BRL | 2% <br><sub>base</sub> | −3% <br><sub>base</sub> | −6% <br><sub>base</sub> | −3% <br><sub>base</sub> |
| Inverno cripto | BTC/USD | −27% <br><sub>base</sub> | −32% <br><sub>base</sub> | −55% <br><sub>base</sub> | −73% <br><sub>Covid</sub> |
| Inverno cripto | BTC/BRL | −26% <br><sub>base</sub> | −34% <br><sub>base</sub> | −58% <br><sub>base</sub> | −74% <br><sub>Covid</sub> |
| Pacote fiscal de 2024 | USD/BRL | 5% <br><sub>base</sub> | 14% <br><sub>base</sub> | 4% <br><sub>base</sub> | −2% <br><sub>base</sub> |
| Pacote fiscal de 2024 | BTC/USD | 15% <br><sub>base</sub> | 48% <br><sub>base</sub> | 30% <br><sub>base</sub> | 87% <br><sub>base</sub> |
| Pacote fiscal de 2024 | BTC/BRL | 20% <br><sub>base</sub> | 68% <br><sub>base</sub> | 36% <br><sub>base</sub> | 83% <br><sub>base</sub> |

Cada célula traz a variação realizada e quem a contém no P5: “base” quando a própria distribuição-base já a continha.

## Veredito

- Critério 1 (agregado, 8%–12%): **não atendido** — 7 de 12 células na faixa.
- Critério 2 (nenhuma falha significativa por corte): **atendido** — 0 de 24.
- Critério 3 (choques no P5 da base ou de um estresse independente): **não atendido** — sem cobertura: Covid · BTC/USD · 30 dias.

Células agregadas fora da faixa: BTC/BRL 365 dias (7,8%), BTC/USD 30 dias (13,0%), BTC/USD 365 dias (7,8%), USD/BRL 90 dias (7,6%), USD/BRL 180 dias (7,3%). Todas têm IC95 que contém 10%, isto é, o teste não distingue essas frequências de uma calibração exata. Empurrá-las para dentro da faixa exigiria ajustar o modelo ao próprio período de teste, o que trocaria um erro pequeno e visível por sobreajuste invisível.

## Por que o corte 2018 é difícil

De 2018 a 2020 o dólar subiu cerca de 57% contra o real (greve dos caminhoneiros, eleição, Covid e crise fiscal de 2020): uma tendência persistente, não um aumento de volatilidade (a volatilidade anual do câmbio foi de 13,7%, 11,1% e 20,3%, perto da média histórica de 15%). De 2021 a 2026 o câmbio oscilou, mas acumulou só cerca de 14% em quase seis anos. Um modelo sem aposta de tendência erra o primeiro período para o lado otimista e o segundo para o lado pessimista; o agregado mede o equilíbrio entre os dois.

## O que mudou da v1 para a v2

- **Amostra do câmbio desde 01/03/1999**, início do câmbio flutuante, em vez de 2003. A v1 deixava de fora as crises de 2001 e 2002, embora usasse 2002 como análogo do cenário 2026–27.
- **Recalibração da cauda ruim estimada dentro da amostra.** O diagnóstico dentro da própria janela de ajuste mostrou que o modelo simétrico subestima a cauda ruim do câmbio (13% a 19% das origens abaixo do P10, conforme o horizonte, contra 10% a 12% acima do P90): o real cai mais depressa do que sobe. O fator k corrige isso com dados anteriores a cada corte. Para BTC, o histórico dentro da amostra não pede correção (k = 1).
- **Testadas e descartadas**: incerteza de tendência (deriva aleatória por trajetória estimada pela razão de variâncias) no câmbio, que deixou o corte 2021 pessimista demais quando combinada com a recalibração; e no BTC, que derrubou o P10 de 365 dias para perto de zero, porque a razão de variâncias do BTC é dominada por um único episódio (2017).
