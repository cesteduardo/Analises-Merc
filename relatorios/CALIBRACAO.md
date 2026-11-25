# Relatório de calibração

Gerado por `pipeline/relatorio.py` a partir de `data/processed/backtest_*.json`.

## Desenho do teste

- **Cortes**: parâmetros estimados só com dados até 31/12/2017 (corte 2018) e até 31/12/2020 (corte 2021), e congelados.
- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 até o último dado com horizonte completo (corte 2021). Em cada origem a volatilidade é filtrada com os retornos observados até ali, e a correlação usa os 250 dias anteriores.
- **Métrica**: frequência com que o valor realizado ficou **pior que o P10** (dólar acima do percentil 90; BTC abaixo do percentil 10). Meta: 8% a 12%.
- **Incerteza**: as origens se sobrepõem (horizonte maior que o passo de 5 dias), então o número de observações independentes é aproximadamente n × 5 / passos do horizonte. Os intervalos de confiança de Wilson (95%) usam esse n efetivo e são, por isso, largos.
- **Legenda**: ✓ dentro da meta; ▲ acima de 12% (o modelo subestimou o risco); ▼ abaixo de 8% (pessimista demais).

## Deriva zero, sem camada de crise

Combinações na meta: **5 de 24**.

### Corte 2018 (projeções de 2018 a 2020)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 25,7% <br><sub>IC95 14,2%–41,8%, n≈36</sub> | ▲ 27,0% <br><sub>IC95 10,0%–55,1%, n≈12</sub> | ▲ 28,3% <br><sub>IC95 7,4%–66,2%, n≈6</sub> | ▲ 38,2% <br><sub>IC95 7,8%–81,8%, n≈3</sub> |
| BTC/USD | ▲ 16,4% <br><sub>IC95 7,7%–31,6%, n≈36</sub> | ▲ 14,5% <br><sub>IC95 3,7%–42,4%, n≈12</sub> | ▲ 15,8% <br><sub>IC95 2,7%–55,6%, n≈6</sub> | ▼ 7,9% <br><sub>IC95 0,4%–62,6%, n≈3</sub> |
| BTC/BRL | ▲ 13,2% <br><sub>IC95 5,6%–27,8%, n≈36</sub> | ✓ 11,8% <br><sub>IC95 2,7%–39,5%, n≈12</sub> | ▲ 14,5% <br><sub>IC95 2,4%–54,3%, n≈6</sub> | ▼ 6,6% <br><sub>IC95 0,3%–61,6%, n≈3</sub> |

### Corte 2021 (projeções de 2021 a 2026)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ✓ 11,3% <br><sub>IC95 5,8%–20,8%, n≈69</sub> | ✓ 9,8% <br><sub>IC95 2,9%–28,7%, n≈22</sub> | ✓ 8,8% <br><sub>IC95 1,4%–39,1%, n≈10</sub> | ▼ 5,7% <br><sub>IC95 0,3%–54,5%, n≈4</sub> |
| BTC/USD | ▲ 14,7% <br><sub>IC95 8,2%–24,9%, n≈69</sub> | ▲ 13,0% <br><sub>IC95 4,4%–32,6%, n≈22</sub> | ▲ 17,3% <br><sub>IC95 4,5%–48,3%, n≈10</sub> | ▲ 12,1% <br><sub>IC95 1,3%–60,1%, n≈4</sub> |
| BTC/BRL | ✓ 11,9% <br><sub>IC95 6,2%–21,7%, n≈69</sub> | ▲ 14,7% <br><sub>IC95 5,3%–34,6%, n≈22</sub> | ▲ 19,5% <br><sub>IC95 5,4%–50,5%, n≈10</sub> | ▲ 12,1% <br><sub>IC95 1,3%–60,1%, n≈4</sub> |

### Os dois cortes juntos

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 16,2% <br><sub>IC95 10,4%–24,4%, n≈105</sub> | ▲ 15,8% <br><sub>IC95 7,1%–31,4%, n≈34</sub> | ▲ 15,8% <br><sub>IC95 5,1%–39,8%, n≈16</sub> | ▲ 18,0% <br><sub>IC95 3,8%–54,9%, n≈7</sub> |
| BTC/USD | ▲ 15,3% <br><sub>IC95 9,6%–23,4%, n≈105</sub> | ▲ 13,5% <br><sub>IC95 5,7%–28,7%, n≈34</sub> | ▲ 16,7% <br><sub>IC95 5,5%–40,8%, n≈16</sub> | ✓ 10,5% <br><sub>IC95 1,5%–47,5%, n≈7</sub> |
| BTC/BRL | ▲ 12,4% <br><sub>IC95 7,4%–20,0%, n≈105</sub> | ▲ 13,7% <br><sub>IC95 5,8%–29,0%, n≈34</sub> | ▲ 17,7% <br><sub>IC95 6,0%–41,9%, n≈16</sub> | ✓ 10,0% <br><sub>IC95 1,4%–47,0%, n≈7</sub> |

## Deriva do diferencial de juros (Selic − Fed Funds), sem camada de crise

Combinações na meta: **2 de 24**.

### Corte 2018 (projeções de 2018 a 2020)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 23,7% <br><sub>IC95 12,8%–39,7%, n≈36</sub> | ▲ 21,1% <br><sub>IC95 6,8%–49,3%, n≈12</sub> | ▲ 26,3% <br><sub>IC95 6,5%–64,6%, n≈6</sub> | ▲ 33,6% <br><sub>IC95 6,2%–79,4%, n≈3</sub> |
| BTC/USD | ▲ 16,4% <br><sub>IC95 7,7%–31,6%, n≈36</sub> | ▲ 14,5% <br><sub>IC95 3,7%–42,4%, n≈12</sub> | ▲ 15,8% <br><sub>IC95 2,7%–55,6%, n≈6</sub> | ▼ 7,9% <br><sub>IC95 0,4%–62,6%, n≈3</sub> |
| BTC/BRL | ▲ 13,2% <br><sub>IC95 5,6%–27,8%, n≈36</sub> | ✓ 11,8% <br><sub>IC95 2,7%–39,5%, n≈12</sub> | ▲ 15,1% <br><sub>IC95 2,5%–54,9%, n≈6</sub> | ▼ 7,2% <br><sub>IC95 0,4%–62,1%, n≈3</sub> |

### Corte 2021 (projeções de 2021 a 2026)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ✓ 8,9% <br><sub>IC95 4,2%–17,9%, n≈69</sub> | ▼ 6,3% <br><sub>IC95 1,4%–24,2%, n≈22</sub> | ▼ 2,2% <br><sub>IC95 0,1%–30,8%, n≈10</sub> | ▼ 1,2% <br><sub>IC95 0,0%–50,2%, n≈4</sub> |
| BTC/USD | ▲ 14,7% <br><sub>IC95 8,2%–24,9%, n≈69</sub> | ▲ 13,0% <br><sub>IC95 4,4%–32,6%, n≈22</sub> | ▲ 17,3% <br><sub>IC95 4,5%–48,3%, n≈10</sub> | ▲ 12,1% <br><sub>IC95 1,3%–60,1%, n≈4</sub> |
| BTC/BRL | ▲ 13,3% <br><sub>IC95 7,2%–23,3%, n≈69</sub> | ▲ 17,9% <br><sub>IC95 7,1%–38,2%, n≈22</sub> | ▲ 21,3% <br><sub>IC95 6,3%–52,3%, n≈10</sub> | ▲ 16,6% <br><sub>IC95 2,2%–63,7%, n≈4</sub> |

### Os dois cortes juntos

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 13,9% <br><sub>IC95 8,6%–21,8%, n≈105</sub> | ✓ 11,4% <br><sub>IC95 4,5%–26,2%, n≈34</sub> | ✓ 10,8% <br><sub>IC95 2,8%–34,1%, n≈16</sub> | ▲ 13,5% <br><sub>IC95 2,3%–50,6%, n≈7</sub> |
| BTC/USD | ▲ 15,3% <br><sub>IC95 9,6%–23,4%, n≈105</sub> | ▲ 13,5% <br><sub>IC95 5,7%–28,7%, n≈34</sub> | ▲ 16,7% <br><sub>IC95 5,5%–40,8%, n≈16</sub> | ✓ 10,5% <br><sub>IC95 1,5%–47,5%, n≈7</sub> |
| BTC/BRL | ▲ 13,3% <br><sub>IC95 8,1%–21,1%, n≈105</sub> | ▲ 15,8% <br><sub>IC95 7,1%–31,4%, n≈34</sub> | ▲ 19,1% <br><sub>IC95 6,8%–43,4%, n≈16</sub> | ▲ 13,0% <br><sub>IC95 2,2%–50,1%, n≈7</sub> |

## Deriva zero + camada de crise com devolução (ESCOLHIDA)

Combinações na meta: **8 de 24**.

### Corte 2018 (projeções de 2018 a 2020)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 23,7% <br><sub>IC95 12,8%–39,7%, n≈36</sub> | ▲ 20,4% <br><sub>IC95 6,5%–48,7%, n≈12</sub> | ▲ 26,3% <br><sub>IC95 6,5%–64,6%, n≈6</sub> | ▲ 33,6% <br><sub>IC95 6,2%–79,4%, n≈3</sub> |
| BTC/USD | ▲ 15,1% <br><sub>IC95 6,9%–30,1%, n≈36</sub> | ▲ 13,8% <br><sub>IC95 3,5%–41,7%, n≈12</sub> | ▲ 15,8% <br><sub>IC95 2,7%–55,6%, n≈6</sub> | ▼ 7,2% <br><sub>IC95 0,4%–62,1%, n≈3</sub> |
| BTC/BRL | ▲ 13,2% <br><sub>IC95 5,6%–27,8%, n≈36</sub> | ✓ 11,2% <br><sub>IC95 2,4%–38,7%, n≈12</sub> | ▲ 14,5% <br><sub>IC95 2,4%–54,3%, n≈6</sub> | ▼ 6,6% <br><sub>IC95 0,3%–61,6%, n≈3</sub> |

### Corte 2021 (projeções de 2021 a 2026)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ✓ 9,9% <br><sub>IC95 4,8%–19,2%, n≈69</sub> | ▼ 5,6% <br><sub>IC95 1,2%–23,3%, n≈22</sub> | ▼ 1,8% <br><sub>IC95 0,1%–30,3%, n≈10</sub> | ▼ 2,4% <br><sub>IC95 0,1%–51,4%, n≈4</sub> |
| BTC/USD | ▲ 12,3% <br><sub>IC95 6,5%–22,1%, n≈69</sub> | ▼ 7,7% <br><sub>IC95 1,9%–26,1%, n≈22</sub> | ✓ 9,2% <br><sub>IC95 1,5%–39,5%, n≈10</sub> | ✓ 8,1% <br><sub>IC95 0,6%–56,7%, n≈4</sub> |
| BTC/BRL | ✓ 10,6% <br><sub>IC95 5,3%–20,0%, n≈69</sub> | ✓ 9,1% <br><sub>IC95 2,5%–27,9%, n≈22</sub> | ✓ 11,0% <br><sub>IC95 2,1%–41,6%, n≈10</sub> | ✓ 8,5% <br><sub>IC95 0,6%–57,0%, n≈4</sub> |

### Os dois cortes juntos

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 14,6% <br><sub>IC95 9,1%–22,6%, n≈105</sub> | ✓ 10,8% <br><sub>IC95 4,1%–25,4%, n≈34</sub> | ✓ 10,6% <br><sub>IC95 2,7%–33,8%, n≈16</sub> | ▲ 14,3% <br><sub>IC95 2,6%–51,3%, n≈7</sub> |
| BTC/USD | ▲ 13,3% <br><sub>IC95 8,1%–21,1%, n≈105</sub> | ✓ 9,8% <br><sub>IC95 3,6%–24,2%, n≈34</sub> | ✓ 11,6% <br><sub>IC95 3,1%–34,9%, n≈16</sub> | ▼ 7,8% <br><sub>IC95 0,9%–44,6%, n≈7</sub> |
| BTC/BRL | ✓ 11,5% <br><sub>IC95 6,7%–19,0%, n≈105</sub> | ✓ 9,8% <br><sub>IC95 3,6%–24,2%, n≈34</sub> | ▲ 12,3% <br><sub>IC95 3,4%–35,7%, n≈16</sub> | ▼ 7,8% <br><sub>IC95 0,9%–44,6%, n≈7</sub> |

## Deriva do diferencial de juros + camada de crise

Combinações na meta: **6 de 24**.

### Corte 2018 (projeções de 2018 a 2020)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 22,4% <br><sub>IC95 11,8%–38,2%, n≈36</sub> | ▲ 19,1% <br><sub>IC95 5,8%–47,3%, n≈12</sub> | ▲ 24,3% <br><sub>IC95 5,7%–63,0%, n≈6</sub> | ▲ 30,9% <br><sub>IC95 5,4%–77,9%, n≈3</sub> |
| BTC/USD | ▲ 15,1% <br><sub>IC95 6,9%–30,1%, n≈36</sub> | ▲ 13,8% <br><sub>IC95 3,5%–41,7%, n≈12</sub> | ▲ 15,8% <br><sub>IC95 2,7%–55,6%, n≈6</sub> | ▼ 7,2% <br><sub>IC95 0,4%–62,1%, n≈3</sub> |
| BTC/BRL | ▲ 13,2% <br><sub>IC95 5,6%–27,8%, n≈36</sub> | ✓ 11,2% <br><sub>IC95 2,4%–38,7%, n≈12</sub> | ▲ 14,5% <br><sub>IC95 2,4%–54,3%, n≈6</sub> | ▼ 7,2% <br><sub>IC95 0,4%–62,1%, n≈3</sub> |

### Corte 2021 (projeções de 2021 a 2026)

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▼ 6,8% <br><sub>IC95 2,9%–15,3%, n≈69</sub> | ▼ 2,8% <br><sub>IC95 0,3%–19,3%, n≈22</sub> | ▼ 0,0% <br><sub>IC95 0,0%–27,8%, n≈10</sub> | ▼ 0,0% <br><sub>IC95 0,0%–49,0%, n≈4</sub> |
| BTC/USD | ▲ 12,3% <br><sub>IC95 6,5%–22,1%, n≈69</sub> | ▼ 7,7% <br><sub>IC95 1,9%–26,1%, n≈22</sub> | ✓ 9,2% <br><sub>IC95 1,5%–39,5%, n≈10</sub> | ✓ 8,1% <br><sub>IC95 0,6%–56,7%, n≈4</sub> |
| BTC/BRL | ✓ 11,6% <br><sub>IC95 6,0%–21,3%, n≈69</sub> | ✓ 10,2% <br><sub>IC95 3,0%–29,2%, n≈22</sub> | ▲ 13,6% <br><sub>IC95 3,0%–44,4%, n≈10</sub> | ✓ 11,7% <br><sub>IC95 1,2%–59,8%, n≈4</sub> |

### Os dois cortes juntos

| Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| USD/BRL | ▲ 12,1% <br><sub>IC95 7,2%–19,7%, n≈105</sub> | ✓ 8,5% <br><sub>IC95 2,9%–22,5%, n≈34</sub> | ✓ 8,7% <br><sub>IC95 2,0%–31,5%, n≈16</sub> | ✓ 11,8% <br><sub>IC95 1,8%–48,8%, n≈7</sub> |
| BTC/USD | ▲ 13,3% <br><sub>IC95 8,1%–21,1%, n≈105</sub> | ✓ 9,8% <br><sub>IC95 3,6%–24,2%, n≈34</sub> | ✓ 11,6% <br><sub>IC95 3,1%–34,9%, n≈16</sub> | ▼ 7,8% <br><sub>IC95 0,9%–44,6%, n≈7</sub> |
| BTC/BRL | ▲ 12,1% <br><sub>IC95 7,2%–19,7%, n≈105</sub> | ✓ 10,5% <br><sub>IC95 4,0%–25,1%, n≈34</sub> | ▲ 13,9% <br><sub>IC95 4,1%–37,7%, n≈16</sub> | ✓ 10,0% <br><sub>IC95 1,4%–47,0%, n≈7</sub> |

## Os choques reais cabem no P5? (variante escolhida)

Percentil do valor realizado na distribuição projetada na véspera do choque, na direção ruim. Abaixo de 5 significa que o choque foi pior que o P5.

| Choque | Ativo | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|---|
| Covid (14/02/2020) | USD/BRL | **0,1** | **0,3** | **2,9** | 7,8 |
| Covid (14/02/2020) | BTC/USD | **0,2** | 37,1 | 75,7 | 99,3 |
| Covid (14/02/2020) | BTC/BRL | **0,5** | 85,7 | 90,5 | 99,4 |
| Inverno cripto (10/11/2021) | USD/BRL | 22,2 | 72,9 | 76,1 | 62,1 |
| Inverno cripto (10/11/2021) | BTC/USD | 5,3 | 11,9 | 5,3 | **2,9** |
| Inverno cripto (10/11/2021) | BTC/BRL | 6,7 | 10,5 | **4,4** | **2,5** |
| Pacote fiscal (30/09/2024) | USD/BRL | 9,1 | 5,8 | 32,6 | 60,3 |
| Pacote fiscal (30/09/2024) | BTC/USD | 88,8 | 95,1 | 83,8 | 91,0 |
| Pacote fiscal (30/09/2024) | BTC/BRL | 93,0 | 97,4 | 84,4 | 89,0 |

## Variantes exploratórias só de câmbio

Testadas antes da escolha, com o mesmo desenho (frequência pior que o P10, corte 2018 / corte 2021):

| Variante | 30 dias | 90 dias | 180 dias | 365 dias |
|---|---|---|---|---|
| Metade do diferencial de juros | 25,2% / 9,6% | 24,5% / 7,4% | 27,2% / 4,4% | 33,8% / 3,7% |
| Tendência de 1 ano × 0,5 | 22,5% / 10,6% | 21,9% / 9,9% | 28,5% / 11,4% | 29,8% / 14,2% |
| Tendência de 3 anos | 22,5% / 9,2% | 20,5% / 7,4% | 25,8% / 8,5% | 30,5% / 13,4% |

## Conclusão

**A meta ainda não foi atingida.** Nenhuma das variantes testadas calibra os dois cortes ao mesmo tempo, e o motivo é de dados, não de ajuste fino: de 2018 a 2020 o dólar subiu cerca de 57% contra o real (greve dos caminhoneiros, eleição, Covid e crise fiscal de 2020), um movimento persistente que a volatilidade de 2003 a 2017 não antecipava; de 2021 a 2026 o câmbio oscilou muito, mas o dólar acumulou só cerca de 14% em quase seis anos. Um modelo largo o bastante para o primeiro período é pessimista demais no segundo.

A variante escolhida (deriva zero + camada de crise) foi a que melhor equilibrou os dois cortes nos ativos de BTC e a que mais aproximou os choques reais do P5, sem inventar tendência. As escolhas foram feitas olhando os resultados do backtest, o que é uma forma branda de sobreajuste; por isso todas as variantes ficam registradas aqui.
