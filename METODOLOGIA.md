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
| P10 | probabilidade estimada de 10% de terminar pior | percentil 90 | percentil 10 |
| P5 | probabilidade estimada de 5% de terminar pior | percentil 95 | percentil 5 |
| P1 | probabilidade estimada de 1% de terminar pior (cauda ruim) | percentil 99 | percentil 1 |
| P90 | lado favorável, só como referência | percentil 10 | percentil 90 |

O **pior caso plausível** do painel é o P1 da distribuição-base em 365 dias. Os P1 são de cada ativo isolado: o painel informa, ao lado, a probabilidade de os dois P1 de 365 dias acontecerem juntos nas mesmas trajetórias, que é muito menor que 1%.

**Probabilidade, não contagem de trajetórias.** No câmbio, a cauda é recalibrada (4.5): o P1 exibido tem probabilidade estimada de 1%, mas corresponde a menos de 1% das trajetórias simuladas (cerca de 0,5% em 365 dias). O painel diz em cada leque qual quantil da simulação foi lido. Os cenários de estresse mostram, ao lado, o que aconteceria se episódios reais se repetissem a partir dos preços de hoje.

**Âncora histórica.** Abaixo de cada leque, a linha "Pior histórico" traz a pior variação observada em cada horizonte, na direção ruim (câmbio desde 01/03/1999; BTC desde 26/01/2015). Ela serve para julgar a plausibilidade do P1: em 30 dias o P1 fica aquém do pior mês da história (setembro de 2008 no câmbio, janeiro de 2018 no BTC), porque um mês tão ruim é mais raro que 1 em 100; em 365 dias, o P1 do câmbio passa do pior ano observado (+74%, de set/2014 a set/2015). É uma consequência da recalibração da cauda (4.5), não uma previsão de que isso vá acontecer, e está exposta para que o leitor a pese.

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
- Os brutos do **Tesouro Direto** e do **Focus anual** são grandes demais para o repositório. A coleta grava, junto com eles, um extrato da última data (`tesouro_resumo.json`, `focus_resumo.json`), que é versionado; sem o bruto completo, o painel usa o extrato. O extrato atual foi reconstruído a partir da coleta completa de 25/11/2026 e traz essa nota no próprio arquivo.
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
- Amostras: câmbio desde 01/03/1999, início do câmbio flutuante (inclui 2001, 2002, 2008, 2013, 2015, 2018, 2020 e 2024). Janeiro e fevereiro de 1999 ficam fora porque são a transição do regime de bandas, não um choque dentro do regime atual. A v1 começava em 2003 e deixava de fora 2001 e 2002, embora usasse 2002 como análogo do cenário 2026–27. BTC desde 26/01/2015.

### 4.3 Deriva zero

A mediana não aposta em tendência: a deriva diária é zero nos dois ativos. Testamos a deriva implícita no diferencial de juros (Selic − Fed Funds, que equivale ao dólar futuro) e tendências passadas; nenhuma melhorou a calibração nos dois cortes (ver `relatorios/CALIBRACAO.md`). O pessimismo do painel vem da cauda gorda, da assimetria, da camada de crise e dos estresses, não de uma mediana empurrada para baixo.

### 4.4 Camada de crise

O GARCH-t subestima episódios em que a perda se acumula por semanas. A camada de crise acrescenta, a cada trajetória, a chance de uma crise começar:

1. **Episódios históricos**: janelas de 21 dias úteis cujo retorno acumulado está entre os 2,5% piores da amostra, separadas por pelo menos 126 dias úteis.
2. **Taxa extra**: simulamos 400 anos com o próprio GARCH-t e contamos quantos episódios ele já gera com o mesmo critério. A camada só acrescenta a diferença entre a taxa observada e a do modelo, para não contar a cauda duas vezes.
3. **Dinâmica**: a crise chega como processo de Poisson. Ao começar, a variância salta para o nível mediano das crises históricas e, por 21 dias, a trajetória recebe a deriva do choque mediano histórico. Nos 126 dias seguintes, devolve a fração mediana historicamente devolvida.

Os valores estimados (taxa extra por ano, choque mediano, fração devolvida) aparecem no painel, na seção de premissas.

### 4.5 Recalibração da cauda ruim

Um diagnóstico dentro da própria amostra de ajuste (o modelo estimado com todos os dados, aplicado a origens passadas a cada 10 dias úteis) mostrou um defeito sistemático no câmbio: o realizado passou do P10 ruim em 13% a 19% das origens, conforme o horizonte, enquanto passou do P90 favorável em 10% a 12%. O real cai mais depressa do que sobe, e um GARCH com inovações simétricas, mesmo com o termo de assimetria, não reproduz isso inteiro.

A correção é deliberadamente simples:

- para cada ativo e horizonte, `k = (frequência abaixo do P10 dentro da amostra) / 10%`, limitado entre 1 e 2;
- o painel passa a ler P10, P5 e P1 nos níveis 10%/k, 5%/k e 1%/k da simulação. Com k = 1,4, o P10 exibido é o quantil 7,1% do modelo;
- entre os horizontes, k é interpolado linearmente nos dias úteis; antes de 21 dias vale o de 30 dias. O drawdown usa o mesmo k;
- **só torna o painel mais pessimista, nunca menos** (k ≥ 1). Essa assimetria é uma premissa ligada ao objetivo do painel, não uma estimativa;
- a mediana (P50) e o lado favorável (P90) não são recalibrados.

No backtest, k é estimado **só com dados anteriores a cada corte**, com horizontes que terminam antes do corte; o período de teste não entra nele. Para BTC e BTC/BRL, o histórico dentro da amostra não pede correção (k = 1 em todos os horizontes e nos dois cortes): a cauda ruim do BTC já é bem servida pela t com ν ≈ 3.

Limite conhecido: k é medido no P10 e estendido proporcionalmente ao P5 e ao P1. Dentro da amostra, a frequência abaixo do P5 do câmbio também passa do esperado (8% a 12% contra 5%), o que apoia a extensão, mas o P1 não tem dados suficientes para ser verificado diretamente.

### 4.6 Correlação e cópula

Os choques padronizados dos dois ativos são ligados por uma **cópula t**, que permite caudas conjuntas (os dois piores dias acontecendo juntos):

- correlação: a dos últimos 250 dias úteis entre os resíduos padronizados do câmbio e do BTC;
- graus de liberdade da cópula: estimados por máxima verossimilhança. Na amostra completa o estimador vai ao limite superior (60), o que equivale a uma cópula quase gaussiana: os dados não mostram dependência de cauda forte no dia a dia.
- **Nos estresses**, a correlação sobe para o maior valor entre a do episódio e o percentil 95 histórico da correlação móvel de 63 dias, e a cópula passa a ter 4 graus de liberdade. Essa é uma piora deliberada (premissa), não uma estimativa.

### 4.7 BTC/BRL

Nunca é projetado sozinho. Em cada trajetória simulada, `BTC/BRL = BTC/USD × USD/BRL`. Assim, um choque que derruba o real atenua a queda do BTC em reais, e um choque que derruba os dois ao mesmo tempo aparece com a força correta.

### 4.8 Simulação

20.000 trajetórias de 252 dias úteis, semente fixa. Nos leques, as linhas das caudas são suavizadas por média móvel centrada de 7 dias úteis, para tirar o ruído do Monte Carlo (o P1 recalibrado do câmbio é lido em cerca de 100 trajetórias); nos quatro horizontes, os valores exibidos são os exatos, iguais aos das tabelas. Os horizontes de 30, 90, 180 e 365 dias corridos são lidos nos passos 21, 63, 126 e 252. O eixo do gráfico é em dias úteis sem feriados; as datas exibidas são aproximadas.

## 5. Cenários de estresse

Cada cenário é uma distribuição condicional: "se as condições do episódio se repetissem a partir dos preços de hoje".

**Regra comum (premissas):**

- **Mediana**: segue, dia a dia, os retornos reais do episódio até o pior ponto dentro de 365 dias corridos, separadamente para câmbio e BTC. Depois do pior ponto, deriva zero. **A recuperação histórica não é assumida.** O painel mostra, ao lado, o que de fato aconteceu 365 dias depois.
- **Dispersão** (premissa): inovações t de Student com **metade** da volatilidade realizada nos 252 dias úteis do episódio, com **piso** na volatilidade de longo prazo do próprio modelo (15% a.a. no câmbio, 66% no BTC). A metade evita contar duas vezes a dispersão do episódio, que a mediana já carrega dia a dia (na v1, com a volatilidade inteira do episódio, o P1 do BTC no inverno cripto chegava a −95%; hoje, com o piso, fica em nível parecido, mas pela incerteza de um ano normal somada à réplica, não pela dispersão do episódio contada duas vezes). O piso impede que um estresse fique mais calmo que um ano comum: só com a metade, a dispersão do câmbio caía para 8% a 11% a.a., abaixo da do modelo-base, e alguns estresses ficavam mais brandos que a base no mapa de calor. Nos episódios atuais o piso está ativo nos dois ativos, de modo que a dispersão efetiva é a de longo prazo do modelo. As duas frações são escolhas declaradas, não estimativas; a sensibilidade do critério 3 a elas está em 7.3. Consequência visível: o P1 de um estresse passa do pior ano observado, porque descreve uma repetição pior que a original somada à incerteza de um ano normal; o painel avisa quando isso acontece.
- **Sem recalibração**: o fator k (4.5) vale só para a distribuição-base. Um estresse pode, num ativo que o episódio não atingiu, ficar mais brando que a base; o painel avisa nesse caso.
- **Correlação**: a maior entre a do episódio e o percentil 95 histórico (63 dias); cópula t com 4 graus de liberdade.
- **Ordem**: do mais severo ao menos severo, pelo maior drawdown mediano em 365 dias entre os três ativos.

| Cenário | Tipo | Início | Base |
|---|---|---|---|
| Crise fiscal, 2015 | reconstruído | 26/01/2015 | PTAX e BTC reais. O início é o primeiro dia com BTC confiável; o real já vinha se depreciando. |
| Covid, mar/2020 | reconstruído | 14/02/2020 | Véspera do choque global de liquidez. |
| Inverno cripto, 2022 | reconstruído | 10/11/2021 | Máxima histórica do BTC antes da queda de 2022. |
| Fiscal e eleitoral, 2026–27 | **construído** | hoje | Câmbio segue a média dos retornos diários de três episódios domésticos: eleição de 2002 (desde 01/04/2002), crise fiscal de 2015 (desde 02/01/2015) e pacote fiscal de 2024 (desde 30/09/2024). BTC sem deriva própria, com a volatilidade de longo prazo; o contágio vem só da correlação piorada. |

O cenário 2026–27 é uma **hipótese**, não uma reconstrução. Ele não afirma nada sobre o resultado da eleição; descreve uma transição com dúvida sobre o arcabouço fiscal.

**Validação cruzada dos estresses.** Um cenário reconstruído contém o próprio episódio por construção, o que não prova nada. O teste útil é outro: cada choque real nomeado (Covid, inverno cripto, pacote fiscal de 2024) é comparado com o P5 da distribuição-base projetada na véspera e com o P5 dos cenários construídos **só com dados anteriores à véspera** (cada cenário usa os 252 dias úteis seguintes ao início do episódio; o 2026–27 usa dados até 01/10/2025). Assim, a Covid só pode ser coberta pelo estresse de 2015; o inverno cripto, pelos de 2015 e da Covid; o pacote fiscal de 2024, pelos três reconstruídos. O resultado está no painel e em `relatorios/CALIBRACAO.md`.

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

- **Cortes**: parâmetros (GARCH, camada de crise, cópula e fator de recalibração) estimados só com dados até 31/12/2017 e até 31/12/2020, e congelados.
- **Origens**: a cada 5 dias úteis, de 2018 a 2020 (corte 2018) e de 2021 ao último dado com horizonte completo (corte 2021). Em cada origem, a volatilidade é filtrada com os dados até ali e a correlação usa os 250 dias anteriores.
- **Métrica**: frequência com que o realizado ficou pior que o P10. Meta do projeto: entre 8% e 12%.
- **Incerteza**: as origens se sobrepõem, então o número de observações independentes é cerca de n × 5 / passos do horizonte. Em 365 dias, cada corte tem de 3 a 4 observações independentes; os dois juntos, cerca de 7. Os intervalos de confiança (Wilson, 95%) usam esse n efetivo.

### 7.2 Critério de aprovação

Escrito nesta rodada, depois de ver os resultados da v1; não é um pré-registro.

1. **Meta principal, agregada.** Para cada ativo × horizonte, com os dois cortes juntos (2018 a 2026), a frequência abaixo do P10 fica entre 8% e 12%.
2. **Por corte, sem falha significativa.** Em cada corte, nenhuma célula tem IC95 que exclua 10%. A faixa de 8% a 12% por corte é mostrada, mas não é exigida: com n = 4, o IC95 de uma frequência de 10% vai de 0% a 55%, e exigir a faixa estreita nessas células seria pedir ao teste uma precisão que ele não tem.
3. **P5 e choques reais.** Cada choque real nomeado cabe no P5 da distribuição-base **ou** no P5 de um estresse construído só com dados anteriores ao choque.

Por que não exigir que o P5 da base contenha todos os choques: os choques nomeados são, por escolha, os piores episódios do período de teste. No câmbio, o mês que começa na véspera da Covid (+18%) está entre os piores de 2018 a 2026, num universo de cerca de 450 origens. Uma distribuição que pusesse esse mês acima do seu P5 teria de ser tão larga que quase nada cairia abaixo do P10, e o critério 1 falharia por excesso de pessimismo. Os estresses existem para cobrir o que a base, calibrada, não cobre.

### 7.3 Estado atual da calibração

**Calibração parcial.** Resultados completos e todas as variantes testadas em `relatorios/CALIBRACAO.md`; resumo da variante em uso (`v3_1999_crise_recal`):

- **Critério 1: 7 de 12** células agregadas na faixa (v1: 6 de 12). Fora da faixa: USD/BRL em 90 e 180 dias (7,6% e 7,3%, pessimista), BTC/USD em 30 dias (13,0%, otimista) e BTC/USD e BTC/BRL em 365 dias (7,8%, pessimista). Em todas, o IC95 contém 10%. Atenção: no câmbio, as células agregadas "na faixa" de 30 e 365 dias resultam de erros opostos que se compensam (corte 2018 otimista, corte 2021 pessimista); o painel as marca. A calibração do câmbio depende do regime.
- **Critério 2: atendido**, mas com pouco poder. Nenhuma das 24 células por corte tem desvio estatisticamente significativo (v1: 1). Com 3 a 10 observações independentes nos horizontes longos, só desvios grandes seriam detectados; isso não é uma aprovação forte.
- **Critério 3: não atendido.** Ficam 3 casos sem cobertura, todos na Covid: o câmbio em 90 dias (+32%) e o BTC/USD e o BTC/BRL em 30 dias (−48% e −38%). Só o estresse de 2015 é anterior à Covid, e nenhum dos três cabe no P5 dele nem no da base. Duas regras pesam nesse resultado, e o efeito de cada uma é separável:
  - **anterioridade**: na rodada 1, sem ela, os mesmos choques da Covid eram "cobertos" por estresses de 2022 e 2026–27, construídos com dados posteriores. A regra de só aceitar estresses anteriores tirou essa cobertura falsa;
  - **dispersão dos estresses**: com metade da volatilidade do episódio e sem piso, seriam 5 casos (o câmbio da Covid em 30 dias e o BTC/BRL do inverno cripto em 365 dias também ficariam de fora); com o piso em uso, 3; com a volatilidade inteira do episódio, 2.
  A falha mais grave é a do BTC em 30 dias na Covid: a queda de 48% fica fora sob qualquer das três regras.

O painel declara esse estado no topo e na seção de backtest. Forçar as cinco células restantes para dentro da faixa exigiria ajustar o modelo ao próprio período de teste.

### 7.4 Crítico cego

Um revisor que vê apenas o painel publicado e este documento, nunca o código, aponta premissas ocultas, pessimismo exagerado ou fraco e gráficos que enganam. As revisões ficam em `relatorios/CRITICO.md`.

## 8. Limitações conhecidas

- **Mudança de regime**: o modelo não prevê mudanças persistentes de tendência (como 2018 a 2020 no câmbio). A camada de crise e os estresses compensam parte disso, não tudo.
- **Parâmetros estimados**: a incerteza de estimação dos parâmetros do GARCH não é propagada para as trajetórias.
- **Correlação**: a correlação medida entre real e BTC é baixa (cerca de 0,2) e instável; a defasagem de horário entre a PTAX e o fechamento do BTC tende a reduzi-la.
- **Dados de BTC antes de 2017** vêm de uma única corretora (Coinbase), com liquidez menor.
- **Gatilhos** não alimentam o modelo. Um gatilho em alerta não muda as faixas; ele indica que um dos estresses ficou mais relevante.
- **Escolhas guiadas pelo backtest**: a variante final foi escolhida olhando os resultados do teste, o que é uma forma branda de sobreajuste. Todas as variantes testadas (11, em três rodadas) estão registradas em `pipeline/variantes.py` e no relatório de calibração. O fator de recalibração, em si, nunca vê o período de teste.
- **Recalibração assimétrica**: k só pode alargar a cauda ruim. Se o histórico um dia indicar que o modelo é pessimista demais, o painel não se corrige sozinho nessa direção.
- **P1 do câmbio em 365 dias acima do pior ano observado**: efeito da recalibração estendida ao P1 (4.5). O painel mostra a âncora histórica ao lado.

## 9. Como atualizar

```
pip install numpy pandas scipy
python3 pipeline/coletar.py              # baixa as séries
python3 pipeline/backtest.py v3_1999_crise_recal   # backtest da variante em uso (~5 min)
python3 pipeline/projetar.py             # gera projections.json (~3 min na 1ª vez do dia)
python3 pipeline/relatorio.py            # gera relatorios/CALIBRACAO.md
```

O painel (`index.html`, `style.css`, `charts.js`) lê `projections.json` e não depende de servidor próprio.
