# Cauda Gorda

Projeções deliberadamente pessimistas de **USD/BRL**, **BTC/USD** e **BTC/BRL** para 30, 90, 180 e 365 dias, entregues num painel visual.

> **Aviso:** este material é estudo de risco, não conselho de investimento.

## O que o painel mostra

- **Distribuições, nunca previsões pontuais:** cada horizonte traz P50, P10, P5 e P1 (a cauda ruim).
- **Pessimismo calibrado:** real depreciando, BTC caindo em dólar e choques correlacionados, em que o risk-off global derruba o bitcoin e o real ao mesmo tempo.
- **Cenários de estresse reconstruídos sobre dados reais:** crise fiscal de 2015, Covid em março de 2020, inverno cripto de 2022 e um cenário fiscal e eleitoral para 2026–27.
- **Leitura de risco primeiro:** fan charts com a cauda P1 em destaque, mapa de calor de drawdown máximo por horizonte e uma tabela do que precisaria acontecer para cada estresse se materializar.

## Modelo, em resumo

Monte Carlo com volatilidade GARCH e caudas gordas (t de Student). A correlação entre USD/BRL e BTC é estimada em janelas móveis e piorada nos estresses. BTC/BRL é sempre derivado de BTC/USD × USD/BRL, nunca projetado isoladamente. A validação combina backtest (dados até 2018 e 2021, meta de 8% a 12% de observações abaixo do P10) e a revisão de um crítico cego, que lê apenas o painel e a metodologia.

## Fontes

Somente públicas e citadas: BCB/PTAX, Boletim Focus, Tesouro Nacional (DI e NTN-B), FRED (DXY, Fed Funds), CoinGecko ou Binance.

## Estrutura

```
.
├── index.html            # painel
├── style.css             # estilos do painel
├── charts.js             # leques, mapa de calor, cenários, gatilhos e backtest
├── projections.json      # saída do modelo: quantis por ativo, horizonte e cenário
├── METODOLOGIA.md        # premissas, fontes, modelo, critérios de calibração e limitações
├── relatorios/
│   ├── CALIBRACAO.md     # backtest de todas as variantes e veredito por critério
│   └── CRITICO.md        # revisões do crítico cego
├── pipeline/             # coleta, modelo, backtest, projeção e relatórios (Python)
└── data/                 # séries brutas com fonte e data de coleta; resultados do backtest
```

## Estado atual

- **Calibração parcial**: 7 de 12 células agregadas na meta de 8% a 12%, nenhuma falha estatisticamente significativa por corte e 3 casos de choque real (todos na Covid) fora do P5 da base e dos estresses anteriores. Detalhes em `relatorios/CALIBRACAO.md`.
- **Crítico cego: aprovado na rodada 3**, sem defeitos críticos ou maiores; os menores restantes foram corrigidos. Histórico em `relatorios/CRITICO.md`.
- O painel abre direto no navegador a partir de um servidor estático qualquer (ele lê `projections.json` via `fetch`).
