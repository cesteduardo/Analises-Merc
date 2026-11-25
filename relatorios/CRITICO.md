# Revisões do crítico cego

O crítico é um subagente que vê apenas capturas do painel renderizado (desktop, celular e tema escuro, com todos os blocos expandidos), o texto renderizado e o `METODOLOGIA.md`. Nunca vê o código nem os dados brutos. Severidades: **crítico** (engana sobre o risco ou viola as prioridades 1 e 2), **maior**, **menor**, **cosmético**. Pronto quando não restar defeito acima de menor.

## Rodada 1 — 25/11/2026 (commit 23b0f67)

**Veredito: REPROVADO** — 2 críticos, 8 maiores, 14 menores, 3 cosméticos.

| # | Severidade | Defeito | Tratamento na rodada 2 |
|---|---|---|---|
| 1 | Crítico | A manchete juntava os dois P1 numa frase ("o dólar passa de R$ 11,41 **e** o bitcoin cai abaixo de US$ 11,8 mil"), sugerindo uma probabilidade conjunta de 1% que o modelo não estimou. | Duas frases separadas e a probabilidade conjunta de fato, calculada nas mesmas trajetórias. |
| 2 | Crítico | A validação cruzada aceitava como cobertura estresses construídos com dados **posteriores** ao choque (2022 cobrindo a Covid; 2026–27, feito com 2024, cobrindo a Covid). | Só contam estresses cujos dados terminam antes da véspera do choque. A contagem de choques sem cobertura subiu. |
| 3 | Maior | "1 em cada 100 trajetórias" é falso depois da recalibração: o P1 do câmbio em 365 dias é o quantil 0,53% da simulação. | Texto passa a falar em probabilidade estimada, e cada tabela diz qual quantil da simulação foi usado. |
| 4 | Maior | O P1 do câmbio em 365 dias (+94%) é o número menos verificável e aparecia sem âncora no topo; k sem incerteza. | Âncora histórica e aviso de extrapolação no cartão do topo; k com IC95. |
| 5 | Maior | Estresses com dispersão contada duas vezes (a mediana já replica o episódio e por cima entrava a volatilidade inteira dele): BTC no Inverno cripto com P1 de −95%. | Dispersão em volta da réplica fixada, como premissa declarada, em metade da volatilidade do episódio; P1 do estresse comparado ao pior histórico. |
| 6 | Maior | Não se dizia se k vale nos estresses; o P1 do câmbio no estresse cripto ficava mais brando que o da base sem aviso. | Declarado que k não se aplica aos estresses; aviso por ativo quando o estresse é mais brando que a base. |
| 7 | Maior | O agregado verde escondia erros opostos entre os cortes (câmbio 30 dias: 19,1% e 6,1%). | Células com cortes em direções opostas marcadas; nota no topo de que a calibração do câmbio depende do regime. |
| 8 | Maior | A única falha otimista (BTC em 30 dias) não chegava à leitura do BTC; "nenhum desvio significativo" soava como aprovação. | Aviso no leque do BTC; selo do topo cita o critério 3 e o baixo poder do teste. |
| 9 | Maior | "Percentil 0,2" na tabela de choques usava a direção ruim, ao contrário da convenção do painel. | Reescrito como "probabilidade estimada de algo pior". |
| 10 | Maior | Celular: coluna de 365 dias cortada nos quantis, legendas truncadas, datas da tabela de fontes invisíveis. | Tabelas compactas que cabem em 390 px; legendas fora do contêiner que rola; fontes em pilha. |
| 11 | Menor | Números do cartão do cenário e da tabela "o que precisaria acontecer" diferentes (mediana simulada × trajetória histórica). | Rótulos explicitam qual é qual. |
| 12 | Menor | Premissa de correlação da Covid mostrava o limiar (0,37), não o valor usado (0,39). | Mostra o valor usado e os dois candidatos. |
| 13 | Menor | Cenário 2026–27: "0,22 no episódio", mas não há episódio. | "correlação atual". |
| 14 | Menor | Persistência 0,99 com meia-vida de 51 dias não fecha. | Três casas decimais. |
| 15 | Menor | Início do BTC: 27/01/2015 no painel, 26/01/2015 na metodologia. | Explicado: preços desde 26/01, primeiro retorno em 27/01. |
| 16 | Menor | Selic com "último dado" em data futura; IPCA 12 meses listado sem uso. | Data limitada à coleta; série sem uso retirada da lista. |
| 17 | Menor | "Deriva zero" com mediana do BTC em −4,3%. | Explicado o efeito da camada de crise na mediana. |
| 18 | Menor | Linha do P1 serrilhada (ruído do Monte Carlo). | Suavização declarada. |
| 19 | Menor | Trecho histórico dos leques sem data; "30d" some no celular. | Data de início e rótulos mantidos. |
| 20 | Menor | "Pior histórico" do BTC só desde 2015, omitindo quedas anteriores. | Nota sobre 2011 e 2013–15, marcada como fora das fontes do painel. |
| 21 | Menor | "O que precisaria acontecer" não dizia se hoje está mais perto ou mais longe; gatilhos sem estresse associado. | Coluna de distância e estresse ligado a cada gatilho. |
| 22 | Menor | Mapa de calor em ordem global, não por ativo. | Ordenado por ativo, pior primeiro. |
| 23 | Menor | Status do backtest só por cor; "!" anunciado e ausente. | Marcadores textuais. |
| 24 | Menor | "Risk-off conjunto" ambíguo. | Definição explícita em USD/BRL e BTC/USD. |
| 25 | Cosmético | Arredondamentos diferentes entre gráfico e cabeçalho. | Mesmo formato. |
| 26 | Cosmético | "US$ 3.050" ao lado de "US$ 14,6 mil". | Formato único. |
| 27 | Cosmético | Datas ISO e nomes internos na tabela de fontes. | Datas em pt-BR e nomes legíveis. |

O que o crítico considerou bem resolvido: direção do "ruim" fixa e explicada; BTC/BRL derivado na mesma trajetória; pior caso primeiro com âncora histórica; backtest exposto com franqueza (IC de Wilson, n efetivo, cortes separados, critério declarado como não pré-registrado); estresses com premissas explícitas; gatilhos com limiar, fonte e data; ausência de dado sobre ETFs declarada.

## Rodada 2 — 25/11/2026 (commit fd4a133)

**Veredito: REPROVADO** — 0 críticos, 2 maiores, 7 menores, 3 cosméticos. Dos 27 defeitos da rodada 1, 24 resolvidos e 3 parciais (7, 19, 21).

| # | Severidade | Defeito | Tratamento na rodada 3 |
|---|---|---|---|
| N1 | Maior | Em 1600 px, a coluna de 365 dias (a do P1) ficava cortada nos quadros do BTC, nas colunas de um terço. | Unidade no cabeçalho ("em US$ mil") e números sem sufixo nas células. |
| N2 | Maior | Com metade da volatilidade do episódio, a dispersão do câmbio nos estresses caía para 8% a 11% a.a., abaixo da de um ano comum; estresses mais brandos que a base no mapa de calor, sem aviso; casos da Covid perdiam cobertura por isso, não pela anterioridade. | Piso na volatilidade de longo prazo do modelo; aviso no mapa de calor quando um estresse é mais brando que a base; sensibilidade do critério 3 a três regras de dispersão (5, 3 e 2 casos sem cobertura). |
| 7 (parcial) | Menor | O selo do topo não dizia que a calibração do câmbio depende do regime. | Selo cita os erros opostos dos dois cortes. |
| 19 (parcial) | Menor | Históricos de comprimentos diferentes entre os leques; rótulo de data sobreposto a "hoje" no celular; "30d" e "30". | Mesmo comprimento nos três; rótulo só quando cabe; rótulos iguais. |
| 21 (parcial) | Menor | Distância da correlação enganosa quando o cenário usa um valor pior que os dois; fluxo cambial ligado a 2015, que não teve saída; ETFs ligados a 2022, sem ETF à vista na época. | "o cenário já usa um valor pior"; ligações retiradas. |
| N3 | Menor | A metodologia atribuía à anterioridade casos que eram efeito da dispersão. | 7.3 separa os dois efeitos. |
| N4 | Menor | 0,53% no topo e 0,54% no leque para o mesmo quantil. | Mesmo cálculo nos dois lugares. |
| N5 | Menor | Retângulo claro vazando e nota cortada no cartão de gatilhos. | Artefato da captura recortada (o `backdrop-filter` falha na borda do recorte); a captura passou a ser de página inteira, cortada depois. |
| N6 | Menor | Tabela da seção 2 da metodologia ainda falava em "trajetórias". | "probabilidade estimada". |
| N7 | Cosmético | Concordância ("o estresse X e Y"). | Plural. |
| N8 | Cosmético | "O P1 vai além" quando o P1 do BTC estava no nível do pior ano. | "no nível do pior ano observado" quando a diferença é de até 3 p.p. |
| N9 | Cosmético | Backtest apertado no celular. | IC sem o rótulo "IC95" no celular. |
