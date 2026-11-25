# Metodologia do Painel Merc

> **Aviso.** Este painel é um estudo de risco. Não é recomendação de investimento, não diz o que vai acontecer e não sugere compra nem venda de nenhum ativo.

## 1. O que o painel responde

Quão ruim pode ficar, em 30, 90, 180 e 365 dias, o preço do dólar em reais (USD/BRL), do bitcoin em dólar (BTC/USD) e do bitcoin em reais (BTC/BRL), dentro do que é plausível pela história recente. A pergunta é sobre a cauda ruim, não sobre o cenário mais provável.

**"Ruim" tem direção fixa.** Para USD/BRL, ruim é o dólar mais caro (o real perdendo valor). Para BTC/USD e BTC/BRL, ruim é o preço mais baixo. Choques correlacionados, em que uma aversão a risco global derruba o real e o bitcoin juntos, são tratados explicitamente.

## 2. Como ler os números

Toda saída é uma distribuição, nunca um valor único.

| Rótulo | Significado | USD/BRL | BTC/USD e BTC/BRL |
|---|---|---|---|
| P50 | mediana | percentil 50 | percentil 50 |
| P10 | 10% das trajetórias terminam pior | percentil 90 | percentil 10 |
| P5 | 5% terminam pior | percentil 95 | percentil 5 |
| P1 | 1% termina pior (cauda ruim) | percentil 99 | percentil 1 |
| P90 | lado favorável, só como referência | percentil 10 | percentil 90 |

O **pior caso plausível** do painel é o P1 da distribuição-base em 365 dias. Os cenários de estresse mostram, ao lado, o que aconteceria se episódios reais se repetissem a partir dos preços de hoje.

O **drawdown máximo** é a maior queda desde o pico ao longo do caminho, até cada horizonte. Para USD/BRL, é a maior perda do real contra o dólar (queda máxima de BRL/USD). O mapa de calor mostra o P5 (a queda que só 1 em 20 trajetórias ultrapassa) e, menor, a mediana.

## 3. Dados

Só fontes públicas. Cada série é gravada com URL e data e hora de coleta (`data/raw/*.json`); o painel lista todas na seção "Fontes e datas de coleta".

| Uso | Série | Fonte |
|---|---|---|
| Câmbio | Dólar (venda), PTAX, diário, desde 1999 | BCB/SGS 1 |
| BTC/USD | BTCUSDT, fechamento diário UTC, desde 17/08/2017 | Binance (`data-api.binance.vision`) |
| BTC/USD antes de 17/08/2017 | Coinbase Bitcoin, desde 26/01/2015 | FRED CBBTCUSD |
| Conferência do preço à vista | BTC em USD e BRL | CoinGecko |
| Selic | Meta Selic | BCB/SGS 432 |
| Inflação esperada | IPCA esperado 12 meses à frente (suavizado) | BCB/Focus |
| Expectativas anuais | Câmbio, IPCA, Selic, primário, dívida bruta | BCB/Focus |
| Juro real de mercado | Tesouro IPCA+ (NTN-B) e Prefixado, taxa de compra | Tesouro Transparente |
| Risco fiscal | Dívida bruta do governo geral (% PIB); primário 12 meses (% PIB) | BCB/SGS 13762 e 5793 |
| Fluxo cambial | Fluxo contratado, total, diário | BCB/SGS 13961 |
| Dólar global | Índice amplo nominal do dólar | FRED DTWEXBGS |
| Juros americanos | Fed Funds efetivo | FRED DFF |
| Aversão a risco | VIX | FRED VIXCLS |

**Decisões sobre os dados (premissas):**

- O **DXY** da ICE não é publicado no FRED. Usamos o índice amplo do Fed (DTWEXBGS) como proxy público.
- A série da Coinbase no FRED tem lacunas e cotações isoladas antes da abertura da bolsa da Coinbase (por exemplo, US$ 120 em 14/01/2015). Por isso o BTC começa em 26/01/2015.
- O BTC é alinhado às datas da PTAX: em cada dia útil brasileiro usamos o fechamento UTC do mesmo dia. O retorno de segunda-feira inclui o fim de semana. A PTAX é formada por volta das 13h de Brasília, então há algumas horas de defasagem entre as duas séries, o que tende a atenuar a correlação medida.
- O **fluxo de ETFs de BTC** está na lista de gatilhos, mas nenhuma das fontes autorizadas o publica. Ele aparece como "sem dado" e não entra no modelo.
- O **halving** é estimado por cálculo próprio (bloco 1.050.000, a 10 minutos por bloco desde o halving de 20/04/2024), sem série externa. Cai fora da janela de 365 dias e não entra no modelo.

## 4. Modelo-base

### 4.1 Retornos na direção ruim

Trabalhamos com dois retornos diários, ambos com sinal tal que negativo é perda:

- câmbio: `x_fx = −ln(USD/BRL_t / USD/BRL_{t−1})`, o retorno do real contra o dólar;
- bitcoin: `x_btc = ln(BTC_t / BTC_{t−1})`.

### 4.2 Volatilidade: GJR-GARCH(1,1) com t de Student

Para cada ativo:

`σ²_t = ω + (α + γ·1[ε_{t−1} < 0]) · ε²_{t−1} + β · σ²_{t−1}`,   `ε_t = σ_t · z_t`,   `z_t ~ t de Student padronizada (ν)`.

- O termo γ dá **assimetria**: choques ruins (real caindo, BTC caindo) elevam mais a volatilidade seguinte.
- Estimação por máxima verossimilhança com *variance targeting*: ω é fixado para que a variância de longo prazo seja a variância amostral da janela de estimação.
- A persistência α + γ/2 + β é limitada a 0,99 para evitar volatilidade integrada, que faria o cone explodir sem base empírica.
- Amostras: câmbio desde 2003 (inclui 2008, 2013, 2015, 2018, 2020 e 2024); BTC desde 26/01/2015.

### 4.3 Deriva zero

A mediana não aposta em tendência: a deriva diária é zero nos dois ativos. Testamos a deriva implícita no diferencial de juros (Selic − Fed Funds, que equivale ao dólar futuro) e tendências passadas; nenhuma melhorou a calibração nos dois cortes (ver `relatorios/CALIBRACAO.md`). O pessimismo do painel vem da cauda gorda, da assimetria, da camada de crise e dos estresses, não de uma mediana empurrada para baixo.

### 4.4 Camada de crise

O GARCH-t subestima episódios em que a perda se acumula por semanas. A camada de crise acrescenta, a cada trajetória, a chance de uma crise começar:

1. **Episódios históricos**: janelas de 21 dias úteis cujo retorno acumulado está entre os 2,5% piores da amostra, separadas por pelo menos 126 dias úteis.
2. **Taxa extra**: simulamos 400 anos com o próprio GARCH-t e contamos quantos episódios ele já gera com o mesmo critério. A camada só acrescenta a diferença entre a taxa observada e a do modelo, para não contar a cauda duas vezes.
3. **Dinâmica**: a crise chega como processo de Poisson. Ao começar, a variância salta para o nível mediano das crises históricas e, por 21 dias, a trajetória recebe a deriva do choque mediano histórico. Nos 126 dias seguintes, devolve a fração mediana historicamente devolvida.

Os valores estimados (taxa extra por ano, choque mediano, fração devolvida) aparecem no painel, na seção de premissas.

### 4.5 Correlação e cópula

Os choques padronizados dos dois ativos são ligados por uma **cópula t**, que permite caudas conjuntas (os dois piores dias acontecendo juntos):

- correlação: a dos últimos 250 dias úteis entre os resíduos padronizados do câmbio e do BTC;
- graus de liberdade da cópula: estimados por máxima verossimilhança. Na amostra completa o estimador vai ao limite superior (60), o que equivale a uma cópula quase gaussiana: os dados não mostram dependência de cauda forte no dia a dia.
- **Nos estresses**, a correlação sobe para o maior valor entre a do episódio e o percentil 95 histórico da correlação móvel de 63 dias, e a cópula passa a ter 4 graus de liberdade. Essa é uma piora deliberada (premissa), não uma estimativa.

### 4.6 BTC/BRL

Nunca é projetado sozinho. Em cada trajetória simulada, `BTC/BRL = BTC/USD × USD/BRL`. Assim, um choque que derruba o real atenua a queda do BTC em reais, e um choque que derruba os dois ao mesmo tempo aparece com a força correta.

### 4.7 Simulação

20.000 trajetórias de 252 dias úteis, semente fixa. Os horizontes de 30, 90, 180 e 365 dias corridos são lidos nos passos 21, 63, 126 e 252. O eixo do gráfico é em dias úteis sem feriados; as datas exibidas são aproximadas.

## 5. Cenários de estresse

Cada cenário é uma distribuição condicional: "se as condições do episódio se repetissem a partir dos preços de hoje".

**Regra comum (premissas):**

- **Mediana**: segue, dia a dia, os retornos reais do episódio até o pior ponto dentro de 365 dias corridos, separadamente para câmbio e BTC. Depois do pior ponto, deriva zero. **A recuperação histórica não é assumida.** O painel mostra, ao lado, o que de fato aconteceu 365 dias depois.
- **Dispersão**: inovações t de Student com a volatilidade realizada nos 252 dias úteis do episódio.
- **Correlação**: a maior entre a do episódio e o percentil 95 histórico (63 dias); cópula t com 4 graus de liberdade.
- **Ordem**: do mais severo ao menos severo, pelo maior drawdown mediano em 365 dias entre os três ativos.

| Cenário | Tipo | Início | Base |
|---|---|---|---|
| Crise fiscal, 2015 | reconstruído | 26/01/2015 | PTAX e BTC reais. O início é o primeiro dia com BTC confiável; o real já vinha se depreciando. |
| Covid, mar/2020 | reconstruído | 14/02/2020 | Véspera do choque global de liquidez. |
| Inverno cripto, 2022 | reconstruído | 10/11/2021 | Máxima histórica do BTC antes da queda de 2022. |
| Fiscal e eleitoral, 2026–27 | **construído** | hoje | Câmbio segue a média dos retornos diários de três episódios domésticos: eleição de 2002 (desde 01/04/2002), crise fiscal de 2015 (desde 02/01/2015) e pacote fiscal de 2024 (desde 30/09/2024). BTC sem deriva própria, com a volatilidade de longo prazo; o contágio vem só da correlação piorada. |

O cenário 2026–27 é uma **hipótese**, não uma reconstrução. Ele não afirma nada sobre o resultado da eleição; descreve uma transição com dúvida sobre o arcabouço fiscal.

**"O que precisaria acontecer"**: para cada cenário reconstruído, a tabela compara o que os gatilhos marcaram no episódio (VIX, dólar global, Selic real, dívida bruta, fluxo cambial, correlação) com os valores de hoje. Para o cenário construído, as condições são marcadas como hipóteses.

## 6. Gatilhos monitorados

Cada gatilho tem uma regra explícita de status (normal, atenção, alerta). Os limiares são **premissas do painel**, escolhidas para marcar movimentos raros na história, e não fazem parte do modelo: eles informam, não alteram as projeções.

| Gatilho | Leitura | Atenção | Alerta |
|---|---|---|---|
| Risco fiscal | variação da dívida bruta em 12 meses | > +1,5 p.p. | > +3 p.p. |
| Selic real | Selic meta deflacionada pelo IPCA esperado em 12 meses; NTN-B de ~10 anos | < 6% ou NTN-B > 7% | < 4% |
| Dólar global | variação do índice amplo em 3 meses | > +2% | > +4% |
| Fluxo cambial | soma de 63 dias úteis, percentil histórico | 25% piores | 10% piores |
| Aversão a risco | VIX | > 20 | > 30 |
| Halving | data estimada | informativo | — |
| ETFs de BTC | sem fonte autorizada | sem dado | — |

## 7. Verificação

### 7.1 Backtest fora da amostra

- **Cortes**: parâmetros estimados só com dados até 31/12/2017 e até 31/12/2020, e congelados.
- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 ao último dado com horizonte completo (corte 2021). Em cada origem, a volatilidade é filtrada com os dados até ali e a correlação usa os 250 dias anteriores.
- **Métrica**: frequência com que o realizado ficou pior que o P10. Meta: entre 8% e 12%.
- **Choques reais**: posição do realizado na distribuição projetada na véspera da Covid (14/02/2020), do inverno cripto (10/11/2021) e do pacote fiscal (30/09/2024). O critério é que o P5 contenha o choque.
- **Limitação**: as origens se sobrepõem, então o número de observações independentes é pequeno, sobretudo em 365 dias. O relatório traz intervalos de confiança.

### 7.2 Estado atual da calibração

**Ainda não calibrado.** Resultados completos em `relatorios/CALIBRACAO.md`; resumo:

- No **corte 2018**, o modelo subestima a desvalorização do real de 2018 a 2020: o realizado ficou pior que o P10 em 20% a 34% das origens, conforme o horizonte. Nenhuma variante testada resolveu isso sem ficar pessimista demais no corte 2021.
- No **corte 2021**, BTC/USD e BTC/BRL ficam perto da meta (8% a 12%); USD/BRL fica dentro da meta em 30 dias e pessimista demais nos horizontes longos.
- **Choques reais**: a Covid ficou além do P1 em 30 dias para BTC e câmbio, e em 90 dias para o câmbio. O inverno cripto ficou perto do P5 em 30 e 180 dias e entre o P5 e o P1 em 365 dias. Esses episódios entram como cenários de estresse justamente porque a distribuição-base não os contém.

### 7.3 Crítico cego

Um revisor que vê apenas o painel publicado e este documento, nunca o código, aponta premissas ocultas, pessimismo exagerado ou fraco e gráficos que enganam. As revisões ficam em `relatorios/CRITICO.md`.

## 8. Limitações conhecidas

- **Mudança de regime**: o modelo não prevê mudanças persistentes de tendência (como 2018 a 2020 no câmbio). A camada de crise e os estresses compensam parte disso, não tudo.
- **Parâmetros estimados**: a incerteza de estimação dos parâmetros do GARCH não é propagada para as trajetórias.
- **Correlação**: a correlação medida entre real e BTC é baixa (cerca de 0,2) e instável; a defasagem de horário entre a PTAX e o fechamento do BTC tende a reduzi-la.
- **Dados de BTC antes de 2017** vêm de uma única corretora (Coinbase), com liquidez menor.
- **Gatilhos** não alimentam o modelo. Um gatilho em alerta não muda as faixas; ele indica que um dos estresses ficou mais relevante.
- **Escolhas guiadas pelo backtest**: a variante final foi escolhida olhando os resultados do teste, o que é uma forma branda de sobreajuste. Todas as variantes testadas estão registradas.

## 9. Como atualizar

```
pip install numpy pandas scipy
python3 pipeline/coletar.py              # baixa as séries
python3 pipeline/backtest.py zero 0 crise # backtest da variante em uso
python3 pipeline/projetar.py             # gera projections.json
python3 pipeline/relatorio.py            # gera relatorios/CALIBRACAO.md
```

O painel (`index.html`, `style.css`, `charts.js`) lê `projections.json` e não depende de servidor próprio.
